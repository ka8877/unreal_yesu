"""Generate original small ambience and Foley WAVs; no sampled third-party sound."""
import argparse, array, json, math, random, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'SourceArt/PathOfDawnUnreal/Audio')
args=parser.parse_args();OUT=args.output_dir.resolve()
protected=[OUT/(name+'.wav') for name in ('A_Water','A_Wind','A_Footstep','A_NetRustle')]+[OUT/'manifest.json']
if any(p.exists() for p in protected):
    raise SystemExit('Existing audio sources preserved. Use --output-dir with a fresh directory and review before replacement.')
OUT.mkdir(parents=True,exist_ok=True)
def source_path(path):
    try:return str(path.relative_to(ROOT))
    except ValueError:return str(path)
RATE=24000

def write(name, seconds, kind):
    rng=random.Random(50311+len(name));data=array.array('h');low=0.;slow=0.
    for i in range(int(RATE*seconds)):
        t=i/RATE;noise=rng.uniform(-1,1);low=.965*low+.035*noise;slow=.999*slow+.001*noise
        if kind=='water':
            tide=.55+.22*math.sin(math.tau*t/4.7)+.12*math.sin(math.tau*t/2.9)
            value=(low*2.4+noise*.035)*tide+math.sin(math.tau*(490+70*math.sin(t*.7))*t)*.008*max(0,math.sin(t*2.7))**8
        elif kind=='wind':value=low*(.65+.35*math.sin(t*.51))+slow*2
        elif kind=='step':
            env=max(0,1-t/seconds)**4;value=(noise*.32+low*4)*env
        else:
            env=math.sin(math.pi*t/seconds)**2;value=(noise*.06+low*.8)*env*(.6+.4*math.sin(t*math.tau*21))
        # Ambient loops crossfade their ends with a periodic envelope; avoid clicks.
        edge=min(1,t/.05,(seconds-t)/.05);value*=max(0,edge)
        data.append(int(max(-.95,min(.95,value))*.55*32767))
    path=OUT/(name+'.wav')
    with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes(data.tobytes())
    return {'file':source_path(path),'asset_id':name,'origin':'Original deterministic noise synthesis, create_audio.py','license':'Project-created sound, no third-party recording','temporary':True,'runtime_path':'/Game/PathOfDawn/Audio/'+name,'limitations':'Provisional synthesized Foley/ambience; no speech or soundtrack'}
manifest=[write('A_Water',12,'water'),write('A_Wind',12,'wind'),write('A_Footstep',.22,'step'),write('A_NetRustle',.8,'net')]
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Generated',len(manifest),'original 24kHz PCM WAVs')
