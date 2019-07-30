import os
import subprocess
import sys
import time
import uuid
from functools import wraps

_dir = os.path.dirname(os.path.realpath(__file__))


def root_dir():
    return _dir


def uuid_str(digit=8):
    return str(uuid.uuid4())[:digit]


def cmd(cmd, out=False, quiet=False, async_=False, executable='/bin/bash'):
    """Executes a subprocess running a shell command and returns the output."""
    if async_:
        subprocess.Popen(cmd,
                         shell=True,
                         stdin=None,
                         stdout=None,
                         stderr=None,
                         close_fds=True,
                         executable=executable)
        return
    elif quiet or out:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            executable=executable)
    else:
        proc = subprocess.Popen(cmd, shell=True)

    if proc.returncode:
        if quiet:
            print('Log:\n', out, file=sys.stderr)
        print('Error has occurred running command: %s' % cmd, file=sys.stderr)
        sys.exit(proc.returncode)
    out, _ = proc.communicate()
    return out


def timed(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        ts = time.time()
        result = f(*args, **kwds)
        te = time.time()
        if 'log_time' in kwds:
            name = kwds.get('log_name', f.__name__.upper())
            kwds['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f s' % (f.__name__, (te - ts) * 1))
        return result

    return wrapper


if __name__ == "__main__":
    cmd("echo happy")
