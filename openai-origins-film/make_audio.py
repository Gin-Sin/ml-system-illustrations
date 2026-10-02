"""Compose a new 120-second stereo score and synchronize bespoke effects + VO."""
import json, math, subprocess
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT=Path(__file__).resolve().parent
STORY=json.loads((ROOT/'timing.json').read_text())
SR=48000;DURATION=120;N=SR*DURATION
rng=np.random.default_rng(20261002)
music=np.zeros((N,2),dtype=np.float32)
fx=np.zeros_like(music);voice=np.zeros_like(music)

def freq(note):return 440*2**((note-69)/12)
def add(dest,wave,start,amp=1,pan=0):
    i=round(start*SR)
    if i<0:wave=wave[-i:];i=0
    length=min(len(wave),len(dest)-i)
    if length<=0:return
    wave=wave[:length]*amp
    if wave.ndim==1:
        dest[i:i+length,0]+=wave*np.sqrt((1-pan)/2)
        dest[i:i+length,1]+=wave*np.sqrt((1+pan)/2)
    else:dest[i:i+length]+=wave

def piano(note,dur=3.8,vel=1):
    t=np.arange(int(SR*dur),dtype=np.float32)/SR;f=freq(note)
    y=np.zeros_like(t)
    for h,a in [(1,1),(2,.37),(3,.17),(4.008,.075),(5.015,.045),(7.021,.024)]:
        y+=a*np.sin(2*np.pi*f*h*t+.12*h)*np.exp(-t*(.75+h*.37))
    y*=np.minimum(t/.006,1)*np.minimum((dur-t)/.08,1)
    return y*vel*.34

def pad(notes,dur,brightness=.45):
    t=np.arange(int(SR*dur),dtype=np.float32)/SR
    out=np.zeros((len(t),2),np.float32)
    env=np.minimum(t/1.3,1)*np.minimum((dur-t)/1.8,1)
    for j,note in enumerate(notes):
        f=freq(note)
        for ch in range(2):
            phase=(j*.53+ch*.38)
            for det,gain in [(-.0013,.32),(0,.42),(.0011,.26)]:
                wave=np.sin(2*np.pi*f*(1+det+ch*.0003)*t+phase)
                wave+=brightness*.17*np.sin(2*np.pi*f*2*(1+det)*t+phase)
                wave+=brightness*.06*np.sin(2*np.pi*f*3*(1+det)*t)
                out[:,ch]+=wave*gain
    out*=env[:,None]*(.025/len(notes))*(.86+.14*np.sin(t*.6))[:,None]
    return out

def kick():
    t=np.arange(int(SR*.55),dtype=np.float32)/SR
    phase=2*np.pi*(44*t+2.8*(1-np.exp(-t*22)))
    return np.sin(phase)*np.exp(-t*9)*np.minimum(t/.004,1)*.25

def noise_tick(dur=.06):
    n=rng.normal(0,1,int(SR*dur)).astype(np.float32)
    n=signal.sosfilt(signal.butter(2,6800,'highpass',fs=SR,output='sos'),n).astype('f4')
    t=np.arange(len(n))/SR
    return n*np.exp(-t*65)*.06

def intensity(t):
    return float(np.interp(t,[0,10,23,35,47,59,74,86,98,110,118,120],[.12,.24,.40,.58,.68,.88,.9,.37,.74,.43,.05,0]))

# Harmonic arc: D minor / B-flat major / F major / C suspended, resolving in D major.
chords=[[50,57,60,64,69],[46,53,57,60,65],[48,53,57,64,67],[48,55,60,62,67]]
for bar in range(24):
    t=bar*5
    notes=chords[bar%4] if bar<22 else ([50,57,62,66,69] if bar==22 else [50,57,62,66,73])
    add(music,pad(notes,7.6,intensity(t)),t,1.1+intensity(t)*1.8)
    add(music,piano(notes[0]-12,5.2),t+.03,.10+intensity(t)*.13,-.08)

# A memorable four-note motif, with octave and voicing changes across the film.
motifs=[[74,69,65,64],[74,77,72,69],[72,69,65,67],[67,74,72,69]]
for bar in range(24):
    start=bar*5;seq=motifs[bar%4]
    if bar>=22:seq=[74,78,81,85]
    for j,n in enumerate(seq):
        if bar<2 and j%2:continue
        t=start+.15+j*1.25
        wave=piano(n,4.2)
        amp=.15+intensity(t)*.14
        pan=math.sin(j*1.8+bar)*.25
        add(music,wave,t,amp,pan)
        add(music,wave,t+.375,amp*.21,-pan)
        add(music,wave,t+.75,amp*.09,pan)

# Eighth-note glass arpeggios, entering gradually with the growth of the story.
for step in range(int(110/.3125)):
    t=10+step*.3125
    if t>=111:break
    it=intensity(t);ch=chords[int(t//5)%4]
    if t<23 and step%4:continue
    if 86<t<98 and step%4:continue
    note=ch[[0,2,3,4,2,1,3,2][step%8]]+24
    pl=piano(note,1.3)
    add(music,pl,t,.033+it*.037,math.sin(step*.65)*.65)

# Soft cinematic pulse and restrained high-frequency motion.
k=kick()
for beat in range(192):
    t=beat*.625
    if 23<=t<86 or 99<=t<111:
        it=intensity(t)
        if beat%2==0:add(music,k,t,(.22+it*.35)*(1 if beat%4==0 else .70),0)
        if beat%2==1:add(music,noise_tick(),t,.25+it*.30,(-.35 if beat%4==1 else .35))

# A spacious algorithmic reverb: irregular, filtered, cross-channel early reflections.
dry=music.copy()
for delay,gain in [(.083,.21),(.149,.17),(.271,.15),(.433,.11),(.719,.083),(1.071,.055),(1.619,.032)]:
    shift=int(SR*delay)
    music[shift:]+=dry[:-shift,::-1]*gain
del dry

# Custom transition whooshes, sub drops and crystalline impacts.
for i,s in enumerate(STORY['scenes']):
    start=s['start']
    if i:
        dur=1.85;t=np.arange(int(dur*SR),dtype=np.float32)/SR
        noise=rng.normal(0,1,len(t)).astype('f4')
        noise=signal.sosfilt(signal.butter(2,[500,6500],'bandpass',fs=SR,output='sos'),noise).astype('f4')
        env=np.sin(np.pi*t/dur)**2
        # Swept tonal edge keeps the transition intentional and musical.
        swept=np.sin(2*np.pi*(140*t+720*t*t))*.08
        whoosh=(noise*.17+swept)*env
        motion=np.linspace(-.75,.75,len(t))
        stereo=np.column_stack([whoosh*np.sqrt((1-motion)/2),whoosh*np.sqrt((1+motion)/2)])
        add(fx,stereo,start-1.22,.46 if i!=5 else .8)
        dur=2.2;t=np.arange(int(dur*SR),dtype=np.float32)/SR
        impact=np.sin(2*np.pi*(38*t+3.8*(1-np.exp(-t*10))))*np.exp(-t*3.8)*np.minimum(t/.004,1)
        add(fx,impact,start,.12 if i!=5 else .23)
        add(fx,piano(86 if i!=5 else 81,3.5),start+.04,.21,.25)

# Opening light, constellation ticks, and the first typed conversation.
add(fx,piano(86,5),.8,.19,-.2)
for i in range(8):add(fx,piano([86,81,77,74][i%4],1.5),11.2+i*.33,.07,math.sin(i)*.55)
for start,count,spacing in [(61.1,12,.116),(64.4,21,.10)]:
    for j in range(count):add(fx,noise_tick(.025),start+j*spacing,.2,math.sin(j)*.12)
add(fx,piano(81,4),65.05,.12,.3)
add(fx,piano(86,4),98.05,.15,-.3)

# Narration stays centered; score ducks smoothly under every spoken segment.
duck=np.ones(N,dtype=np.float32)
subtitle=[]
for i,s in enumerate(STORY['scenes']):
    sr,a=wavfile.read(ROOT/'audio'/f'voice_{i:02d}.wav')
    assert sr==SR
    a=a.astype(np.float32)/32768
    rms=float(np.sqrt(np.mean(a*a)))
    a*=.112/max(.001,rms)
    a=np.tanh(a*1.05)*.93
    st=s['voice_start'];en=st+len(a)/SR
    add(voice,a,st,1.0,0)
    i0=max(0,int((st-.28)*SR));i1=min(N,int((en+.42)*SR))
    tt=np.arange(i0,i1)/SR
    e=np.minimum(np.clip((tt-(st-.28))/.28,0,1),np.clip((en+.42-tt)/.42,0,1))
    duck[i0:i1]=np.minimum(duck[i0:i1],1-.52*e)
    caps=s['captions'];total=sum(map(len,caps));cursor=st
    for cap in caps:
        end=cursor+s['voice_duration']*len(cap)/total
        subtitle.append((cursor,end,cap));cursor=end

def timestamp(t):
    ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
(ROOT/'captions.srt').write_text('\n\n'.join(f'{i+1}\n{timestamp(st)} --> {timestamp(en)}\n{txt}' for i,(st,en,txt) in enumerate(subtitle))+'\n')

# Fade all tails into silence at the final frame, and avoid any discontinuity.
fade=np.minimum(np.arange(N)/(SR*1.3),1).astype('f4')
fade*=np.minimum((N-1-np.arange(N))/(SR*3.5),1).astype('f4')
music*=fade[:,None];fx*=fade[:,None];voice*=fade[:,None]
mix=music*duck[:,None]+fx*.62+voice

def export(name,a):
    path=ROOT/'audio'/name
    peak=float(np.max(np.abs(a)))
    wavfile.write(path,SR,a.astype('f4'))
    print(f'{name}: peak={peak:.4f}, RMS={np.sqrt(np.mean(a*a)):.4f}',flush=True)

export('score.wav',music)
export('effects.wav',fx)
export('narration.wav',voice)
export('mix_raw.wav',mix)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(ROOT/'audio'/'mix_raw.wav'),'-af','loudnorm=I=-16:TP=-1.3:LRA=9','-ar','48000','-c:a','pcm_s24le',str(ROOT/'audio'/'master.wav')],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(ROOT/'audio'/'score.wav'),'-af','loudnorm=I=-18:TP=-1.5:LRA=11','-ar','48000','-c:a','libmp3lame','-b:a','256k',str(ROOT/'original-score.mp3')],check=True)
print('Original composition, effects, voice mix and captions are ready.',flush=True)
