"""Check the exact v8 sources consumed by Editor import, without loading Unreal.

This catches missing/incorrectly bundled art before the user compiles or imports.
Blender FBX round-trip reports and actual Unreal visual checks remain separate.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from PIL import Image


def validate(root):
    errors=[]
    records=[]
    script=root/'Tools/PathOfDawnUnreal/generate_demo_assets.py'
    tree=ast.parse(script.read_text(encoding='utf-8'))
    ids={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
         if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
         and node.targets[0].id in ('IMAGES','MODELS')}
    source=root/'SourceArt/PathOfDawnUnreal/VisualV8'
    inputs=[(source/'Illustrations'/(name+'.png'),'illustration') for name in ids['IMAGES']]
    inputs += [(source/'Models'/(name+'.fbx'),'mesh') for name in ids['MODELS']]
    inputs += [(source/'Models'/(name+'.png'),'surface') for name in ('T_LakeNormal','T_ShoreAlbedo','T_ShoreNormal')]
    for path,kind in inputs:
        try:
            data=path.read_bytes()
            # AssetManifest uses repository-relative '/' keys on every OS.
            # str(WindowsPath(...)) would introduce '\\' and reject valid art.
            record={'file':path.relative_to(root).as_posix(),'id':path.stem,'kind':kind,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            if kind=='mesh':
                if len(data)<1024 or not data.startswith(b'Kaydara FBX Binary'):
                    raise ValueError('Expected a nonempty binary FBX, not a placeholder')
            else:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    record['dimensions']=list(image.size)
                    if min(image.size)<512:raise ValueError('Image is smaller than 512 pixels')
                    if kind=='surface' and image.width!=image.height:raise ValueError('Expected a square tiling texture')
            records.append(record)
        except (OSError,ValueError) as error:
            errors.append(path.relative_to(root).as_posix()+': '+str(error))
    for group,expected in (('illustration',7),('mesh',15),('surface',3)):
        group_records=[record for record in records if record['kind']==group]
        if len(group_records)!=expected:errors.append(f'Expected {expected} {group} sources, found {len(group_records)}')
        if len({record['sha256'] for record in group_records})!=len(group_records):
            errors.append('Duplicate file content in '+group+' source set')
    # The manifest is the shipping source index, not an assertion of UE imports.
    manifest=root/'Docs/PathOfDawnUnreal/AssetManifest.json'
    if manifest.is_file():
        try:
            indexed={row['file']:row for row in json.loads(manifest.read_text(encoding='utf-8'))['assets']}
            for record in records:
                entry=indexed.get(record['file'])
                if not entry or entry.get('sha256')!=record['sha256']:
                    errors.append('Missing/stale provenance manifest entry: '+record['file'])
        except (ValueError,KeyError,TypeError) as error:errors.append('Invalid asset manifest: '+str(error))
    else:errors.append('AssetManifest.json is missing')
    return {'status':'passed' if not errors else 'failed','scope':'Source integrity and provenance only; not Unreal import, shaders, collision or graphics','visual_version':'v8','errors':errors,'sources':records}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=validate(args.root.resolve())
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'source_count':len(result['sources']),'errors':result['errors']},ensure_ascii=False))
    raise SystemExit(0 if result['status']=='passed' else 1)
