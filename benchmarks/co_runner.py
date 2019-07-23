import signal
import sys
import time

from .util import cmd


class Sysbench:
    _image = "severalnines/sysbench"

    def __init__(self, num_thread=1, max_prime=1, max_time=10, async_=True):
        self.num_thread = num_thread
        self.max_prime = max_prime
        self.max_time = max_time
        self.async_ = async_

    def __enter__(self):
        self.run()

    def __exit__(self, type, value, traceback):
        self.stop()

    @staticmethod
    def stop():
        cmd("sudo kill -KILL $(pgrep sysbench)")

    def run(self):
        # TODO: add cpu share

        cmd_str = "docker run severalnines/sysbench sysbench cpu " \
                  "--threads={} " \
                  "--cpu-max-prime={} " \
                  "--time={} run".format(self.num_thread,
                                         self.max_prime,
                                         self.max_time)
        if self.async_:
            cmd_str += " > /dev/null 2>&1 &"

        cmd(cmd_str)
        # wait a bit for it to start running
        time.sleep(3)
        
        print(">> sysbench running..")
        return self

    def wait(self, interval=10):
        time.sleep(interval)
        return self


def make_signal_handler(f):
    def handler(sig, frame):
        f()
        sys.exit(0)

    return handler


signal.signal(signal.SIGINT, make_signal_handler(Sysbench.stop))

if __name__ == "__main__":
    Sysbench(num_thread=8, max_prime=200000, max_time=180).run().wait(180).stop()
