"""Original v8 character sculptures. Blender 4.3+, CPU preview, no third-party geometry.
Usage: blender -b --python Tools/PathOfDawnUnreal/create_characters_v8.py -- --render
Existing outputs are preserved; review iterations must use a new --output-dir.
Static, unrigged medium-distance characters, not photorealistic scanned actors.
"""
import argparse, bpy, math, json, sys, random
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output-dir',type=Path,default=R/'SourceArt/PathOfDawnUnreal/VisualV8/Models')
p.add_argument('--render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=a.output_dir.resolve();OUT.mkdir(parents=True,exist_ok=True)
ids=['SM_Jesus','SM_Simon','SM_Traveler']
protected=[OUT/(n+'.fbx') for n in ids]+[OUT/'CharactersV8.blend',OUT/'characters-manifest.json']+list(OUT.glob('CharacterPreview*.png'))
if any(path.exists() for path in protected):raise SystemExit('Existing sources preserved: choose a fresh --output-dir.')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
random.seed(51108)
def mat(n,c,r=.85):
 m=bpy.data.materials.new('V8_'+n);m.diffuse_color=(*c,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=r
 return m
M={
 'skin':mat('OliveSkin',(.33,.198,.118),.7),'simon_skin':mat('WeatheredSkin',(.29,.166,.094),.78),
 'traveler_skin':mat('TravelerSkin',(.38,.236,.145),.75),'lip':mat('NaturalLip',(.29,.128,.086)),
 'hair':mat('ChestnutHair',(.041,.024,.016)), 'hair_hi':mat('ChestnutRidges',(.049,.028,.018)),
 'simon_hair':mat('WeatheredHair',(.071,.058,.039)),'grey':mat('GreyBeard',(.19,.16,.108)),
 'iris':mat('BrownIris',(.08,.046,.022),.48),'pupil':mat('Pupil',(.009,.007,.005),.35),
 'white':mat('WarmSclera',(.43,.385,.30),.45),'crease':mat('FaceCrease',(.15,.066,.04)),
 'linen':mat('IvoryLinen',(.55,.47,.33)),'blue':mat('DustyBlueMantle',(.045,.082,.107)),
 'traveler':mat('TravelerBlue',(.10,.15,.16)),'olive':mat('SimonOliveLinen',(.19,.21,.105)),
 'brown':mat('SimonBrownMantle',(.15,.08,.035)),'belt':mat('BraidedFlax',(.33,.258,.16)),
 'leather':mat('WornLeather',(.15,.087,.044)),'strap':mat('LeatherStrap',(.255,.152,.074)),
 'seam':mat('LinenHem',(.49,.423,.307)), 'traveler_linen':mat('TravelerUndertunic',(.34,.32,.25)),
}
PARTS=[]
def mesh(n,verts,faces,ma,smooth=True):
 me=bpy.data.meshes.new(n);me.from_pydata(verts,[],faces);me.update()
 o=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(o);o.data.materials.append(ma)
 for f in me.polygons:f.use_smooth=smooth
 PARTS.append(o);return o

def interp(keys,t):
 for (x,y),(xx,yy) in zip(keys,keys[1:]):
  if t<=xx:return y+(yy-y)*max(0,(t-x)/(xx-x))
 return keys[-1][1]

def tube(n,pts,radii,ma,segments=10,flat=1):
 vs=[];fs=[]
 for j,point in enumerate(pts):
  point=Vector(point);dr=Vector(pts[min(j+1,len(pts)-1)])-Vector(pts[max(0,j-1)])
  dr.normalize();ref=Vector((0,1,0))
  if abs(dr.dot(ref))>.96:ref=Vector((1,0,0))
  ax=dr.cross(ref).normalized();ay=dr.cross(ax).normalized()
  for i in range(segments):
   ang=math.tau*i/segments;vs.append(point+radii[j]*(math.cos(ang)*ax+flat*math.sin(ang)*ay))
 for j in range(len(pts)-1):
  for i in range(segments):
   q=j*segments+i;r=j*segments+(i+1)%segments;fs.append((q,r,r+segments,q+segments))
 fs.append(tuple(reversed(range(segments))));fs.append(tuple(range((len(pts)-1)*segments,len(pts)*segments)))
 return mesh(n,vs,fs,ma)

def sph(n,loc,sc,ma,seg=24,rings=16):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc);o=bpy.context.object;o.name=n;o.scale=sc
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
 for f in o.data.polygons:f.use_smooth=True
 PARTS.append(o);return o

def facey(x,z,wide=1):
 # Front surface is continuously sculpted; nose, cheek, chin and brows share head topology.
 def g(cx,cz,sx,sz):return math.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)
 y=interp([(1.51,-.036),(1.54,-.066),(1.57,-.082),(1.61,-.087),(1.65,-.086),(1.69,-.081),(1.73,-.080),(1.77,-.061),(1.80,0)],z)
 width=interp([(1.51,.015),(1.54,.065),(1.58,.082),(1.64,.098),(1.70,.093),(1.75,.083),(1.79,.025),(1.80,.003)],z)*wide
 y*=math.sqrt(max(.02,1-(x/max(width,.002))**2))
 y-=.014*g(0,1.666,.012,.036)+.032*g(0,1.630,.014,.012)
 y-=.009*g(-.013,1.624,.009,.008)+.009*g(.013,1.624,.009,.008)
 y-=.006*g(0,1.592,.032,.011)+.008*g(0,1.548,.035,.015)
 for side in [-1,1]:
  y+=.006*g(side*.037*wide,1.680,.023,.013)
  y-=.010*g(side*.042*wide,1.700,.027,.010)
  y-=.009*g(side*.052*wide,1.652,.025,.025)
 return y

def head(kind,skin,hair,wide=1):
 vs=[];fs=[];N=112;Z=75
 for j in range(Z+1):
  z=1.511+(1.799-1.511)*j/Z
  width=interp([(1.511,.005),(1.54,.065),(1.58,.082),(1.64,.098),(1.70,.093),(1.75,.083),(1.79,.025),(1.799,.002)],z)*wide
  back=interp([(1.511,.018),(1.54,.055),(1.60,.09),(1.69,.106),(1.75,.084),(1.799,.003)],z)
  for i in range(N):
   ang=math.tau*i/N;x=math.sin(ang)*width
   y=facey(x,z,wide) if math.cos(ang)>=0 else -math.cos(ang)*back
   vs.append((x,y,z))
 for j in range(Z):
  for i in range(N):
   k=j*N+i;l=j*N+(i+1)%N;fs.append((k,l,l+N,k+N))
 mesh('ContinuousSculptedHead',vs,fs,skin)
 tube('Neck',[(0,.012,1.427),(0,.012,1.485),(0,.013,1.535)],[.085,.064,.061],skin,32)
 for s in [-1,1]:
  # Ears lie close to the skull; helix is one swept ridge, no ornament-like spheres.
  sph('Ear',(s*.096*wide,.008,1.654),(.016,.018,.033),skin,20,14)
  pts=[]
  for j in range(25):
   ang=-.9+4.5*j/24;pts.append((s*(.105*wide+.008*math.cos(ang)),-.003-.006*math.cos(ang),1.654+.026*math.sin(ang)))
  tube('EarHelix',pts,[.003]*len(pts),skin,6)
  cx=s*.038*wide;cz=1.679
  # Almond eye surface and upper/lower lids, restrained scale and no protruding eyeballs.
  vs=[];fs=[]
  for j in range(9):
   v=-1+2*j/8
   for i in range(25):
    u=-1+2*i/24;x=cx+.013*u;zz=cz+.0036*v*(max(0,1-u*u)**.65)+s*u*.0014
    yy=facey(x,zz,wide)-.0015-.003*max(0,1-u*u)*(1-v*v)
    vs.append((x,yy,zz))
  for j in range(8):
   for i in range(24):k=j*25+i;fs.append((k,k+1,k+26,k+25))
  mesh('AlmondEye',vs,fs,M['white'])
  y=facey(cx,cz,wide)-.006
  ivs=[(cx,y-.001,cz)];ifs=[]
  for j in range(48):
   ang=math.tau*j/48;ix=.0045*math.cos(ang);iz=.0045*math.sin(ang);clip=.0036*(1-(ix/.013)**2)**.65
   ivs.append((cx+ix,y-.0005,cz+max(-clip,min(clip,iz))))
  for j in range(48):ifs.append((0,1+j,1+(j+1)%48))
  mesh('LidClippedIris',ivs,ifs,M['iris'])
  sph('Pupil',(cx,y-.001,cz),(.0022,.0008,.0025),M['pupil'],16,8)
  for upper in [-1,1]:
   pts=[]
   for j in range(25):
    u=-1+2*j/24;x=cx+.0134*u;zz=cz+upper*.0037*(max(0,1-u*u)**.65)+s*u*.0014
    pts.append((x,facey(x,zz,wide)-.0022,zz))
   tube('UpperLid' if upper==1 else 'LowerLid',pts,[.00085 if upper==1 else .0006]*25,skin,6)
  brow=[]
  for j in range(18):
   t=j/17;x=s*(.018+.045*t)*wide;z=1.699+.004*math.sin(t*math.pi)-.004*t
   brow.append((x,facey(x,z,wide)-.0025,z))
  tube('Eyebrow',brow,[.0004+.0014*math.sin(math.pi*j/17)**.7 for j in range(18)],hair,8,flat=.55)
  # Very small nostril creases integrated immediately below nose wings.
  pts=[]
  for j in range(9):
   t=j/8;x=s*(.008+.010*t);z=1.622-.0025*math.sin(t*math.pi)
   pts.append((x,facey(x,z,wide)-.001,z))
  tube('Nostril',pts,[.00085]*9,M['crease'],6,.45)
 # Lips form gentle shaped tissue and a tiny closed mouth seam.
 for top in [True,False]:
  pts=[]
  for j in range(29):
   t=-1+2*j/28;x=.027*t;z=1.593+(.0035*(1-t*t)-.0015*math.exp(-(t/.23)**2) if top else -.0025*(1-t*t))
   pts.append((x,facey(x,z,wide)-.001,z))
  tube('UpperLip' if top else 'LowerLip',pts,[.00025+.0010*(1-(-1+2*j/28)**2) for j in range(29)],M['lip'],6,.65)
 pts=[]
 for j in range(25):
  x=-.025+.05*j/24;z=1.5925-.0005*math.cos(x*80);pts.append((x,facey(x,z,wide)-.0027,z))
 tube('Mouth',pts,[.00055]*25,M['crease'],6,.4)
 # Beard is a continuous shaped jaw surface, not a separate oval attached to the face.
 if kind!='Traveler':
  vs=[];fs=[];NX=48;NZ=16
  for j in range(NZ+1):
   t=j/NZ
   for i in range(NX+1):
    q=-1+2*i/NX;x=q*(.077+.009*t)*wide
    bottom=(1.514 if kind=='Jesus' else 1.532)+(.049 if kind=='Jesus' else .031)*abs(q)**1.6;top=1.568+.083*abs(q)**2
    z=bottom+(top-bottom)*t;y=facey(x,max(z,1.521),wide)-.005-.007*(1-t)*max(0,1-q*q)
    vs.append((x,y,z))
  for j in range(NZ):
   for i in range(NX):k=j*(NX+1)+i;fs.append((k,k+1,k+NX+2,k+NX+1))
  mesh('ContouredBeard',vs,fs,hair)
  for k in range(73):
   q=-.96+1.92*k/72;x=q*.080*wide;top=1.568+.083*abs(q)**2;bottom=(1.514 if kind=='Jesus' else 1.532)+(.049 if kind=='Jesus' else .031)*abs(q)**1.6
   pts=[]
   for j in range(12):
    t=j/11;xx=x*(1-.12*t)+.0012*math.sin(t*12+k);z=top+(bottom-top)*t
    pts.append((xx,facey(xx,max(z,1.521),wide)-.010-.004*math.sin(t*math.pi),z))
   tube('BeardFlow',pts,[.00075*math.sin(math.pi*(j+.5)/12)**.7 for j in range(12)],M['grey'] if kind=='Simon' and k%7==0 else M['hair_hi'] if k%3==0 else hair,5,.45)
  for s in [-1,1]:
   pts=[]
   for j in range(18):
    t=j/17;x=s*(.003+.032*t);z=1.610-.014*t+.001*math.sin(t*math.pi)
    pts.append((x,facey(x,z,wide)-.0035,z))
   tube('Moustache',pts,[.0006+.0020*math.sin(math.pi*(j+.8)/19) for j in range(18)],hair,8,.5)
 # Scalp shell, back and sides; the front hairline is deliberately swept away from eyes.
 vs=[];fs=[];NN=96;HH=32
 for j in range(HH+1):
  t=j/HH
  for i in range(NN):
   ang=math.tau*i/NN;front=max(0,math.cos(ang))
   low=(1.485+.262*(front**.30) if kind=='Jesus' else 1.60+.147*(front**.45)) if kind!='Simon' else 1.675+.071*(front**.55)
   low+=.0025*math.sin(13*ang)
   z=low+(1.807-low)*t
   shape=math.sqrt(max(.00015,1-(max(0,z-1.665)/.143)**2))
   w=(.104*shape+.0017*math.sin(31*ang+z*11))*wide
   d=.112*shape+.0017*math.sin(31*ang+z*11)
   vs.append((w*math.sin(ang),-.96*d*math.cos(ang)+.006,z))
 for j in range(HH):
  for i in range(NN):k=j*NN+i;l=j*NN+(i+1)%NN;fs.append((k,l,l+NN,k+NN))
 mesh('NaturalHairVolume',vs,fs,hair)
 # Long layered locks have ribbon cross sections and flowing paths; short cropped locks for Simon.
 for side in [-1,1]:
  for k in range(18 if kind!='Simon' else 20):
   phase=k/17;pts=[];length= (.25 if kind=='Jesus' else .17)+.018*math.sin(k*1.8) if kind!='Simon' else .062+.008*math.sin(k)
   for j in range(22):
    t=j/21
    if kind!='Simon':
     x=side*(.013+.080*math.sin(min(1,t*2)*math.pi/2)+.014*phase+.006*math.sin(t*9+k))
     y=-.065+.17*phase-.021*math.sin(t*3)+.006*math.sin(t*8+k)
     z=1.793-.018*phase-length*t
    else:
     ang=side*(.2+2.8*phase);z=1.795-length*t
     rad=.032+.052*math.sin(t*1.45);x=rad*math.sin(ang)*wide;y=-rad*math.cos(ang)+.01
     x+=.002*math.sin(t*18+k);y+=.002*math.cos(t*18+k)
    pts.append((x,y,z))
   tube('SweptHairLock',pts,[.001+.008*math.sin(math.pi*(j+.8)/23)**.7 for j in range(22)],M['hair_hi'] if k%4==0 else hair,7,.42)

def robe(kind,cloth):
 vs=[];fs=[];N=80;K=55;wide=1.11 if kind=='Simon' else .94 if kind=='Traveler' else 1
 for j in range(K+1):
  t=j/K;z=.135+1.355*t
  rx=interp([(.135,.240),(.35,.234),(.70,.214),(1.0,.177),(1.085,.171),(1.22,.204),(1.36,.235),(1.415,.216),(1.490,.070)],z)*wide
  ry=interp([(.135,.175),(.50,.160),(1.03,.133),(1.10,.131),(1.32,.155),(1.43,.109),(1.490,.065)],z)
  for i in range(N):
   ang=math.tau*i/N
   amp=.006+.009*max(0,1-(z-.25)/.92)
   fold=amp*(math.sin(11*ang+.4*math.sin(z*5))+.46*math.sin(19*ang-z*1.4)+.24*math.sin(31*ang+z*3))
   waistwrinkle=.006*math.exp(-((z-1.04)/.10)**2)*math.sin(43*z+4*ang)
   x=(rx+fold+waistwrinkle)*math.cos(ang)+.006*math.sin(z*3)
   y=(ry+fold+waistwrinkle)*math.sin(ang)
   zz=z+.006*math.sin(7*ang)*math.exp(-((z-.135)/.13)**2)
   vs.append((x,y,zz))
 for j in range(K):
  for i in range(N):k=j*N+i;l=j*N+(i+1)%N;fs.append((k,l,l+N,k+N))
 mesh('LinenRobeSculptedFolds',vs,fs,cloth)
 # Rolled collar rather than a hard cylinder neckline.
 pts=[(.067*math.cos(math.tau*i/64),.065*math.sin(math.tau*i/64),1.49) for i in range(65)]
 tube('CollarStitch',pts,[.003]*len(pts),M['seam'],6)
 # Slightly bent resting arms with continuous curved sleeves and compression creases.
 for s in [-1,1]:
  vs=[];fs=[];NN=40;JJ=34
  for j in range(JJ+1):
   t=j/JJ;z=1.427-.448*t;cx=s*(.178*wide+.085*math.sin(t*math.pi*.72));cy=-.015-.082*t*t
   r=interp([(0,.022),(.13,.081),(1,.049)],t)
   for i in range(NN):
    ang=math.tau*i/NN
    wrinkle=.0023*math.sin(8*ang+2*t)+.004*math.sin(55*t+2*ang)*math.exp(-((t-.55)/.21)**2)
    vs.append((cx+(r+wrinkle)*math.cos(ang),cy+(r+wrinkle)*math.sin(ang),z+.012*math.cos(ang)*s))
  for j in range(JJ):
   for i in range(NN):k=j*NN+i;l=j*NN+(i+1)%NN;fs.append((k,l,l+NN,k+NN))
  mesh('SoftBentLinenSleeve',vs,[tuple(reversed(f)) for f in fs],cloth)
  skin=M['simon_skin'] if kind=='Simon' else M['traveler_skin'] if kind=='Traveler' else M['skin']
  wrist=Vector((s*(.178*wide+.085*math.sin(math.pi*.72)),-.097,.977))
  # Palm and individually bent fingers are small and proportional.
  sph('NaturalPalm',wrist+Vector((s*.005,-.008,-.039)),(.030,.018,.052),skin,28,18)
  for f in range(4):
   x=wrist.x+s*(-.022+.014*f);length=[.050,.062,.058,.043][f];pts=[]
   for j in range(9):
    t=j/8;pts.append((x+s*.005*t,wrist.y-.005-.013*math.sin(t*math.pi*.7),wrist.z-.066-length*t))
   tube('BentFinger',pts,[.007*(1-.55*j/8) for j in range(9)],skin,8)
  pts=[tuple(wrist+Vector((-s*.026,-.003,-.018))),tuple(wrist+Vector((-s*.043,-.010,-.041))),tuple(wrist+Vector((-s*.044,-.027,-.061)))]
  tube('RelaxedThumb',pts,[.012,.010,.006],skin,10)
 # Woven waist cord and two irregular loose ends.
 for strand in range(2):
  pts=[]
  for i in range(145):
   ang=math.tau*i/144;pts.append((.180*wide*math.cos(ang),.141*math.sin(ang),1.065+.003*math.sin(ang*33+strand*math.pi)))
  tube('TwistedWaistCord',pts,[.0026]*len(pts),M['belt'],6)
 for s in [-1,1]:
  pts=[]
  for j in range(22):
   t=j/21;pts.append((.025+s*.015*t+.012*math.sin(t*4),-.151-.008*math.sin(t*3),1.064-.22*t))
  tube('HangingCord',pts,[.003]*22,M['belt'],7)
 # Soft leather sandals and low feet with open toes.
 for s in [-1,1]:
  x=s*.105;y=-.025
  sph('SandalSole',(x,y-.041,.028),(.060,.132,.022),M['leather'],32,16)
  sph('Foot',(x,y-.035,.060),(.050,.110,.035),skin,28,16)
  tube('Ankle',[(x,y+.019,.060),(x,y+.02,.17)],[.038,.040],skin,22)
  for f in range(5):
   sph('Toe',(x+s*(-.035+.016*f),y-.125+.007*f,.052),(.010,.025-.002*f,.012),skin,14,10)
  for zz,yy in [(0,-.075),(.009,-.012)]:
   pts=[]
   for j in range(17):
    t=-1+2*j/16;pts.append((x+.051*t,y+yy,.067+zz+.014*math.sqrt(max(0,1-t*t))))
   tube('SandalStrap',pts,[.006]*17,M['strap'],8,.4)

def mantle(kind):
 ma=M['blue'] if kind=='Jesus' else M['brown'] if kind=='Simon' else M['traveler']
 # Broad, asymmetric cloth wraps the shoulder and chest, curving around the body's sides.
 def point(t,q,back):
  z=1.467-1.20*t
  center=-.110+.07*math.sin(math.pi*min(1,t*2))-.06*t
  width=.114+.085*math.sin(math.pi*min(1,t*1.5))
  if back:
   center=-.110*(1-min(1,t*4));width+=.075*math.sin(math.pi*t)**.6
  if kind=='Traveler':width+=.020*math.sin(math.pi*t)
  x=center+q*width
  bodydepth=interp([(.2,.18),(.8,.155),(1.1,.145),(1.35,.166),(1.467,.095)],z)
  bodywidth=interp([(.2,.24),(.8,.205),(1.1,.19),(1.35,.24),(1.467,.23)],z)
  wrap=math.sqrt(max(.10,1-(x/(bodywidth+.025))**2))
  folds=(.009+.006*t)*math.sin(q*9+t*4)+.004*math.sin(q*20-t*3)
  y=(bodydepth*wrap+.017+folds)*(1 if back else -1)
  zz=z+.025*q*(1-t)+.012*math.sin(q*6+1)*t*t
  return (x,y,zz)
 for back in [False,True]:
  vs=[];fs=[];N=36;K=56
  for j in range(K+1):
   for i in range(N+1):vs.append(point(j/K,-1+2*i/N,back))
  for j in range(K):
   for i in range(N):k=j*(N+1)+i;fs.append((k,k+1,k+N+2,k+N+1))
  o=mesh('BroadMantleBack' if back else 'BroadMantleFront',vs,fs if back else [tuple(reversed(f)) for f in fs],ma)
  sol=o.modifiers.new('WovenClothThickness','SOLIDIFY');sol.thickness=.003
  bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sol.name)
 # The connector uses the exact same boundary positions as both drape panels.
 vs=[];fs=[];N=36;K=24
 for j in range(K+1):
  ang=math.pi*j/K
  for i in range(N+1):
   q=-1+2*i/N;front=point(0,q,False)
   vs.append((front[0],front[1]*math.cos(ang),front[2]+(.027+.003*math.sin(q*11))*math.sin(ang)))
 for j in range(K):
  for i in range(N):k=j*(N+1)+i;fs.append((k,k+1,k+N+2,k+N+1))
 o=mesh('JoinedShoulderMantle',vs,fs,ma)
 sol=o.modifiers.new('WovenClothThickness','SOLIDIFY');sol.thickness=.003
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sol.name)

MODELS=[];records=[]
for kind in ['Jesus','Simon','Traveler']:
 PARTS.clear();skin=M['simon_skin'] if kind=='Simon' else M['traveler_skin'] if kind=='Traveler' else M['skin'];hair=M['simon_hair'] if kind=='Simon' else M['hair']
 robe(kind,M['olive'] if kind=='Simon' else M['traveler_linen'] if kind=='Traveler' else M['linen']);mantle(kind);head(kind,skin,hair,1.07 if kind=='Simon' else .96 if kind=='Traveler' else 1)
 bpy.ops.object.select_all(action='DESELECT')
 for o in PARTS:o.select_set(True)
 bpy.context.view_layer.objects.active=PARTS[0];bpy.ops.object.join();o=bpy.context.object;o.name='SM_'+kind
 bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
 if kind=='Simon':o.scale=(1.035,1.035,.985)
 if kind=='Traveler':o.scale=(.96,.96,.99)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 # Mesh normals are explicitly exported; no rig or animation dependency.
 bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False)
 records.append({'id':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'dimensions_m':list(o.dimensions),'materials':[m.name for m in o.data.materials], 'source':'Original procedural sculpt authored for this project; no third-party mesh or actor likeness','provisional':True,'limitations':'Static unrigged medium-distance sculpture; no facial animation or deformable walk cycle. Requires in-engine lighting and integration verification.'})
 MODELS.append(o);o.hide_render=True
# Put three sculptures on a single presentation stage for source-art review.
for idx,o in enumerate(MODELS):o.location.x=(idx-1)*.9;o.hide_render=False
PARTS.clear()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.resolution_x=1800;scene.render.resolution_y=1350;scene.render.resolution_percentage=100
scene.world.color=(.09,.09,.09);scene.view_settings.view_transform='AgX'
bg=mat('PreviewSand',(.145,.125,.092));bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.003));ground=bpy.context.object;ground.name='PreviewOnly_Ground';ground.data.materials.append(bg)
def area(n,loc,power,color,size,target):
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=n;o.data.energy=power;o.data.color=color;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('PreviewOnly_DawnKey',(-3,-4,5),600,(1,.80,.60),4,(0,0,1))
area('PreviewOnly_SkyFill',(3,-2,3),260,(.62,.78,1),3,(0,0,1.2))
area('PreviewOnly_Rim',(0,2,4),700,(1,.72,.46),3,(0,0,1.2))
bpy.ops.object.camera_add(location=(2.6,-7,2.7));cam=bpy.context.object;cam.name='PreviewOnly_Camera';cam.rotation_euler=(Vector((0,0,.98))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=3.25;scene.camera=cam
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CharactersV8.blend'))
if a.render:
 scene.render.filepath=str(OUT/'CharacterPreview_Trio.png');bpy.ops.render.render(write_still=True)
 for i,o in enumerate(MODELS):o.hide_render=i!=0
 cam.location=(-.9,-3.5,1.70);target=Vector((-.9,-.015,1.60));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.46
 scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.filepath=str(OUT/'CharacterPreview_Jesus.png');bpy.ops.render.render(write_still=True)
 cam.location=(-1.7,-3.5,1.72);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/'CharacterPreview_JesusThreeQuarter.png');bpy.ops.render.render(write_still=True)
manifest={'revision':'visual-v8','generator':'Tools/PathOfDawnUnreal/create_characters_v8.py','blender':bpy.app.version_string,'units':'meters','forward':'Blender -Y; FBX axis_forward=-Y, axis_up=Z','origin':'feet at 0,0,0 before preview staging','license':'Original project-authored geometry and material colors. No third-party asset restrictions. Creative depiction, not historically verified likeness.','models':records,'renders':'Blender CPU Cycles source-art previews, not Unreal game screenshots','runtime':'Single static mesh per character; original diffuse colors and explicit FACE smoothing; no image texture dependency','review':'Render and FBX roundtrip validation recorded separately.'}
(OUT/'characters-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('CHARACTERS_V8_COMPLETE '+str(OUT))
