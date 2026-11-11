import unittest
from practice_timer import PracticeTimer


class PracticeTimerTests(unittest.TestCase):
    def test_explicit_pause_resume_fractional_time_and_reset(self):
        now = [10.0]
        timer = PracticeTimer(5, clock=lambda: now[0])
        now[0] += 100
        self.assertEqual(timer.seconds(), 5)
        timer.start()
        now[0] += 1.6
        timer.start()
        self.assertEqual(timer.pause(), 6)
        now[0] += 50
        self.assertEqual(timer.seconds(), 6)
        timer.start()
        now[0] += 0.6
        self.assertEqual(timer.pause(), 7)
        timer.reset()
        self.assertEqual(timer.seconds(), 0)
        self.assertFalse(timer.running)

    def test_limit_backward_clock_and_invalid_initial_values(self):
        now = [100.0]
        timer = PracticeTimer(86399, clock=lambda: now[0])
        timer.start()
        now[0] += 1000
        self.assertEqual(timer.seconds(), 86400)
        self.assertEqual(timer.pause(), 86400)
        timer.reset()
        timer.start()
        now[0] -= 100
        self.assertEqual(timer.pause(), 0)
        for value in (True, -1, 86401, 1.5):
            with self.assertRaises(ValueError):
                PracticeTimer(value)
