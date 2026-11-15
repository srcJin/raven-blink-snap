"""BlinkSnap — a local, two-blink camera for Raven Prism."""
import math
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QPointF, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import QApplication, QWidget
from raven_framework import Button, RavenApp, RunApp, VerticalContainer
from blink import BlinkDetector

ACCENT = '#EDC181'
INK = '#ECEAE3'
MUTED = '#9DABA5'


def demo_image():
    """An original illustrated scene. No camera image is represented as live."""
    image = QImage(1200, 800, QImage.Format.Format_RGB32)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    sky = QLinearGradient(0, 0, 0, 800)
    sky.setColorAt(0, QColor('#102B31'))
    sky.setColorAt(1, QColor('#C39061'))
    p.fillRect(image.rect(), sky)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor('#F3D1A1'))
    p.drawEllipse(QPointF(815, 235), 79, 79)
    for points, color in [([(0,560),(220,240),(450,500),(670,310),(930,580),(1200,355),(1200,800),(0,800)], '#355455'), ([(0,670),(270,480),(500,690),(860,450),(1200,650),(1200,800),(0,800)], '#163D40')]:
        path = QPainterPath(QPointF(*points[0]))
        for point in points[1:]:
            path.lineTo(*point)
        path.closeSubpath()
        p.fillPath(path, QColor(color))
    p.fillRect(0,660,1200,140,QColor('#0C292F'))
    p.setPen(QPen(QColor('#BB9D79'), 2))
    for i in range(15):
        y=670+i*8
        p.drawLine(660-i*8,y,920+i*8,y)
    p.end()
    return image


class CameraJob(QThread):
    captured = Signal(QImage)
    failed = Signal(str)

    def run(self):
        camera = None
        try:
            from raven_framework.peripherals.camera import Camera
            import cv2
            camera = Camera(app_id=os.getenv('RAVEN_APP_ID',''), app_key=os.getenv('RAVEN_APP_KEY',''))
            camera.open_camera()
            if not camera.is_camera_open():
                raise RuntimeError('Camera unavailable. Check permission and retry.')
            frame = camera.capture_camera_image()
            if frame is None:
                raise RuntimeError('No frame received. Please retry.')
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, _ = rgb.shape
            self.captured.emit(QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy())
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if camera is not None:
                camera.close_camera()


class View(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setFixedSize(600, 470)
        self.setAccessibleName('BlinkSnap viewfinder')

    def paintEvent(self, event):
        a = self.owner
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        def text(x,y,value,size=18,color=INK,weight=QFont.Weight.Normal):
            font = QFont('Inter 24pt')
            font.setPixelSize(round(size * 4 / 3))
            font.setWeight(weight)
            p.setFont(font)
            p.setPen(QColor(color))
            p.drawText(x,y,value)
        text(8,30,'BLINKSNAP',18,INK,QFont.Weight.DemiBold)
        text(402,30,'DEMO' if a.demo else 'CAMERA',13,ACCENT,QFont.Weight.DemiBold)
        p.setPen(QPen(QColor('#354641'),1))
        p.drawLine(8,48,590,48)
        text(8,103,a.heading,34,INK,QFont.Weight.Medium)
        text(8,137,a.subtitle,17,MUTED)
        frame = QRectF(8,161,582,246)
        path = QPainterPath()
        path.addRoundedRect(frame,18,18)
        p.save()
        p.setClipPath(path)
        if a.demo or a.photo is not None:
            photo = a.photo if a.photo is not None else a.scene
            crop_height = min(photo.height(), photo.width() * frame.height() / frame.width())
            crop_width = min(photo.width(), photo.height() * frame.width() / frame.height())
            source = QRectF((photo.width()-crop_width)/2, (photo.height()-crop_height)/2, crop_width, crop_height)
            p.drawImage(frame,photo,source)
            p.fillRect(QRectF(8,365,582,42),QColor(0,0,0,125))
        else:
            p.fillRect(frame,QColor('#101C19'))
        p.restore()
        # Clear, generously spaced viewfinder corners.
        p.setPen(QPen(QColor(ACCENT),2))
        for x,y,sx,sy in [(28,181,1,1),(570,181,-1,1),(28,387,1,-1),(570,387,-1,-1)]:
            p.drawLine(x,y,x+sx*20,y)
            p.drawLine(x,y,x,y+sy*20)
        text(56,391,'ILLUSTRATED DEMO' if a.demo else ('SAVED PHOTO' if a.photo else 'CAMERA READY'),11,INK)
        if not a.demo and a.photo is None:
            text(155,285,'Capture with two blinks',20)
        for i in range(2):
            lit = a.phase == 'saved' or (i == 0 and a.detector.first_blink is not None)
            p.setBrush(QColor(ACCENT if lit else '#263C34'))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(540+i*28,438),6,6)
        text(8,445,a.status,15,ACCENT if a.phase=='saved' else MUTED)
        if a.phase == 'capturing':
            p.setPen(QPen(QColor(ACCENT),3))
            p.drawArc(QRectF(270,263,40,40),int((-a.animation*180 % 360)*16),230*16)
        p.end()


class BlinkSnap(RavenApp):
    def __init__(self, parent=None, device=False, output=None, clock=time.monotonic):
        from raven_framework.helpers.font_utils import load_font_family
        load_font_family("inter")
        super().__init__(parent)
        self.clock = clock
        self.demo = True
        self.armed = True
        self.device = device
        self.output = Path(output or os.getenv('BLINKSNAP_DIR', str(Path.home()/'Pictures'/'Raven BlinkSnap'))).expanduser()
        self.detector = BlinkDetector()
        self.scene = demo_image()
        self.photo = None
        self.job = None
        self.phase = 'ready'
        self.status = 'B = one simulated blink' if not device else 'Waiting for stable eye tracking'
        self.heading = 'Stay in the moment.'
        self.subtitle = 'Two blinks. One memory.'
        self.animation = 0.0
        self.simulated_loss_until = 0.0
        self.reset_at = 0.0
        self.capture_due = None
        self.eye = None
        if device:
            from raven_framework.peripherals.eye_control import EyeControl
            self.eye = EyeControl(app_id=os.getenv('RAVEN_APP_ID',''),app_key=os.getenv('RAVEN_APP_KEY',''))
        root = VerticalContainer(width=640,height=640,spacing=10,inner_margin=(20,15),is_main_container=True,background_color='#000000',border_width=0)
        self.view = View(self)
        controls = QWidget()
        controls.setFixedSize(600,120)
        self.pause_button = Button(center_text='Pause',width=160,height=52,text_size=23,background_color='#192B24')
        self.pause_button.setParent(controls)
        self.pause_button.move(440,0)
        self.pause_button.on_clicked(self.toggle_pause)
        self.mode_button = Button(center_text='Use camera',width=190,height=52,text_size=23,background_color='#192B24')
        self.mode_button.setParent(controls)
        self.mode_button.move(240,0)
        self.mode_button.on_clicked(self.toggle_camera)
        self.blink_button = Button(center_text='Blink',width=160,height=52,text_size=23,background_color='#34291A')
        self.blink_button.setParent(controls)
        self.blink_button.move(440,62)
        self.blink_button.on_clicked(self.simulate_blink)
        self.blink_button.setVisible(not device)
        root.add(self.view,controls)
        self.app.add(root)
        self.shortcut = QShortcut(QKeySequence('B'),self)
        self.shortcut.activated.connect(self.simulate_blink)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(20)
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def simulate_blink(self):
        if self.device or not self.armed or self.phase == 'capturing':
            return
        now = self.clock()
        if now < self.simulated_loss_until:
            return
        self.simulated_loss_until = now + 0.13

    def toggle_pause(self):
        if self.phase == 'capturing':
            return
        self.armed = not self.armed
        self.detector.reset()
        self.pause_button.set_text('Pause' if self.armed else 'Resume')
        self.phase = 'ready' if self.armed else 'paused'
        self.heading = 'Stay in the moment.' if self.armed else 'Take your time.'
        self.subtitle = 'Two blinks. One memory.' if self.armed else 'Camera gestures are paused.'
        self.status = 'B = one simulated blink' if self.armed and not self.device else ('Ready' if self.armed else 'Paused')
        self.view.update()

    def toggle_camera(self):
        if self.phase == 'capturing':
            return
        self.demo = not self.demo
        self.photo = None
        self.detector.reset()
        self.mode_button.set_text('Use camera' if self.demo else 'Use demo')
        self.status = 'Demo scene selected' if self.demo else 'Camera will open on capture'
        self.view.update()

    def tick(self):
        now = self.clock()
        self.animation = now
        if self.capture_due is not None and now >= self.capture_due:
            self.capture_due = None
            self.save_photo(self.scene.copy())
        if self.phase == 'saved' and now >= self.reset_at:
            self.phase = 'ready'
            self.heading = 'Another moment?'
            self.subtitle = 'Two blinks when you are ready.'
            self.status = 'B = one simulated blink' if not self.device else 'Ready'
        if self.armed and self.phase != 'capturing':
            tracked = now >= self.simulated_loss_until
            if self.eye:
                try:
                    gaze = self.eye.get_gaze_position()
                    tracked = gaze is not None and len(gaze)==2 and all(math.isfinite(v) and v>=0 for v in gaze)
                except Exception:
                    tracked = False
            if self.detector.sample(tracked,now):
                self.capture()
            elif self.detector.first_blink is not None:
                self.status = 'One blink. Once more.'
            elif self.status == 'One blink. Once more.':
                self.status = 'Ready for two blinks'
        self.view.update()

    def capture(self):
        if not self.armed or self.phase == 'capturing':
            return
        self.phase = 'capturing'
        self.heading = 'Hold that moment.'
        self.subtitle = 'Capturing…'
        self.status = 'Shutter released'
        self.pause_button.set_disabled(True)
        self.mode_button.set_disabled(True)
        if self.demo:
            self.capture_due = self.clock() + 0.18
        else:
            self.job = CameraJob(self)
            self.job.captured.connect(self.save_photo)
            self.job.failed.connect(self.capture_failed)
            self.job.start()

    def save_photo(self,image):
        try:
            self.output.mkdir(parents=True,exist_ok=True)
            name = ('demo-' if self.demo else 'shot-') + time.strftime('%Y%m%d-%H%M%S-') + uuid4().hex[:8]+'.jpg'
            path = self.output/name
            temporary = path.with_suffix('.tmp')
            if not image.save(str(temporary),'JPG',95):
                raise OSError('Could not write photo')
            temporary.replace(path)
            self.photo = image
            self.last_saved = path
            self.phase = 'saved'
            self.heading = 'Moment, kept.'
            self.subtitle = 'Saved to your photo folder.'
            self.status = 'Saved locally  ·  Two blinks to capture again'
            self.reset_at = self.clock()+3
        except Exception as exc:
            self.capture_failed(str(exc))
        self.pause_button.set_disabled(False)
        self.mode_button.set_disabled(False)
        self.view.update()

    def capture_failed(self,message):
        self.phase = 'error'
        self.heading = 'Let’s try again.'
        self.subtitle = 'Camera or storage unavailable.'
        self.status = 'Check permissions, then blink twice'
        self.last_error = message
        print('Capture failed:', message, file=sys.stderr)
        self.detector.reset()
        self.pause_button.set_disabled(False)
        self.mode_button.set_disabled(False)
        self.view.update()

    def shutdown(self):
        self.timer.stop()
        if self.job and self.job.isRunning():
            self.job.wait()

    def closeEvent(self,event):
        self.shutdown()
        super().closeEvent(event)


if __name__ == '__main__':
    from raven_framework.helpers.utils_light import is_raven_device
    device = '--device' in sys.argv or is_raven_device()
    if '--device' in sys.argv:
        sys.argv.remove('--device')
    RunApp.run(lambda:BlinkSnap(device=device),app_id=os.getenv('RAVEN_APP_ID',''),app_key=os.getenv('RAVEN_APP_KEY',''))
