"""FBX round-trip source-art validation; not an Unreal import/collision test."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
source=ROOT/'SourceArt/PathOfDawnUnreal/Models'
report={'tool':bpy.app.version_string,'kind':'Blender FBX round-trip; NOT Unreal','status':'passed','models':[]}
for path in sorted(source.glob('*.fbx')):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(path))
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert len(objs)==1,(path.name,len(objs))
    obj=objs[0];dims=list(obj.dimensions)
    assert all(x>0 for x in dims),(path.name,dims)
    assert len(obj.data.polygons)>0 and len(obj.data.materials)>0,path.name
    if path.stem in ('SM_Traveler','SM_Jesus','SM_Simon'):assert 1.7<dims[2]<2.0,(path.name,dims)
    if path.stem=='SM_Boat':assert 3.8<dims[0]<4.5,(path.name,dims)
    report['models'].append({'file':path.name,'dimensions_metres':dims,'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons),'material_slots':len(obj.data.materials)})
assert len(report['models'])==10
out=ROOT/'Docs/PathOfDawnUnreal/Evidence/blender-fbx-validation.json';out.write_text(json.dumps(report,indent=2)+'\n')
print('POD_FBX_ROUNDTRIP_PASSED',len(report['models']))
