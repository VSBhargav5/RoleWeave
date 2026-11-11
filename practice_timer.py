"""Explicit local elapsed time; not attention, skill or learning measurement."""
import time
from rehearsal_journal import MAX_PRACTICE_SECONDS


class PracticeTimer:
    def __init__(self, seconds=0, *, clock=time.monotonic):
        if type(seconds) is not int or not 0 <= seconds <= MAX_PRACTICE_SECONDS:
            raise ValueError("Invalid initial practice seconds")
        self.clock = clock
        self.total = float(seconds)
        self.started = None

    @property
    def running(self):
        return self.started is not None

    def seconds(self):
        extra = max(0.0, self.clock() - self.started) if self.running else 0.0
        return min(MAX_PRACTICE_SECONDS, int(self.total + extra))

    def start(self):
        if not self.running:
            self.started = self.clock()

    def pause(self):
        if self.running:
            self.total = min(MAX_PRACTICE_SECONDS, self.total + max(0.0, self.clock() - self.started))
            self.started = None
        return self.seconds()

    def reset(self):
        self.started = None
        self.total = 0.0
