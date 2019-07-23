import multiprocessing
import os
import pprint as pp
import time

import ray

from .co_runner import Sysbench
from .util import cmd


def get_images():
    if "IMAGE" in os.environ:
        return [os.environ["IMAGE"]]
    if "IMAGE_FILE" in os.environ:
        file_ = os.environ["IMAGE_FILE"]
    else:
        file_ = "./images.txt"

    with open(file_, "r") as f:
        return [line.rstrip() for line in f.readlines()]


def clean(images):
    print(">> cleaning..")
    for i in images:
        cmd("docker rmi {} || true".format(i))


def pull(images, parallel=False):
    print(">> pulling..")
    if parallel:
        pull_parallel(images)
    else:
        pull_serial(images)


def pull_parallel(images):
    futures = [_pull_async.remote(i) for i in images]
    ray.get(futures)


def pull_serial(images):
    for i in images:
        cmd("docker pull {} || true ".format(i))


@ray.remote
def _pull_async(image):
    cmd("docker pull {} || true ".format(image))


"""Benchmark setups"""


def baseline(trials=1):
    results = list()
    images = get_images()

    for t in range(trials):
        clean(images)

        start = time.time()
        pull(images, parallel=True)
        end = time.time() - start

        print(">> trial %d takes:" % t, end)
        results.append(end)

    return results


def with_corunner(trials=1):
    with Sysbench(num_thread=multiprocessing.cpu_count(),
                  max_prime=200000,
                  max_time=1800):
        return baseline(trials)


def main():
    ray.init()

    pp.pprint({
        "baseline": baseline(trials=1),
        "with_corunner": with_corunner(trials=1),
    })


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("please run as root.")
    else:
        main()
