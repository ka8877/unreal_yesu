import bpy,sys,json
from pathlib import Path
from mathutils import Vector
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
manifest=json.loads((root/'manifest.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
asset=next(a for a in manifest['assets'] if a['id']=='ceramic_pot')
meshrow=next(f for f in asset['files'] if f['role']=='mesh')
bpy.ops.import_scene.fbx(filepath=str(root/meshrow['path']))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert meshes,'No real mesh loaded'
rows=[]
for o in meshes:
 o.data.calc_loop_triangles()
 assert len(o.data.vertices)>50 and len(o.data.loop_triangles)>50
 assert len(o.data.uv_layers)>0
 rows.append({'name':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),'uv_layers':len(o.data.uv_layers),'dimensions_m':[round(x,5) for x in o.dimensions],'materials':[s.material.name if s.material else None for s in o.material_slots]})
report={'status':'passed','scope':'Original provider FBX parsed by Blender; not Unreal import/render or historical certification','blender_version':bpy.app.version_string,'mesh_objects':rows,'total_triangles':sum(r['triangles'] for r in rows),'original_file':meshrow['path'],'original_sha256':meshrow['sha256'],'material_note':'Provider EXR file links were not bundled; use manifest base_color/DirectX normal/roughness textures with explicit material assignment.'}
(root/'verification/ceramic-pot-blender-load.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
