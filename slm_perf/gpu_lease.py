"""Advisory process lease shared by supported GPU launchers; no MLX import."""
import fcntl
import os
from pathlib import Path

LOCK_PATH = Path.home() / '.cache/benchmark-slm/gpu-lease.lock'
FD_ENV = 'SLM_GPU_LEASE_FD'


class GPUBusy(RuntimeError):
    """Another cooperating process owns the GPU lease."""


class GPULease:
    """Hold an exclusive flock, optionally sharing a descriptor inherited from a parent."""

    def __init__(self, path=None):
        """Choose a persistent lock inode; never unlink it while processes may use it."""
        self.path = Path(path) if path is not None else LOCK_PATH
        self.fd = None

    def __enter__(self):
        """Acquire before GPU work; validate inherited descriptors against the lock inode."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        inherited = os.environ.get(FD_ENV)
        if inherited is not None:
            try:
                source = int(inherited)
                info = os.fstat(source)
                expected = self.path.stat()
                if (info.st_dev, info.st_ino) != (expected.st_dev, expected.st_ino):
                    raise ValueError('Inherited GPU lease refers to a different file')
                self.fd = os.dup(source)
            except (OSError, ValueError) as exc:
                raise RuntimeError('Invalid inherited GPU lease') from exc
        else:
            self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.close()
            raise GPUBusy('Another GPU workload holds the shared lease') from exc
        except BaseException:
            self.close()
            raise
        return self

    def child_options(self):
        """Explicitly hand the same lock description to one supervised child process."""
        if self.fd is None:
            raise RuntimeError('GPU lease is not acquired')
        return dict(pass_fds=(self.fd,), env={**os.environ, FD_ENV: str(self.fd)})

    def survive_exec(self):
        """Retain ownership when an off-mode launcher execs the original workload."""
        if self.fd is None:
            raise RuntimeError('GPU lease is not acquired')
        os.set_inheritable(self.fd, True)

    def close(self):
        """Close our reference; inherited children retain ownership until they exit."""
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __exit__(self, *exc):
        """Release this process's reference on success and on exceptional exits."""
        self.close()
