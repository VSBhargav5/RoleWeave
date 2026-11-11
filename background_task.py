"""Keep provider I/O off Tk's thread and discard cancelled/late results."""
import queue
import threading
import time


class BackgroundTask:
    def __init__(self, owner):
        self.owner = owner
        self.active = None
        self.poll_id = None

    def start(self, work, done, failed):
        if self.active is not None:
            raise ValueError("A request is already running")
        cancel, results = threading.Event(), queue.Queue(maxsize=1)
        token = object()
        self.active = (token, cancel)
        deadline = time.monotonic() + 60

        def worker():
            try:
                result = (True, work(cancel))
            except Exception as exc:
                result = (False, str(exc) if isinstance(exc, ValueError) else "Provider task failed; no automatic retry")
            results.put(result)

        def poll():
            self.poll_id = None
            if self.active is None or self.active[0] is not token:
                return
            if not self.owner.winfo_exists():
                self.cancel()
                return
            if time.monotonic() >= deadline:
                self.cancel()
                failed("Local 60-second deadline reached. A sent request may still be processed remotely.")
                return
            try:
                ok, value = results.get_nowait()
            except queue.Empty:
                self.poll_id = self.owner.after(50, poll)
                return
            self.active = None
            (done if ok else failed)(value)

        threading.Thread(target=worker, daemon=True).start()
        self.poll_id = self.owner.after(50, poll)

    def cancel(self):
        if self.poll_id is not None:
            self.owner.after_cancel(self.poll_id)
            self.poll_id = None
        if self.active is not None:
            self.active[1].set()
            self.active = None
