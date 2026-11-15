import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from main import BlinkSnap


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def test_photo_survives_pause_and_mode_change(self):
        with tempfile.TemporaryDirectory() as folder:
            app = BlinkSnap(output=folder)
            app.timer.stop()
            app.save_photo(app.scene)
            saved = app.last_saved
            self.assertTrue(saved.is_file())
            self.assertGreater(saved.stat().st_size,1000)
            app.toggle_pause()
            app.simulate_blink()
            self.assertEqual(app.simulated_loss_until,0)
            app.toggle_camera()
            self.assertTrue(saved.is_file())
            self.assertIsNone(app.photo)
            app.close()

    def test_storage_failure_can_be_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            blocked = Path(folder)/'blocked'
            blocked.write_text('This path is a file')
            app = BlinkSnap(output=blocked)
            app.timer.stop()
            app.save_photo(app.scene)
            self.assertEqual(app.phase,'error')
            app.output = Path(folder)/'photos'
            app.save_photo(app.scene)
            self.assertEqual(app.phase,'saved')
            self.assertTrue(app.last_saved.exists())
            app.close()
