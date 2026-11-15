"""Drive BlinkSnap in the official visible Raven simulator and use its recorder."""
import argparse
import time
from pathlib import Path
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit
from raven_framework import RunApp
from main import BlinkSnap

ROOT=Path(__file__).resolve().parent

class LiveDemo(BlinkSnap):
    def __init__(self, output, duration=35.72, delay=3, exit_after_save=False):
        super().__init__(output=ROOT/'.demo-photos')
        self.video_output=output.resolve()
        self.video_output.parent.mkdir(parents=True,exist_ok=True)
        self.duration=duration
        self.delay=delay
        self.jobs=[]
        self.ready=False
        self.started=False
        self.saved=False
        self.save_requested=False
        self.exit_after_save=exit_after_save
        self.watch=QTimer(self)
        self.watch.setInterval(50)
        self.watch.timeout.connect(self.watch_ui)
        self.watch.start()

    def schedule(self,seconds,fn):
        timer=QTimer(self)
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.setSingleShot(True)
        timer.timeout.connect(fn)
        timer.start(round(seconds*1000))
        self.jobs.append(timer)

    def watch_ui(self):
        window=self.window()
        if not self.ready and window.isVisible() and 'Raven App' in window.windowTitle():
            self.ready=True
            print('DEMO_READY',flush=True)
            self.schedule(self.delay-0.5,self.record_start)
            self.schedule(self.delay,self.begin)
        if self.save_requested and not self.saved and self.video_output.is_file():
            self.saved=True
            print(f'RECORD_SAVED {self.video_output}',flush=True)
            if self.exit_after_save:
                QTimer.singleShot(200, self.window().close)
        if self.started and not self.save_requested:
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget,QFileDialog) and widget.isVisible() and 'Save recording' in widget.windowTitle():
                    widget.setDirectory(str(self.video_output.parent))
                    widget.selectFile(self.video_output.name)
                    name_edit=widget.findChild(QLineEdit,'fileNameEdit')
                    if name_edit is not None:
                        name_edit.setText(self.video_output.name)
                    self.save_requested=True
                    widget.accept()

    def record_start(self):
        self.window()._record_button.click()
        print(f'RECORD_T0 monotonic_ns={time.monotonic_ns()}',flush=True)

    def begin(self):
        self.started=True
        print(f'DEMO_T0 monotonic_ns={time.monotonic_ns()}',flush=True)
        for seconds,action in [(5,self.simulate_blink),(5.44,self.simulate_blink),(11,self.toggle_pause),(14,self.toggle_pause),(18.4,self.simulate_blink),(18.84,self.simulate_blink),(28,self.toggle_pause)]:
            self.schedule(seconds,action)
        self.schedule(self.duration,self.end)

    def end(self):
        self.window()._record_button.click()
        print(f'RECORD_STOP monotonic_ns={time.monotonic_ns()}',flush=True)
        self.timer.stop()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-output',type=Path,default=ROOT/'media/official-simulator-raw.mp4')
    parser.add_argument('--duration',type=float,default=35.72)
    parser.add_argument('--exit-after-save',action='store_true')
    args=parser.parse_args()
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs,True)
    RunApp.run(lambda:LiveDemo(args.record_output,duration=args.duration,exit_after_save=args.exit_after_save),app_id='',app_key='')
