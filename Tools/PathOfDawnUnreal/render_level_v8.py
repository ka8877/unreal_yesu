"""Render a source-art composition review, NOT an Unreal capture or performance test.

The actor placements are evaluated from this project's own create_map function
through a small Blender adapter. FBX geometry and texture inputs are the actual
VisualV8 authoring sources. Cycles lighting is an artistic approximation, not
Unreal/Lumen. Invisible game collision and UI are deliberately not represented.

blender -b --python Tools/PathOfDawnUnreal/render_level_v8.py -- --output-dir /tmp/dawn-level-review
"""
import argparse, ast, bpy, hashlib, json, math, random, sys, types
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'SourceArt/PathOfDawnUnreal/VisualV8/Models'
GENERATOR=ROOT/'Tools/PathOfDawnUnreal/generate_demo_assets.py'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output-dir',type=Path,default=ROOT/'Docs/PathOfDawnUnreal/Evidence/VisualV8')
p.add_argument('--samples',type=int,default=32)
p.add_argument('--width',type=int,default=1440)
p.add_argument('--view',choices=['all','shore','overview'],default='all')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=a.output_dir.resolve();OUT.mkdir(parents=True,exist_ok=True)
if any(OUT.glob('LevelPreview*')):raise SystemExit('Existing previews preserved. Choose a fresh --output-dir.')
for name in ('SM_Jesus.fbx','SM_Simon.fbx','SM_Traveler.fbx','T_ShoreAlbedo.png','T_ShoreNormal.png','T_LakeNormal.png'):
 if not (SOURCE/name).is_file():raise SystemExit('Missing final VisualV8 input: '+name)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC'
TEMPLATES={};PLACEMENTS=[];HASHES={}
class Dummy:
 def __init__(self,obj=None,path=''):self.obj=obj;self.path=path
 def get_editor_property(self,name):return self
 def get_world_settings(self):return self
 def set_editor_property(self,*args):pass
 def generated_class(self):return self
 def get_path_name(self):return self.path
 def get_component_by_class(self,*args):return self
 def get_cine_camera_component(self):return self
 def set_relative_scale3d(self,value):
  if self.obj:self.obj.scale=value

def load_mesh(name):
 if name in TEMPLATES:return TEMPLATES[name]
 path=SOURCE/(name+'.fbx')
 HASHES[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
 old=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath=str(path))
 objs=[o for o in bpy.data.objects if o not in old and o.type=='MESH']
 if len(objs)!=1:raise RuntimeError('Expected one FBX mesh: '+name)
 obj=objs[0]
 for coll in list(obj.users_collection):coll.objects.unlink(obj)
 TEMPLATES[name]=obj
 return obj

def image_file(name,color=True):
 path=SOURCE/(name+'.png');HASHES[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
 im=bpy.data.images.load(str(path),check_existing=True)
 im.colorspace_settings.name='sRGB' if color else 'Non-Color'
 return im

def material(name,color,roughness=.85,water=False,normal=None,albedo=None,tiling=(180.,63.)):
 m=bpy.data.materials.new(name);m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links
 bs=nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness
 texcoord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(*tiling,1)
 links.new(texcoord.outputs['UV'],mapping.inputs[0])
 if albedo:
  tex=nodes.new('ShaderNodeTexImage');tex.image=image_file(albedo.rsplit('/',1)[-1]);links.new(mapping.outputs[0],tex.inputs['Vector']);links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 if normal:
  tex=nodes.new('ShaderNodeTexImage');tex.image=image_file(normal.rsplit('/',1)[-1],False);links.new(mapping.outputs[0],tex.inputs['Vector'])
  # Authored textures use DirectX tangent Y. Blender expects the OpenGL convention.
  separate=nodes.new('ShaderNodeSeparateColor');combine=nodes.new('ShaderNodeCombineColor');invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1
  links.new(tex.outputs['Color'],separate.inputs['Color']);links.new(separate.outputs['Red'],combine.inputs['Red']);links.new(separate.outputs['Blue'],combine.inputs['Blue']);links.new(separate.outputs['Green'],invert.inputs[1]);links.new(invert.outputs[0],combine.inputs['Green'])
  n=nodes.new('ShaderNodeNormalMap');links.new(combine.outputs[0],n.inputs['Color']);links.new(n.outputs[0],bs.inputs['Normal'])
 return m

def static(label,mesh,loc,rotation=(0,0,0),scale=None,material=None,collision=True):
 if mesh.endswith('/Plane'):
  bpy.ops.mesh.primitive_plane_add(size=1);obj=bpy.context.object
 else:
  template=load_mesh(mesh.rsplit('/',1)[-1]);obj=template.copy();scene.collection.objects.link(obj)
 obj.name=label;obj.location=tuple(v*.01 for v in loc)
 obj.rotation_euler=(math.radians(rotation[2]),math.radians(rotation[0]),math.radians(rotation[1]))
 if scale:obj.scale=scale
 if material:
  # Object-linked material overrides do not mutate the reusable authoring mesh.
  if not obj.material_slots:obj.data.materials.append(material)
  for slot in obj.material_slots:slot.link='OBJECT';slot.material=material
 PLACEMENTS.append(dict(label=label,mesh=mesh,location_cm=loc,rotation_pitch_yaw_roll=rotation,scale=scale or (1,1,1),visible=True))
 return Dummy(obj)

def interact(identifier,display,mesh,loc,rotation=(0,0,0),character=False):
 return static('Interact_'+identifier,'/Game/PathOfDawn/'+mesh,loc,rotation)

def spawn(cls,label,loc,rotation=(0,0,0),scale=None):
 if label=='PlayerStart':
  # Represent the controllable traveler at the initial point; the exact live
  # CharacterMovement capsule drop and camera framing are not simulated.
  return static('Traveler_start_marker','/Game/PathOfDawn/SM_Traveler',(loc[0],loc[1],0),(0,180,0))
 return Dummy()

def barrier(label,loc,scale):PLACEMENTS.append(dict(label=label,location_cm=loc,scale=scale,visible=False))
BASE='/Game/PathOfDawn';MAP=BASE+'/Maps/L_Galilee'
ue=types.SimpleNamespace(Vector=lambda *v:v,Color=lambda *v:v,get_default_object=lambda *v:Dummy(),
 EditorLoadingAndSavingUtils=types.SimpleNamespace(new_blank_map=lambda _:Dummy(),save_map=lambda *v:True))
for cls in ('PlayerStart','SkyAtmosphere','DirectionalLight','DirectionalLightComponent','SkyLight','SkyLightComponent','ExponentialHeightFog','ExponentialHeightFogComponent','CineCameraActor'):setattr(ue,cls,cls)
def need(path):return Dummy(path=path) if '/BP_' in path else path
ns=dict(REPORT={'created':[],'preserved':[]},LIB=types.SimpleNamespace(does_asset_exist=lambda _:False,set_metadata_tag=lambda *v:None,save_loaded_asset=lambda *v,**kw:True),MAP=MAP,BASE=BASE,u=ue,need=need,make_material=material,static=static,interact=interact,barrier=barrier,spawn=spawn,path_model=lambda n:BASE+'/Environment/'+n,random=random,math=math)
generator_bytes=GENERATOR.read_bytes()
tree=ast.parse(generator_bytes);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_map']
if len(nodes)!=1:raise RuntimeError('create_map not found')
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(GENERATOR),'exec'),ns);ns['create_map']()
# Use a wide atmospheric review rig. It is intentionally not presented as the
# game's lighting. Mesh placements above come directly from create_map.
world=bpy.data.worlds.new('Review dawn atmosphere');scene.world=world;world.use_nodes=True
wn=world.node_tree.nodes;wl=world.node_tree.links
sky=wn.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_disc=False;sky.sun_elevation=math.radians(9);sky.sun_rotation=math.radians(130);sky.altitude=.1;sky.air_density=1.2;sky.dust_density=1.6
wl.new(sky.outputs['Color'],wn.get('Background').inputs['Color']);wn.get('Background').inputs['Strength'].default_value=.25
bpy.ops.object.light_add(type='SUN',location=(20,30,15));sun=bpy.context.object;sun.name='Preview warm sun';sun.data.energy=3.4;sun.data.angle=math.radians(4);sun.data.color=(1,.76,.49);sun.rotation_euler=(math.radians(67),0,math.radians(130))
# Thin distant haze: avoids obscuring medium-distance characters.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,115,15));haze=bpy.context.object;haze.name='Preview distance haze';haze.scale=(600,220,36)
hm=bpy.data.materials.new('Preview haze only');hm.use_nodes=True;hn=hm.node_tree.nodes;hn.clear();output=hn.new('ShaderNodeOutputMaterial');volume=hn.new('ShaderNodeVolumePrincipled');volume.inputs['Density'].default_value=.0015;volume.inputs['Color'].default_value=(.69,.78,.82,1);hm.node_tree.links.new(volume.outputs['Volume'],output.inputs['Volume']);haze.data.materials.append(hm)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=a.samples;scene.cycles.use_denoising=False
scene.cycles.max_bounces=6;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.volume_bounces=1
scene.render.resolution_x=a.width;scene.render.resolution_y=round(a.width*9/16);scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.25
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera
views=[('LevelPreview_Shore',(0,-13.0,2.65),(0,2.5,1.25),30),('LevelPreview_Overview',(-21,-28,14),(0,-3,0.6),28)]
if a.view!='all':views=[v for v in views if v[0].endswith('_'+a.view.capitalize())]
outputs=[]
for name,loc,target,lens in views:
 camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=lens
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);outputs.append(scene.render.filepath)
report={'kind':'Blender source-art layout render; NOT Unreal gameplay or screenshot','blender_version':bpy.app.version_string,'render_engine':'Cycles CPU','resolution':[scene.render.resolution_x,scene.render.resolution_y],'samples':a.samples,'denoising':False,'generator':str(GENERATOR.relative_to(ROOT)),'generator_sha256':hashlib.sha256(generator_bytes).hexdigest(),'method':'Evaluated actual create_map actor placement function through Blender adapter; centimetres converted to metres. Static FBX files imported without geometry replacement. Invisible collision omitted.','limitations':['Cycles lighting/haze approximates art direction, not Unreal Lumen or actual GPU output.','FBX orientation/conversion, live movement, collisions, UI and camera behavior still require UE verification.','Traveler shown at initial foot location; CharacterMovement not simulated.'],'source_hashes':HASHES,'visible_actor_count':sum(r['visible'] for r in PLACEMENTS),'placements':PLACEMENTS,'views':[dict(name=v[0],position_m=v[1],target_m=v[2],lens_mm=v[3]) for v in views],'outputs':[{'file':Path(o).name,'sha256':hashlib.sha256(Path(o).read_bytes()).hexdigest()} for o in outputs]}
(OUT/'LevelPreview-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('POD_BLENDER_LAYOUT_PREVIEW_COMPLETE',str(OUT))
