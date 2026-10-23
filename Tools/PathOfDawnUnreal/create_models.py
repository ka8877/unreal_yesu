"""Original provisional art. Run: blender -b --python create_models.py -- [--render].
No third-party geometry. Existing outputs are never replaced. Use --output-dir with a fresh directory.
These .blend/FBX assets are not Unreal screenshots or cooked content.
"""
import argparse, bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'SourceArt/PathOfDawnUnreal/Models')
parser.add_argument('--render',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=args.output_dir.resolve()
expected=['SM_Traveler','SM_Jesus','SM_Simon','SM_Boat','SM_Net','SM_NetPrepared','SM_Jar','SM_StoneWall','SM_Canopy','SM_ShoreRock']
protected=[OUT/(x+'.fbx') for x in expected]+[OUT/'PathOfDawn_SourceModels.blend',OUT/'manifest.json',OUT/'Blender_ModelPreview.png']
if any(p.exists() for p in protected):
    raise SystemExit('Existing model sources preserved. Use --output-dir with a fresh directory, review the result, then import deliberately.')
OUT.mkdir(parents=True, exist_ok=True)
def source_path(path):
    try:return str(path.relative_to(ROOT))
    except ValueError:return str(path)
random.seed(50311)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0

def material(name, rgb, roughness=.86):
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*rgb,1); bs.inputs['Roughness'].default_value=roughness
    return m
M={
 'Linen':material('M_Linen',(.71,.65,.48)), 'Cream':material('M_Cream',(.87,.80,.64)),
 'Blue':material('M_FadedBlue',(.22,.32,.34)), 'Olive':material('M_Olive',(.32,.35,.22)),
 'Earth':material('M_Earth',(.39,.26,.16)), 'Wood':material('M_OldWood',(.27,.18,.10)),
 'WoodLight':material('M_WornWood',(.40,.29,.17)), 'Skin':material('M_WarmSkin',(.45,.28,.17)),
 'SkinSimon':material('M_SimonSkin',(.40,.25,.15)), 'Hair':material('M_DarkHair',(.075,.051,.030)),
 'HairSimon':material('M_SimonHair',(.14,.11,.075)), 'Eye':material('M_DarkEyes',(.035,.027,.02)),
 'Stone':material('M_SandStone',(.55,.51,.39)), 'Rope':material('M_Rope',(.47,.39,.25)),
 'Terracotta':material('M_Clay',(.48,.28,.16)), 'Sand':material('M_ShoreSand',(.57,.51,.37)),
}

def finish(obj, name, mat):
    obj.name=name; obj.data.materials.append(mat)
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def ellipsoid(name, loc, scale, mat, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    o=bpy.context.object; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,mat)

def cube(name,loc,scale,mat,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); finish(o,name,mat)
    if bevel:
        b=o.modifiers.new('Soft worn edges','BEVEL'); b.width=bevel; b.segments=2
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=b.name)
    return o

def limb(name,a,b,r1,r2,mat,verts=12):
    a,b=Vector(a),Vector(b); d=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=verts,radius1=r1,radius2=r2,depth=d.length,location=(a+b)/2)
    o=bpy.context.object; o.rotation_euler=d.to_track_quat('Z','Y').to_euler(); finish(o,name,mat); return o

def loft(name,rings,mat,segments=24):
    vs=[]
    for z,rx,ry,xoff,yoff in rings:
        for i in range(segments):
            a=i*math.tau/segments; fold=1+.035*math.cos(i*5)
            vs.append((xoff+math.cos(a)*rx*fold,yoff+math.sin(a)*ry*fold,z))
    fs=[]
    for j in range(len(rings)-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;fs.append((a,b,b+segments,a+segments))
    fs.append(tuple(reversed(range(segments))));fs.append(tuple(range((len(rings)-1)*segments,len(rings)*segments)))
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return finish(o,name,mat)

def character(kind):
    simon=kind=='Simon'; traveler=kind=='Traveler'; robe=M['Olive'] if simon else M['Blue'] if traveler else M['Cream'];skin=M['SkinSimon'] if simon else M['Skin'];hair=M['HairSimon'] if simon else M['Hair']
    width=.26 if simon else .225
    loft('robe',[(.16,.24,.17,0,0),(.45,.23,.16,0,0),(.90,.21,.14,0,0),(1.08,.18,.12,0,0),(1.40,width,.13,0,0),(1.47,.13,.10,0,0)],robe)
    for x in (-.115,.115):
        ellipsoid('sandaled_foot',(x,-.065,.07),(.085,.17,.06),M['Earth']);limb('ankle',(x,0,.08),(x,0,.24),.055,.06,skin)
        cube('sandal_strap',(x,-.08,.115),(.14,.035,.016),M['WoodLight'],.004)
    limb('neck',(0,0,1.40),(0,0,1.55),.075,.078,skin)
    ellipsoid('head',(0,-.015,1.655),(.105 if not simon else .12,.095, .14),skin,24,16)
    ellipsoid('nose',(0,-.108,1.64),(.024,.038,.045),skin)
    for s in (-1,1):
        ellipsoid('ear',(s*.105,-.006,1.65),(.025,.018,.042),skin)
        ellipsoid('eye',(s*.040,-.101,1.685),(.012,.008,.006),M['Eye'])
        limb('eyebrow',(s*.018,-.106,1.709),(s*.064,-.100,1.71),.007,.007,hair,8)
        shoulder=(s*width,0,1.37);elbow=(s*(width+.07),-.018,1.10);wrist=(s*(width+.035),-.12,.93)
        limb('sleeve_upper',shoulder,elbow,.105,.09,robe);limb('sleeve_lower',elbow,wrist,.09,.065,robe)
        ellipsoid('hand',(wrist[0],wrist[1]-.015,wrist[2]-.045),(.043,.035,.074),skin)
        for f in range(3):
            ellipsoid('finger',(wrist[0]+(f-1)*.017,wrist[1]-.030,wrist[2]-.10),(.009,.014,.030),skin,8,6)
    ellipsoid('beard',(0,-.082,1.575),(.079,.042,.079 if not traveler else .036),hair,18,10)
    ellipsoid('hair_cap',(0,.01,1.75),(.112,.1,.071),hair)
    for s in (-1,1):
        for j in range(4 if simon else 7):
            ellipsoid('hair_lock',(s*(.091+.006*math.sin(j)),.025,1.72-j*.035),(.035,.075,.047),hair,10,6)
    # A natural asymmetrical drape, no T-pose, no armor or modern clothes.
    mantle=M['Earth'] if simon else M['Linen'] if traveler else M['Blue']
    for j in range(4):
        limb('mantle_fold',(-.19+j*.028,.08,1.43),(-.16+j*.025,-.04,.61),.028,.023,mantle)
    limb('belt',(-.18,-.128,1.02),(.18,-.128,1.02),.018,.018,M['Rope'])
    limb('belt_tail',(.05,-.14,1.02),(.065,-.155,.72),.011,.009,M['Rope'])

def boat():
    # Curved, open clinker hull, model forward axis X.
    verts=[];n=23
    for j in range(n):
        t=-1+2*j/(n-1);x=t*2.05;w=.70*(max(0,1-t*t)**.53)+.025;rise=.18+abs(t)**3*.42
        for y,z in [(-w,rise+.43),(-w*.84,rise+.17),(0,rise),(w*.84,rise+.17),(w,rise+.43)]:verts.append((x,y,z))
    faces=[]
    for j in range(n-1):
        for k in range(4):a=j*5+k;faces.append((a,a+5,a+6,a+1))
    me=bpy.data.meshes.new('Hull');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('hull',me);bpy.context.collection.objects.link(o);finish(o,'hull',M['Wood'])
    sol=o.modifiers.new('Solid timber','SOLIDIFY');sol.thickness=.055;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sol.name)
    for side in (-1,1):
        for j in range(n-1):
            a=verts[j*5+(0 if side<0 else 4)];b=verts[(j+1)*5+(0 if side<0 else 4)];limb('gunwale',a,b,.035,.035,M['WoodLight'],8)
    for x in (-1.05,0,1.05):cube('bench',(x,0,.55),( .27,1.05,.07),M['WoodLight'])
    limb('oar',(-1.4,.42,.73),(1.6,.42,.73),.024,.024,M['WoodLight']);cube('oar_blade',(1.65,.42,.73),(.62,.19,.035),M['WoodLight'],.03)
    for x in (-1.6,-.8,0,.8,1.6):limb('rib',(x,-.42,.29),(x,.42,.29),.028,.028,M['WoodLight'])

def net(prepared):
    n,m=17,11
    def point(i,j):
        x=(i/n-.5)*2.3;y=(j/m-.5)*1.5;z=.035+(.035 if prepared else .14)*math.sin(i*.8)*math.cos(j*.7)
        if not prepared:y*=.73+.2*math.sin(i*.8)
        return (x,y,z)
    for i in range(n+1):
        for j in range(m):limb('net_rope',point(i,j),point(i,j+1),.007,.007,M['Rope'],5)
    for j in range(m+1):
        for i in range(n):limb('net_rope',point(i,j),point(i+1,j),.007,.007,M['Rope'],5)
    for i in range(0,n+1,2):ellipsoid('float',point(i,0),(.04,.022,.025),M['WoodLight'],8,6)
    if prepared:
        limb('repair',(-.4,-.12,.07),(.4,.16,.07),.015,.015,M['Linen'])

def jar():
    loft('jar',[(0,.12,.12,0,0),(.08,.22,.22,0,0),(.4,.25,.25,0,0),(.62,.11,.11,0,0),(.68,.12,.12,0,0)],M['Terracotta'],28)
    for s in (-1,1):
        for j in range(9):
            a=j*math.pi/9;b=(j+1)*math.pi/9
            limb('handle',(s*(.13+.14*math.sin(a)),0,.50+.12*math.cos(a)),(s*(.13+.14*math.sin(b)),0,.50+.12*math.cos(b)),.022,.022,M['Terracotta'],8)

def wall():
    for row in range(5):
        for col in range(8):
            x=(col-3.5)*.5+(row%2)*.12
            cube('stone_block',(x,random.uniform(-.015,.015),.18+row*.37),(.48+random.uniform(-.02,.02),.4,.35),M['Stone'],.055)

def canopy():
    for x in (-1.4,1.4):
        for y in (-1,1):limb('pole',(x,y,0),(x,y,2.05),.045,.035,M['Wood'])
    loft('cloth',[(1.94,1.5,1.1,0,0),(2.08,1.5,1.1,0,0)],M['Linen'],4)

def rock():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(0,0,.2));o=bpy.context.object
    for v in o.data.vertices:
        v.co.x*=.51*random.uniform(.88,1.12);v.co.y*=.40*random.uniform(.88,1.12);v.co.z*=.31*random.uniform(.88,1.12)
    finish(o,'shore_rock',M['Stone'])

def export_model(name,creator):
    before=set(bpy.data.objects);creator();objects=[o for o in bpy.data.objects if o not in before]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True)
    return o

models=[]
for n,fn in [('SM_Traveler',lambda:character('Traveler')),('SM_Jesus',lambda:character('Jesus')),('SM_Simon',lambda:character('Simon')),('SM_Boat',boat),('SM_Net',lambda:net(False)),('SM_NetPrepared',lambda:net(True)),('SM_Jar',jar),('SM_StoneWall',wall),('SM_Canopy',canopy),('SM_ShoreRock',rock)]:
    models.append(export_model(n,fn));models[-1].hide_render=True;models[-1].hide_set(True)
# Preserve source geometry separately in one native Blender project.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PathOfDawn_SourceModels.blend'))
manifest=[]
for o in models:
    manifest.append({'file':source_path(OUT/(o.name+'.fbx')),'asset_id':o.name,'origin':'Original procedural geometry authored for PathOfDawnUnreal','license':'Project-created asset; no third-party source geometry','temporary':True,'modifications':'Blender 4.3.2 deterministic generator; materials and natural resting poses','runtime_path':'/Game/PathOfDawn/'+('Characters/' if o.name in ('SM_Traveler','SM_Jesus','SM_Simon') else 'Environment/')+o.name,'limitations':'Static geometric silhouette; no facial rig or skeletal animation' if o.name in ('SM_Traveler','SM_Jesus','SM_Simon') else 'Provisional art; needs Unreal collision/lighting review'})
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if args.render:
    placement={'SM_Traveler':(-1.4,0,0),'SM_Jesus':(0,0,0),'SM_Simon':(1.4,0,0),'SM_Boat':(0,3,0),'SM_Net':(-3,1.5,0),'SM_NetPrepared':(3,1.5,0),'SM_Jar':(2.5,0,0),'SM_StoneWall':(0,5,0),'SM_Canopy':(-3,4,0),'SM_ShoreRock':(-2.5,-.4,0)}
    for o in models:o.hide_render=False;o.hide_set(False);o.location=placement[o.name]
    cube('preview_floor',(0,1,-.10),(15,15,.2),M['Sand'],.0)
    bpy.ops.object.light_add(type='AREA',location=(-4,-4,8));bpy.context.object.data.energy=1800;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=7;bpy.context.object.data.color=(1,.83,.60)
    bpy.ops.object.light_add(type='AREA',location=(4,3,6));bpy.context.object.data.energy=900;bpy.context.object.data.size=6;bpy.context.object.data.color=(.61,.75,1)
    bpy.ops.object.camera_add(location=(8,-12,7));cam=bpy.context.object;cam.rotation_euler=(Vector((0,1,1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=12;bpy.context.scene.camera=cam
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=24;sc.cycles.use_denoising=False;sc.render.resolution_x=1280;sc.render.resolution_y=800;sc.render.resolution_percentage=100
    sc.world.color=(.18,.18,.18);sc.view_settings.view_transform='AgX';sc.render.filepath=str(OUT/'Blender_ModelPreview.png');bpy.ops.render.render(write_still=True)
print('POD_MODELS_COMPLETE',len(models))
