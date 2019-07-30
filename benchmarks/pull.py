import multiprocessing
import os
import pprint as pp
import time

import cloudpickle as pickle
import ray
from cgroupspy import trees

from .co_runner import Sysbench
from .util import cmd, uuid_str, root_dir


def get_images():
    if "IMAGE" in os.environ:
        return [os.environ["IMAGE"]]
    if "IMAGE_FILE" in os.environ:
        file_ = os.environ["IMAGE_FILE"]
    else:
        file_ = root_dir() + "/images.txt"

    with open(file_, "r") as f:
        return [line.rstrip() for line in f.readlines()]


def clean(images):
    print(">> cleaning images..")
    for i in images:
        cmd("docker rmi {} || true".format(i))


def pull(images, parallel=False):
    print(">> pulling..")

    if parallel:
        _pull_parallel(images)
    else:
        _pull_serial(images)


def _pull_parallel(images):
    @ray.remote
    def _pull_async(image):
        cmd_str = "docker pull {} || true ".format(image)
        # if cgroup is not None:
        #     cmd_str = "echo $$ > {}/tasks; ".format(cgroup) + cmd_str
        cmd(cmd_str)

    futures = [_pull_async.remote(i) for i in images]
    ray.get(futures)


def _pull_serial(images):
    for i in images:
        cmd_str = "docker pull {} || true ".format(i)
        cmd(cmd_str)


"""Experiment tools"""


def exp(f_, name_, **kwargs):
    return {
        "name": name_,
        "configs": kwargs,
        "results": f_(**kwargs),
    }


def output(results):
    # write out results
    print("results:")
    pp.pprint(results)

    if "RESULT" in os.environ:
        result_file = os.environ["RESULT"]
    else:
        result_file = root_dir() + "/results/results-" + uuid_str(4) + ".pickle"
    with open(result_file, "wb") as f:
        pickle.dump(results, f)
        print("results written to:", f.name)


def normalize_dockerd_docker_cpu_shares(dockerd_shares=None, docker_shares=None):
    """Make sure the sum of cpu.shares equal to the total shares which depends on the number of cores."""
    per_core_shares = 1024
    num_cores = multiprocessing.cpu_count()
    total_cpu_shares = per_core_shares * num_cores

    if dockerd_shares and docker_shares:
        assert dockerd_shares + docker_shares == total_cpu_shares, "make sure the sum of shares is less than " + str(
            total_cpu_shares) + "; given dockerd_shares: {}, docker_shares: {}".format(dockerd_shares, docker_shares)
    elif dockerd_shares:
        assert dockerd_shares <= total_cpu_shares, "cpu shares {} too larger for dockerd, maximum {} ".format(
            dockerd_shares, total_cpu_shares)
        docker_shares = total_cpu_shares - dockerd_shares
    elif dockerd_shares:
        assert docker_shares <= total_cpu_shares, "cpu shares {} too larger for docker, maximum {} ".format(
            docker_shares, total_cpu_shares)
        dockerd_shares = total_cpu_shares - dockerd_shares
    else:
        dockerd_shares = per_core_shares
        docker_shares = total_cpu_shares - dockerd_shares

    set_dockerd_docker_cpu_shares(dockerd_shares, docker_shares)


def set_dockerd_docker_cpu_shares(dockerd_shares, docker_shares):
    assert (dockerd_shares >= 0) and (docker_shares >= 0), "given dockerd: %d; docker: %d" % (
        dockerd_shares, docker_shares)
    if dockerd_shares == 0:
        dockerd_shares = 2
    if docker_shares == 0:
        docker_shares = 2

    t = trees.Tree()
    docker_cpu_cg = t.get_node_by_path("/cpu/docker/")
    system_cpu_cg = t.get_node_by_path("/cpu/system.slice/")
    dockerd_cpu_cg = t.get_node_by_path("/cpu/system.slice/docker.service/")

    # set up the cpu.shares s.t. c(docker) + c(system/dockerd) == c(total)
    docker_cpu_cg.controller.shares = docker_shares
    system_cpu_cg.controller.shares = dockerd_shares
    # TODO: decide how to set dockerd cpu share within system.slice
    # dockerd_cpu_cg.controller.shares = dockerd_shares

    print("cpu shares set; dockerd, docker:")
    print(system_cpu_cg.controller.shares, docker_cpu_cg.controller.shares)


class ShareAccount:
    def __init__(self, init_dockerd_shares, init_docker_shares):
        self.dockerd_shares = init_dockerd_shares
        self.docker_shares = init_docker_shares

    def update(self, delta_dockerd, delta_docker):
        self.dockerd_shares += delta_dockerd
        self.docker_shares += delta_docker
        return self

    def set(self):
        set_dockerd_docker_cpu_shares(self.dockerd_shares, self.docker_shares)
        return self


"""Benchmark setups"""


def batch(trials=1, images: list = None):
    # pulling
    results = list()
    if images is None:
        images = get_images()

    for t in range(trials):
        clean(images)

        start = time.time()
        pull(images, parallel=True)
        end = time.time() - start

        print(">> trial %d takes:" % t, end)
        results.append(end)
    return results


def batch_with_corunner(trials=1, dockerd_cpu_shares=None, docker_cpu_shares=None):
    normalize_dockerd_docker_cpu_shares(dockerd_cpu_shares, docker_cpu_shares)

    with Sysbench(num_thread=multiprocessing.cpu_count(),  # occupy all cpu
                  max_prime=200000,
                  max_time=3600,
                  ):
        results = batch(trials)

    # reset by not giving arguments
    normalize_dockerd_docker_cpu_shares()

    return results


class Request:
    def __init__(self, image, cpu_shares):
        self.image = image
        self.cpu_shares = cpu_shares


def synthetic_arrival(dockerd_cpu_shares=128, docker_cpu_shares=8064, image_cpu_shares=500, batch_lend=False, trials=1):
    """Image requests arrive one by one using a synthetic arrival pattern and images.

    If batch_lend is enabled, all requests are assumed to arrive at the beginning, and their
    resources are lent to the dockerd all together and returned one by one after one is pulled.

    image_cpu_shares controls how much cpu share is associated with each image request."""
    # initialize requests from given images
    images = get_images()
    requests = [Request(i, image_cpu_shares) for i in images]  # default shares to 200

    # baseline
    set_dockerd_docker_cpu_shares(dockerd_cpu_shares, docker_cpu_shares)
    baseline_results = list()
    for i in range(trials):
        clean(images)
        total_time = 0
        for r in requests:
            image = r.image
            with Sysbench(num_thread=multiprocessing.cpu_count(),  # occupy all cpu
                          max_prime=200000,
                          max_time=3600,
                          ):
                total_time += batch(images=[image])[0]

        baseline_results.append(total_time)

    # with resource lending
    set_dockerd_docker_cpu_shares(dockerd_cpu_shares, docker_cpu_shares)

    lend_results = list()
    for i in range(trials):
        clean(images)
        total_time = 0

        # use stateful counter to manage and set the cpu shares
        sa = ShareAccount(dockerd_cpu_shares, docker_cpu_shares).set()

        if batch_lend:
            lump_sum_shares = image_cpu_shares * len(requests)
            sa.update(lump_sum_shares, -lump_sum_shares).set()

        for r in requests:
            image = r.image

            # the resource to lend
            cpu_shares = r.cpu_shares

            # update/lend the cpu shares
            if not batch_lend:
                sa.update(cpu_shares, -cpu_shares).set()

            # pull the image
            with Sysbench(num_thread=multiprocessing.cpu_count(),  # occupy all cpu
                          max_prime=200000,
                          max_time=3600,
                          ):
                total_time += batch(images=[image])[0]

            # return the lent resources for this request
            sa.update(-cpu_shares, cpu_shares).set()
        lend_results.append(total_time)

    # clean up and reset cgroup
    set_dockerd_docker_cpu_shares(dockerd_cpu_shares, docker_cpu_shares)
    return baseline_results, lend_results


# benchmarks
def benchmark_1(trials=3):
    """Image pulling time over dockerd cpu shares"""
    ray.init()

    # set up exp and run
    cpu_share_seq = [2 ** i for i in range(7, 14, 1)]  # 128 - 8194, 8 core machine
    results = [
        exp(batch_with_corunner, str(i), trials=trials, dockerd_cpu_shares=i, docker_cpu_shares=8192 - i)
        for i in cpu_share_seq
    ]

    output(results)


def benchmark_2(trials=3):
    """Synthetic image arrival w/w/o resource lending"""
    ray.init()

    results = {
        "serial_lend": synthetic_arrival(dockerd_cpu_shares=128, docker_cpu_shares=8064, image_cpu_shares=500,
                                         batch_lend=False, trials=trials),
        "batch_lend": synthetic_arrival(dockerd_cpu_shares=128, docker_cpu_shares=8064, image_cpu_shares=500,
                                        batch_lend=True, trials=trials),
    }
    output(results)


def benchmark_3(trials=3):
    """Previous benchmark but on the sensitivity of image cpu shares."""
    ray.init()

    results = [
        synthetic_arrival(dockerd_cpu_shares=128, docker_cpu_shares=8064, image_cpu_shares=s, batch_lend=True, trials=trials)
        for s in [100, 200, 400, 800]
    ]
    output(results)


def cgroup_test():
    t = trees.Tree()
    cpu = t.get_node_by_path("/cpu/")
    new_cpu = cpu.create_cgroup("testcg")

    cmd("echo $$ > {}/tasks".format(new_cpu.full_path.decode()) + "; cat {}/tasks".format(new_cpu.full_path.decode()))

    print(new_cpu.name)
    print(new_cpu.full_path.decode())
    print(new_cpu.controller.shares)

    cpu.delete_cgroup("testcg")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("please run as root.")
    else:
        benchmark_3()
        # cgroup_test()
