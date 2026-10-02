import asyncio, json, os, subprocess
from pathlib import Path
import edge_tts

ROOT=Path(__file__).resolve().parent
STORY=json.loads((ROOT/'story.json').read_text())
(ROOT/'audio').mkdir(exist_ok=True)

async def main():
    sem=asyncio.Semaphore(3)
    async def one(i,s):
        async with sem:
            path=ROOT/'audio'/f'voice_{i:02d}.mp3'
            if not path.exists() or path.stat().st_size<1000:
                for trial in range(3):
                    try:
                        c=edge_tts.Communicate(s['voice'],'zh-CN-YunxiNeural',rate='-3%',pitch='-3Hz',proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'))
                        await asyncio.wait_for(c.save(str(path)),90)
                        break
                    except Exception:
                        if trial==2: raise
            duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)]))
            target=s['end']-s['start']-2.0
            tempo=max(1.0,duration/target)
            out=ROOT/'audio'/f'voice_{i:02d}.wav'
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-af',f'atempo={tempo:.6f},highpass=f=80,lowpass=f=12000','-ar','48000','-ac','1',str(out)],check=True)
            actual=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(out)]))
            s['voice_start']=s['start']+1.15
            s['voice_duration']=actual
            print(f'{i:02d}: {duration:.2f}s -> {actual:.2f}s; speed {tempo:.2f}',flush=True)
    await asyncio.gather(*(one(i,s) for i,s in enumerate(STORY['scenes'])))
    (ROOT/'timing.json').write_text(json.dumps(STORY,ensure_ascii=False,indent=2))

asyncio.run(main())
