"""Blender-only source parsing evidence; never a final-character/Unreal test."""
import bpy
import json
from pathlib import Path

root = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
rows = []
for relative in ["DonitzRobe/Monks_Robe.obj", "MakeHumanFoundation/3dobjs/base.obj"]:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(root / relative))
    objects = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    assert objects, relative
    for obj in objects:
        obj.data.calc_loop_triangles()
        assert len(obj.data.vertices) > 100 and len(obj.data.uv_layers) > 0
        rows.append({"source": relative, "object": obj.name, "vertices": len(obj.data.vertices),
                     "triangles": len(obj.data.loop_triangles), "uv_layers": len(obj.data.uv_layers)})
rig = json.loads((root / "MakeHumanFoundation/rigs/default.mhskel").read_text())
weights = json.loads((root / "MakeHumanFoundation/rigs/default_weights.mhw").read_text())
assert len(rig["bones"]) > 10 and weights
report = {"status": "passed", "blender_version": bpy.app.version_string, "source_objects": rows,
          "rig_definition_bones": len(rig["bones"]), "rig_weights_source_parsed": True,
          "game_ready": False, "skeleton_bound_in_blender_or_unreal": False,
          "scope": "Original OBJ/UV and JSON parsing only. No assembled/animated/clothed final character, Unreal import or game image."}
(root / "blender-source-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
