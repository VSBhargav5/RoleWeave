import os
import unittest

from background_task import BackgroundTask


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows task lifecycle")
class BackgroundTaskTests(unittest.TestCase):
    def test_cancel_then_destroy_removes_pending_poll_without_callbacks_or_tcl_errors(self):
        import tkinter as tk
        root = tk.Tk(); root.withdraw()
        self.addCleanup(root.destroy)
        root.tk.eval('set ::task_errors {}; proc bgerror {message} {lappend ::task_errors $message}')
        window = tk.Toplevel(root); window.withdraw()
        task = BackgroundTask(window)
        callbacks = []
        task.start(lambda cancel: "synthetic", lambda value: callbacks.append(value), lambda error: callbacks.append(error))
        task.cancel()
        self.assertIsNone(task.poll_id)
        window.destroy()
        root.after(100, root.quit)
        root.mainloop()
        self.assertEqual(callbacks, [])
        self.assertEqual(root.tk.call("set", "::task_errors"), "")
