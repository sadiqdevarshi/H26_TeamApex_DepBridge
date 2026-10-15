"""A nonblocking process lock prevents two workers from recovering each other's jobs."""
import os


class ProcessLock:
    def __init__(self, data_dir):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.file = (data_dir / "service.lock").open("a+b")
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise RuntimeError("Another service process is using this data directory. Run exactly one Uvicorn worker.") from exc

    def close(self):
        if not self.file.closed:
            self.file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close()
