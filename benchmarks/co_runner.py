import signal
import sys
import time

from cgroupspy.nodes import Node as CG_Node

from .util import cmd, uuid_str, root_dir


class Sysbench:
    _image = "severalnines/sysbench"

    def __init__(self, num_thread=1, max_prime=1, max_time=10, async_=True, quiet=True, get_result=False,
                 cgroup: CG_Node = None, with_docker=True, docker_cpu_share=None):
        self.num_thread = num_thread
        self.max_prime = max_prime
        self.max_time = max_time
        self.async_ = async_
        self.quiet = quiet
        self.cgroup = cgroup
        self.with_docker = with_docker
        self.docker_cpu_share = docker_cpu_share
        self.result_file = root_dir() + "/" + uuid_str()
        self.get_result = get_result

    def __enter__(self):
        self.prepare()
        self.run()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
        self.clean()

    @staticmethod
    def prepare():
        cmd("set -x; sudo kill -KILL $(pgrep sysbench)")

    @staticmethod
    def stop():
        cmd("set -x; sudo kill -KILL $(pgrep sysbench)")

    def run(self):
        cmd_str = "docker run {} severalnines/sysbench sysbench cpu " \
                  "--threads={} " \
                  "--cpu-max-prime={} " \
                  "--time={} run" \
            .format("" if self.docker_cpu_share is None else "--cpu-shares=" + str(self.docker_cpu_share),
                    self.num_thread,
                    self.max_prime,
                    self.max_time,
                    )
        if self.quiet:
            if self.get_result:
                _to = self.result_file
            else:
                _to = "/dev/null"
            cmd_str += " > {} 2>&1".format(_to)

        if self.async_:
            cmd_str += " &"

        if self.cgroup is not None:
            cmd_str = "echo $$ > {}/tasks; ".format(self.cgroup.full_path.decode()) + cmd_str

        cmd(cmd_str)

        # wait a bit for it to start running
        time.sleep(3)
        print(">> sysbench running..")
        return self

    def wait(self, interval=10):
        time.sleep(interval)
        return self

    def parse(self):
        with open(self.result_file, "r") as f:
            # TODO:
            print(f.read())
        return

    def clean(self):
        if self.get_result:
            cmd("rm " + self.result_file)
        return self


def make_signal_handler(f):
    def handler(sig, frame):
        f()
        sys.exit(0)

    return handler


signal.signal(signal.SIGINT, make_signal_handler(Sysbench.stop))

if __name__ == "__main__":
    Sysbench(num_thread=8, max_prime=200000, max_time=180,
             docker_cpu_share=128, async_=False, quiet=False).run().wait(180)
