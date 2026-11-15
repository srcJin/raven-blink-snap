"""Render the actual Qt app with deterministic simulated tracking-loss input."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import subprocess
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtCore import QRectF
from main import BlinkSnap

FPS = 25
DURATION = 34
app = QApplication([])
now = [0.0]
with tempfile.TemporaryDirectory() as photos:
    widget = BlinkSnap(output=photos,clock=lambda:now[0])
    widget.timer.stop()
    widget.show()
    app.processEvents()
    target=Path('media')
    target.mkdir(exist_ok=True)
    output=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pixel_format','rgba','-video_size','1280x900','-framerate',str(FPS),'-i','-','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','media/demo-silent.mp4'],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
    actions={125:widget.simulate_blink,136:widget.simulate_blink,275:widget.toggle_pause,350:widget.toggle_pause,460:widget.simulate_blink,471:widget.simulate_blink,700:widget.toggle_pause}
    screens={25:'01-ready.png',134:'02-first-blink.png',150:'03-saved.png',290:'04-paused.png'}
    captions=[(0,'Stay in the moment.','A hands-free camera concept for Raven Prism.'),(4,'Two short tracking losses.','Press B twice to simulate two blinks.'),(6,'Moment, kept.','A photo is saved locally, with clear confirmation.'),(11,'Pause whenever you need.','Gestures only work while the camera is armed.'),(14,'Built for deliberate moments.','Short-loss filtering, recovery checks and a cooldown.'),(18,'Ready for another memory.','The same detector runs in demo and device modes.'),(24,'Your photos stay with you.','Choose Use camera for a real camera capture.'),(28,'BLINKSNAP','Two blinks. One memory.')]
    for frame in range(FPS*DURATION):
        now[0]=frame/FPS
        if frame in actions:
            actions[frame]()
        # 50 Hz polling matches normal app operation.
        widget.tick()
        now[0]+=0.02
        widget.tick()
        app.processEvents()
        shot=widget.app.grab().toImage()
        if frame in screens:
            assert shot.save(str(target/screens[frame]))
        canvas=QImage(1280,900,QImage.Format.Format_RGBA8888)
        canvas.fill(QColor('#07120F'))
        p=QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.drawImage(QRectF(320,45,640,640),shot)
        p.setPen(QColor('#EDC181'))
        p.setFont(QFont('Helvetica',12))
        p.drawText(48,52,'RAVEN MINI HACK  /  BLINKSNAP')
        p.drawText(48,855,'SIMULATOR DEMO · ILLUSTRATED SCENE · NO DEVICE FOOTAGE')
        caption=next(c for c in reversed(captions) if now[0]>=c[0])
        p.setPen(QColor('#ECEAE3'))
        p.setFont(QFont('Helvetica',26,QFont.Weight.Medium))
        p.drawText(320,744,caption[1])
        p.setFont(QFont('Helvetica',16))
        p.setPen(QColor('#9DABA5'))
        p.drawText(320,782,caption[2])
        p.end()
        output.stdin.write(bytes(canvas.constBits()))
    output.stdin.close()
    assert output.wait()==0
    assert len(list(Path(photos).glob('*.jpg')))==2, 'Demo must capture exactly two photos'
    print('Rendered 34 seconds and four app screenshots. Verified two saved photos.')
