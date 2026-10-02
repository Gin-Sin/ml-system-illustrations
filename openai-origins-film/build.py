"""Build the film from original source, including embedded chapter markers."""
import argparse, concurrent.futures, json, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def run(cmd,**kw):
    subprocess.run(cmd,cwd=ROOT,check=True,**kw)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--jobs',type=int,default=4);parser.add_argument('--picture-only',action='store_true');args=parser.parse_args()
    if not (ROOT/'timing.json').exists():run([sys.executable,'make_voice.py'])
    if not (ROOT/'audio'/'master.wav').exists():run([sys.executable,'make_audio.py'])
    story=json.loads((ROOT/'timing.json').read_text())
    def chunk(i):
        with (ROOT/f'render-{i}.log').open('w') as log:
            run([sys.executable,'render.py','--start',str(i*30),'--end',str((i+1)*30),'--output',f'part-{i}.mp4'],stdout=log,stderr=subprocess.STDOUT)
        print(f'Picture segment {i+1}/4 ready.',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(chunk,range(4)))
    (ROOT/'concat.txt').write_text(''.join(f"file 'part-{i}.mp4'\n" for i in range(4)))
    meta=';FFMETADATA1\ntitle=向所有人 | OpenAI: A Light for Everyone\nartist=Original procedural film\ncomment=Original script, animation, score and effects. Selected milestones 2015-2024. Synthetic Chinese narration.\n'
    for s in story['scenes']:
        meta+=f"\n[CHAPTER]\nTIMEBASE=1/1000\nSTART={s['start']*1000}\nEND={s['end']*1000}\ntitle={s['year']} {''.join(s['title'])}\n"
    (ROOT/'chapters.ffmeta').write_text(meta)
    run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i','concat.txt','-i','audio/master.wav','-i','chapters.ffmeta','-map','0:v:0','-map','1:a:0','-map_metadata','2','-map_chapters','2','-c:v','copy','-c:a','aac','-b:a','320k','-ar','48000','-t','120','-movflags','+faststart','openai-a-light-for-everyone.mp4'])
    print('FINAL FILM READY: openai-a-light-for-everyone.mp4',flush=True)

if __name__=='__main__':main()
