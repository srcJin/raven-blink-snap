"""Record the official visible Raven simulator; no custom video composition."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DURATION=35.72

def capture():
    audio=ROOT/'media/narration.wav'
    if not audio.exists():
        raise SystemExit('Generate Cartesia narration first: node narrate.mjs')
    duration=max(34,float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(audio)],text=True).strip())+0.5)
    with tempfile.TemporaryDirectory(prefix='blinksnap-official-') as folder:
        recording=Path(folder)/'official.mp4'
        result=subprocess.run([sys.executable,str(ROOT/'live_demo.py'),'--record-output',str(recording),'--exit-after-save','--duration',str(duration)],cwd=ROOT,text=True,capture_output=True,timeout=90)
        print(result.stdout,end='')
        if result.returncode or not recording.exists():
            print(result.stderr,file=sys.stderr)
            raise SystemExit('Official simulator recording failed')
        record_ns=int(re.search(r'RECORD_T0 monotonic_ns=(\d+)',result.stdout)[1])
        demo_ns=int(re.search(r'DEMO_T0 monotonic_ns=(\d+)',result.stdout)[1])
        offset=(demo_ns-record_ns)/1e9
        silent=ROOT/'media/demo-silent.mp4'
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(offset),'-i',str(recording),'-t',str(duration),'-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(silent)],check=True)
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(audio),'-map','0:v','-map','1:a','-af','apad','-t',str(duration),'-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(ROOT/'media/demo.mp4')],check=True)
        print('Created official simulator video with English narration.')

if __name__=='__main__':
    capture()
