"""Unreal Editor only. Compile PathOfDawnUnrealEditor before executing.
Creates real assets through editor APIs, never synthetic .uasset/.umap text.
Changed imports refresh only when their package hashes match the generated baseline.
Edited packages and existing maps/Blueprints are preserved.
Run in a SECOND fresh editor process with -PODVerifyAssets to verify persisted
references. Source JSON is authoritative; runtime reads only the cooked DataAsset.
"""
import hashlib, json, math, random, sys, traceback
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
import source_asset_guard as guard
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'SourceArt/PathOfDawnUnreal'
# v8 is an explicit, complete art set. Never silently fall back to the old
# geometric placeholders when a new source file is missing.
VISUAL_SOURCE=SOURCE/'VisualV8'
PROJECT=ROOT/'Games/PathOfDawnUnreal'
REPORTDIR=PROJECT/'Saved/PathOfDawn';REPORTDIR.mkdir(parents=True,exist_ok=True)
BASE='/Game/PathOfDawn'
MAP=BASE+'/Maps/L_Galilee'
TOOLS=u.AssetToolsHelpers.get_asset_tools()
LIB=u.EditorAssetLibrary
ACTORS=u.get_editor_subsystem(u.EditorActorSubsystem)
LEVELS=u.get_editor_subsystem(u.LevelEditorSubsystem)
VERIFY='-PODVerifyAssets' in u.SystemLibrary.get_command_line()
REPORT={'mode':'reload-verification' if VERIFY else 'generation','status':'running','stage':'preflight','created':[],'preserved':[],'warnings':[],'engine_version':u.SystemLibrary.get_engine_version(),'required':[]}
REPORTFILE=REPORTDIR/('asset-verification-report.json' if VERIFY else 'asset-generation-report.json')
INDEXFILE=PROJECT/'Content/PathOfDawn/generated-source-index.json'
INDEX=None
REPORT['refreshed']=[]
IMAGES=['IL_Title_Dawn','IL_Arrival','IL_Portrait_Jesus','IL_Portrait_Simon','IL_Ending_Together','IL_Ending_Witness','IL_Ending_Departure']
MODELS=['SM_Traveler','SM_Jesus','SM_Simon','SM_Boat','SM_Net','SM_NetPrepared','SM_Jar','SM_StoneWall','SM_Canopy','SM_ShoreRock','SM_OliveTree','SM_ReedClump','SM_PathSlab','SM_ShoreGround','SM_DistantRidge']
SOUNDS=['A_Water','A_Wind','A_Footstep','A_NetRustle']
REPORT['visual_version']='v8'

def path_model(name):return BASE+('/Characters/' if name in ('SM_Traveler','SM_Jesus','SM_Simon') else '/Environment/')+name

def need(path):
    asset=LIB.load_asset(path)
    if not asset:raise RuntimeError('Required asset missing: '+path)
    return asset

def owned(asset):
    LIB.set_metadata_tag(asset,'PathOfDawnGenerator','v1')
    if not LIB.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
    REPORT['created'].append(asset.get_path_name())
    return asset

def existing(path):
    if LIB.does_asset_exist(path):
        REPORT['preserved'].append(path)
        return need(path)
    return None

def source_plan(filename, path):
    exists=LIB.does_asset_exist(path)
    asset=need(path) if exists else None
    source_hash=guard.sha256_file(filename)
    package_hash=guard.package_sha256(path,PROJECT/'Content') if exists else None
    old_source=LIB.get_metadata_tag(asset,'PathOfDawnSourceSHA256') if asset else None
    action,reason=guard.refresh_decision(source_hash,package_hash,INDEX['assets'].get(path),exists,old_source)
    if action=='conflict':
        raise RuntimeError('SOURCE/PACKAGE CONFLICT at '+path+': '+reason+'. Preserve the edited asset under a reviewed new name, then restore the matching generated package and generated-source-index.json from version control, or merge this source in Editor. Deleting the index is not an ownership override.')
    if action in ('preserve_user_edit','preserve_untracked'):
        warning=path+': '+reason
        if warning not in REPORT['warnings']:REPORT['warnings'].append(warning)
    return action,asset,source_hash

def save_source_asset(asset, path, source_file, source_hash, action):
    LIB.set_metadata_tag(asset,'PathOfDawnGenerator','v2')
    LIB.set_metadata_tag(asset,'PathOfDawnSourceSHA256',source_hash)
    if not LIB.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Source asset save failed: '+path)
    package_hash=guard.package_sha256(path,PROJECT/'Content')
    if not package_hash:raise RuntimeError('Saved package not readable on disk: '+path)
    INDEX['assets'][path]={'source':str(source_file.relative_to(ROOT)).replace('\\','/'),'source_sha256':source_hash,'package_sha256':package_hash}
    # Record after every successful save, so a later failure cannot lose this ownership baseline.
    guard.save_index(INDEXFILE,INDEX)
    REPORT['refreshed' if action=='refresh' else 'created'].append(path)
    return asset

def import_file(filename, folder, name, kind):
    REPORT['stage']='import:'+kind+':'+name
    path=folder+'/'+name
    action,asset,source_hash=source_plan(filename,path)
    if action.startswith('preserve'):
        REPORT['preserved'].append(path)
        return asset
    if kind=='font' and action=='refresh':
        raise RuntimeError('Font source changed at '+path+'. Font-face/composite-font updates require a targeted Editor review; no stale font will be cooked automatically.')
    task=u.AssetImportTask();task.set_editor_property('filename',str(filename));task.set_editor_property('destination_path',folder);task.set_editor_property('destination_name',name)
    task.set_editor_property('automated',True);task.set_editor_property('save',False);task.set_editor_property('replace_existing',action=='refresh')
    task.set_editor_property('replace_existing_settings',False)
    if kind=='mesh':
        options=u.FbxImportUI();options.set_editor_property('import_mesh',True);options.set_editor_property('import_as_skeletal',False);options.set_editor_property('import_animations',False)
        options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH);options.set_editor_property('automated_import_should_detect_type',False)
        # Existing shared materials are independent editable assets; a mesh refresh never overwrites them.
        options.set_editor_property('import_materials',action=='create');options.set_editor_property('import_textures',False)
        data=options.get_editor_property('static_mesh_import_data');data.set_editor_property('combine_meshes',True);data.set_editor_property('auto_generate_collision',True)
        task.set_editor_property('options',options)
        if action=='refresh':REPORT['warnings'].append(path+': mesh geometry refreshed; existing shared material assets preserved. Review authored material changes separately in Editor.')
    elif kind=='font':task.set_editor_property('factory',u.FontFileImportFactory())
    TOOLS.import_asset_tasks([task])
    paths=task.get_editor_property('imported_object_paths')
    if not paths:raise RuntimeError('Import produced no object: '+str(filename))
    asset=need(path)
    if kind=='image':
        asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);asset.set_editor_property('srgb',True)
    if kind=='albedo':asset.set_editor_property('srgb',True)
    if kind=='normal':
        asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        asset.set_editor_property('srgb',False)
    if kind=='sound':asset.set_editor_property('looping',name in ('A_Water','A_Wind'))
    # New FBX materials are imported alongside the mesh and must be saved too.
    if kind=='mesh' and action=='create':
        for imported in paths:
            dependency=need(imported)
            if dependency!=asset and not LIB.save_loaded_asset(dependency,only_if_is_dirty=False):raise RuntimeError('Imported material save failed: '+imported)
        for slot in asset.get_editor_property('static_materials'):
            material=slot.get_editor_property('material_interface')
            if material and material.get_path_name().startswith(BASE+'/') and not LIB.save_loaded_asset(material):raise RuntimeError('Imported material save failed: '+material.get_path_name())
    return save_source_asset(asset,path,filename,source_hash,action)

def require_material_link(connected,description):
    if not connected:raise RuntimeError('Material connection failed: '+description)

def make_material(name,color,roughness=.85,water=False,normal=None,albedo=None,tiling=(180.,63.)):
    path=BASE+'/Environment/'+name
    asset=existing(path)
    if asset:return asset
    mat=TOOLS.create_asset(name,BASE+'/Environment',u.Material,u.MaterialFactoryNew());me=u.MaterialEditingLibrary
    c=me.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-300,0);c.set_editor_property('constant',u.LinearColor(*color,1))
    require_material_link(me.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR),name+': base color')
    r=me.create_material_expression(mat,u.MaterialExpressionConstant,-300,120);r.set_editor_property('r',roughness);require_material_link(me.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS),name+': roughness')
    if water:
        time=me.create_material_expression(mat,u.MaterialExpressionTime,-600,300)
        # An empty input name selects the first input. Sine does not expose an
        # input named "Input" through MaterialEditingLibrary in UE 5.8.
        sine=me.create_material_expression(mat,u.MaterialExpressionSine,-400,300);require_material_link(me.connect_material_expressions(time,'',sine,''),name+': time to sine')
        direction=me.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-400,440);direction.set_editor_property('constant',u.LinearColor(0,0,.7,1))
        mult=me.create_material_expression(mat,u.MaterialExpressionMultiply,-150,300)
        require_material_link(me.connect_material_expressions(sine,'',mult,'A'),name+': sine to multiply')
        require_material_link(me.connect_material_expressions(direction,'',mult,'B'),name+': direction to multiply')
        require_material_link(me.connect_material_property(mult,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET),name+': world position offset')
    if normal is not None:
        uv=me.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-850,-200)
        uv.set_editor_property('u_tiling',tiling[0]);uv.set_editor_property('v_tiling',tiling[1])
        pan=me.create_material_expression(mat,u.MaterialExpressionPanner,-650,-200)
        pan.set_editor_property('speed_x',.008 if water else 0.);pan.set_editor_property('speed_y',.004 if water else 0.)
        sample=me.create_material_expression(mat,u.MaterialExpressionTextureSample,-400,-200)
        sample.set_editor_property('texture',normal)
        sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        # Empty names select the documented first coordinate input; no guessed
        # display names such as "Input" are passed to the material API.
        require_material_link(me.connect_material_expressions(uv,'',pan,''),name+': tiled UV to panner')
        require_material_link(me.connect_material_expressions(pan,'',sample,''),name+': panner to texture UV')
        require_material_link(me.connect_material_property(sample,'RGB',u.MaterialProperty.MP_NORMAL),name+': water normal')
        LIB.set_metadata_tag(mat,'PathOfDawnVisualRevision','v8')
    if albedo is not None:
        uv_color=me.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-850,-500)
        uv_color.set_editor_property('u_tiling',tiling[0]);uv_color.set_editor_property('v_tiling',tiling[1])
        sample_color=me.create_material_expression(mat,u.MaterialExpressionTextureSample,-400,-500)
        sample_color.set_editor_property('texture',albedo)
        sample_color.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        require_material_link(me.connect_material_expressions(uv_color,'',sample_color,''),name+': ground UV')
        require_material_link(me.connect_material_property(sample_color,'RGB',u.MaterialProperty.MP_BASE_COLOR),name+': ground color')
    me.recompile_material(mat);return owned(mat)

def localized(key,value):return u.DawnAssetTools.localized_text(str(key),str(value))

def create_narrative():
    REPORT['stage']='narrative'
    path=BASE+'/Narrative/DA_DawnNarrative'
    source_file=SOURCE/'Narrative/episode.json'
    action,asset,source_hash=source_plan(source_file,path)
    if action.startswith('preserve'):
        REPORT['preserved'].append(path)
        return asset
    doc=json.loads(source_file.read_text(encoding='utf-8'))
    if action=='create':
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.DawnNarrativeData)
        asset=TOOLS.create_asset('DA_DawnNarrative',BASE+'/Narrative',u.DawnNarrativeData,factory)
    rows=[]
    for row in doc['Nodes']:
        node=u.DawnDialogueNode();node.set_editor_property('id',row['Id']);node.set_editor_property('speaker',localized(row['Id']+'.Speaker',row['Speaker']))
        node.set_editor_property('text',localized(row['TextKey'],row['Text']));node.set_editor_property('repeat_text',localized(row['TextKey']+'.Repeat',row.get('RepeatText','')));node.set_editor_property('display_note',localized(row['Id']+'.DisplayNote',row.get('DisplayNote','')))
        for field in ('Portrait','Illustration'):
            if row.get(field):
                # TSoftObjectPtr<UTexture2D> is exposed as a Texture2D object to
                # Editor Python, not as an FSoftObjectPath struct. UE serializes
                # the assigned object as a soft reference in the DataAsset.
                texture=need(BASE+'/Illustrations/'+row[field])
                if not isinstance(texture,u.Texture2D):raise TypeError('Expected Texture2D for '+row['Id']+'.'+field)
                node.set_editor_property(field.lower(),texture)
        node.set_editor_property('next_node',row.get('NextNode',''));node.set_editor_property('content_kind',row['ContentKind']);node.set_editor_property('scripture_reference',row['ScriptureReference']);node.set_editor_property('source_note',row['SourceNote'])
        choices=[]
        for c in row.get('Choices',[]):
            choice=u.DawnChoice();choice.set_editor_property('id',c['Id']);choice.set_editor_property('text',localized(c['TextKey'],c['Text']));choice.set_editor_property('next_node',c['NextNode']);choices.append(choice)
        node.set_editor_property('choices',choices);rows.append(node)
    asset.set_editor_property('nodes',rows);asset.set_editor_property('content_version',doc.get('ContentVersion',1));LIB.set_metadata_tag(asset,'PathOfDawnSourceSHA256',source_hash)
    error=u.DawnAssetTools.validate_narrative(asset)
    if error:raise RuntimeError('Narrative validation: '+error)
    return save_source_asset(asset,path,source_file,source_hash,action)

def blueprint(name,parent):
    REPORT['stage']='blueprint:'+name
    path=BASE+'/Characters/'+name
    asset=existing(path)
    if asset:return asset
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',parent)
    bp=TOOLS.create_asset(name,BASE+'/Characters',u.Blueprint,factory)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    return owned(bp)

def spawn(cls,label,loc,rotation=(0,0,0),scale=None):
    a=ACTORS.spawn_actor_from_class(cls,u.Vector(*loc),u.Rotator(*rotation));a.set_actor_label(label)
    a.set_editor_property('tags',[u.Name('PathOfDawnGenerated')])
    if scale:a.set_actor_scale3d(u.Vector(*scale))
    return a

def static(label,mesh,loc,rotation=(0,0,0),scale=None,material=None,collision=True):
    a=spawn(u.StaticMeshActor,label,loc,rotation,scale);c=a.static_mesh_component;c.set_static_mesh(mesh)
    if material:c.set_material(0,material)
    c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if collision else u.CollisionEnabled.NO_COLLISION)
    return a

def barrier(label,loc,scale):
    a=static(label,need('/Engine/BasicShapes/Cube'),loc,scale=scale)
    a.set_actor_hidden_in_game(True)
    return a

def interact(identifier,display,mesh,loc,rotation=(0,0,0),character=False):
    a=spawn(u.DawnInteractable,'Interact_'+identifier,loc,rotation)
    a.set_editor_property('stable_id',identifier);a.set_editor_property('interaction_id',identifier);a.set_editor_property('display_name',localized('Object.'+identifier,display));a.set_editor_property('character',character)
    a.set_editor_property('tags',[u.Name('PathOfDawnGenerated'),u.Name('DawnId:'+identifier)])
    a.get_editor_property('mesh').set_static_mesh(need(path_model(mesh)))
    if identifier=='Net':a.set_editor_property('prepared_mesh',need(path_model('SM_NetPrepared')))
    return a

def create_sequence(camera):
    REPORT['stage']='arrival-sequence'
    path=BASE+'/Cinematics/LS_Arrival'
    if existing(path):return need(path)
    seq=TOOLS.create_asset('LS_Arrival',BASE+'/Cinematics',u.LevelSequence,u.LevelSequenceFactoryNew())
    seq.set_display_rate(u.FrameRate(30,1));seq.set_playback_start(0);seq.set_playback_end(600)
    binding=seq.add_possessable(camera);track=binding.add_track(u.MovieScene3DTransformTrack);section=track.add_section();section.set_range(0,600)
    channels=section.get_all_channels()
    def transform_at(position):
        dx,dy,dz=-position[0],150-position[1],100-position[2]
        pitch=math.degrees(math.atan2(dz,math.hypot(dx,dy)));yaw=math.degrees(math.atan2(dy,dx))
        # MovieScene transform channels: Translation XYZ, Rotation roll/pitch/yaw, Scale XYZ.
        return tuple(position)+(0.,pitch,yaw,1.,1.,1.)
    start=transform_at((-750.,-900.,420.));end=transform_at((-350.,-550.,250.))
    for channel,a,b in zip(channels,start,end):channel.add_key(u.FrameNumber(0),a);channel.add_key(u.FrameNumber(599),b)
    cut=seq.add_track(u.MovieSceneCameraCutTrack);cut_section=cut.add_section();cut_section.set_range(0,600)
    binding_id=u.MovieSceneObjectBindingID();binding_id.set_editor_property('guid',binding.get_id());cut_section.set_camera_binding_id(binding_id)
    return owned(seq)

def create_map():
    REPORT['stage']='map'
    if LIB.does_asset_exist(MAP):
        REPORT['preserved'].append(MAP);return
    # Work in a transient world. A failed spawn/import must not leave a blank protected L_Galilee.
    world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:raise RuntimeError('Cannot create transient demo map')
    plane=need('/Engine/BasicShapes/Plane')
    water=make_material('M_LakeWater',(.055,.13,.15),.24,True,need(BASE+'/Environment/T_LakeNormal'))
    sand=make_material('M_ShoreSurface',(.47,.40,.28),.94,False,need(BASE+'/Environment/T_ShoreNormal'),need(BASE+'/Environment/T_ShoreAlbedo'),(46.,29.))
    # A flat invisible collision surface keeps navigation deterministic while the
    # authored ground, stones and foliage provide the visible organic silhouette.
    barrier('Walkable_shore',(0,-550,-55),(46,29,1))
    static('ShoreGround',need(path_model('SM_ShoreGround')),(0,-550,-4),material=sand,collision=False)
    # Cosmetic land continues beyond the closed gameplay bounds, so turning the
    # camera never reveals the clearing as a floating rectangular platform.
    for side in (-1,1):
        static('ShoreBackdrop_%d'%side,need(path_model('SM_ShoreGround')),(side*4540,-550,-12),material=sand,collision=False)
    static('SouthBackdrop',need(path_model('SM_ShoreGround')),(0,-4020,-18),scale=(3,1.5,1),material=sand,collision=False)
    static('Lake',plane,(0,11200,-9),scale=(600,210,1),material=water,collision=False)
    barrier('Boundary_Water',(0,875,180),(47,.7,4));barrier('Boundary_West',(-2300,-550,180),(.7,30,4));barrier('Boundary_East',(2300,-550,180),(.7,30,4))
    barrier('Walkable_VillageLane',(0,-2675,-55),(9.4,16.5,1))
    static('VillageLaneGround',need(path_model('SM_ShoreGround')),(0,-2675,-4),scale=(.205,.59,1),material=sand,collision=False)
    barrier('Boundary_SouthWest',(-1385,-2000,180),(18.3,.7,4));barrier('Boundary_SouthEast',(1385,-2000,180),(18.3,.7,4))
    barrier('Boundary_LaneWest',(-470,-2675,180),(.7,17.2,4));barrier('Boundary_LaneEast',(470,-2675,180),(.7,17.2,4));barrier('Boundary_VillageEnd',(0,-3500,180),(10,.7,4))
    rng=random.Random(50311)
    slab=need(path_model('SM_PathSlab'))
    # Broken, staggered limestone paving instead of a rectangular cube grid.
    for j in range(39):
        y=-3420+j*88
        bend=28*math.sin(j*.21)
        for i in range(3):
            if i!=1 and rng.random()<.12:continue
            static('PathStone_%02d_%d'%(j,i),slab,((i-1)*76+bend+rng.uniform(-10,10),y+rng.uniform(-14,14),-3),rotation=(0,rng.uniform(-23,23),0),scale=(rng.uniform(.78,1.02),rng.uniform(.82,1.08),rng.uniform(.7,.95)),collision=False)
    wall=need(path_model('SM_StoneWall'))
    for side in (-1,1):
        for j in range(3):static('LaneLowWall_%d_%d'%(side,j),wall,(side*435,-2250-j*400,-4),rotation=(0,90+side*2,0),scale=(1,.85,.52+(.08 if j%2 else 0)))
        static('VillageGatePillar_%d'%side,wall,(side*270,-3375,-3),scale=(.32,1.1,1.55))
    # The lintel uses rough stone geometry; no visible primitive cubes remain.
    static('VillageGateLintel',wall,(0,-3375,265),scale=(1.58,1.2,.24))
    static('LaneJar',need(path_model('SM_Jar')),(300,-2760,-3),scale=(.82,.82,.82))
    village=interact('Village','마을로 이어지는 돌길','SM_ShoreRock',(0,-3200,0))
    village.get_editor_property('mesh').set_relative_scale3d(u.Vector(.7,.7,1.8))
    rock=need(path_model('SM_ShoreRock'))
    for i in range(25):
        x=-2200+i*180
        # Leave the two working boats and interaction approach clear.
        if -1400<x<-650 or -160<x<470:continue
        static('ShoreRock_%02d'%i,rock,(x,690+rng.uniform(-45,75),-10),rotation=(rng.uniform(-6,6),rng.uniform(0,360),rng.uniform(-5,5)),scale=(rng.uniform(.65,1.7),rng.uniform(.6,1.2),rng.uniform(.45,.9)))
    for x in (-1480,1480):
        for j in range(3):static('StoneWall_%d_%d'%(x,j),wall,(x,-1590+j*390,-5),rotation=(0,88+j*2,0),scale=(1,1,.8 if x<0 else 1))
    static('StoneSpace_Back',wall,(950,-1800,-4),rotation=(0,-3,0))
    static('StoneSpace_Canopy',need(path_model('SM_Canopy')),(1050,-1170,-5),rotation=(0,-7,0))
    for i,(x,y,size) in enumerate(((900,-1090,.85),(1020,-1095,.65),(950,-970,.72),(1240,-1390,.92),(1180,-1530,.55))):
        static('Jar_%d'%i,need(path_model('SM_Jar')),(x,y,-5),rotation=(0,i*37,0),scale=(size,size,size))
    # Vegetation frames the little clearing; no tree canopy collision blocks the path.
    trees=[(-1930,-1570,1.14),(-1750,-770,.95),(-1920,150,.85),(1880,-1550,1.1),(1880,-550,.92),(2070,330,.82),(-680,-2350,.9),(680,-2810,.86),(-750,-3390,1.1),(940,-3500,1.05),(-650,-280,.8),(690,-50,.78),(-3150,-1050,1.2),(3200,-1400,1.15),(-2900,-2540,1.05),(2850,-2700,1.2),(-1050,-4500,1.1),(1250,-4480,1.25)]
    for i,(x,y,size) in enumerate(trees):
        static('OliveTree_%02d'%i,need(path_model('SM_OliveTree')),(x,y,-4),rotation=(0,rng.uniform(0,360),0),scale=(size,size,size),collision=False)
        for j in range(3):static('TreeStone_%02d_%d'%(i,j),rock,(x+rng.uniform(-110,110),y+rng.uniform(-90,90),-12),rotation=(0,rng.uniform(0,360),0),scale=(.5,.6,.35),collision=False)
    # Workaday props frame the first view without closing the route to the net.
    static('NearLowWall',wall,(720,-650,-5),rotation=(0,95,0),scale=(.8,.8,.38))
    for i,(x,y,size) in enumerate(((-390,-590,.72),(-460,-550,.55),(620,-670,.8))):
        static('WorkingJar_%d'%i,need(path_model('SM_Jar')),(x,y,-5),rotation=(0,i*51,0),scale=(size,size,size))
    for i in range(27):
        x=-2180+i*170
        if -1450<x<-650 or -200<x<500:continue
        static('ShoreReeds_%02d'%i,need(path_model('SM_ReedClump')),(x,745+rng.uniform(-45,45),-15),rotation=(0,rng.uniform(0,360),0),scale=(.8,.8,rng.uniform(.55,.95)),collision=False)
    # A few stones lead to the net without obscuring any interaction object.
    for i in range(6):static('NetPath_%d'%i,slab,(-120-i*88,-290+i*38,-3),rotation=(0,rng.uniform(-40,40),0),scale=(.65,.75,.7),collision=False)
    # Two boats match Luke 5:2; secondary boat and partners are compressed into narration.
    interact('Boat','작은 배','SM_Boat',(130,540,-9),(0,10,0));static('SecondBoat',need(path_model('SM_Boat')),(-1000,650,-8),rotation=(0,22,0),scale=(.85,.85,.85))
    interact('Net','낡은 그물','SM_Net',(-720,40,-5));interact('Stone','물가의 돌','SM_ShoreRock',(980,380,-3))
    interact('Simon','시몬','SM_Simon',(-180,110,-4),(0,-30,0),True);interact('Jesus','예수님','SM_Jesus',(180,220,-4),(0,-105,0),True)
    spawn(u.PlayerStart,'PlayerStart',(0,-950,110),(0,90,0))
    bp=need(BASE+'/Characters/BP_Traveler');pawn_class=bp.generated_class();game_bp=need(BASE+'/Characters/BP_DawnGameMode');game_cdo=u.get_default_object(game_bp.generated_class())
    if game_bp.get_path_name() in REPORT['created']:
        game_cdo.set_editor_property('default_pawn_class',pawn_class)
        if not LIB.save_loaded_asset(game_bp,only_if_is_dirty=False):raise RuntimeError('Cannot save BP_DawnGameMode default pawn')
    world.get_world_settings().set_editor_property('default_game_mode',game_bp.generated_class())
    sky=spawn(u.SkyAtmosphere,'DawnSky',(0,0,0))
    sun=spawn(u.DirectionalLight,'DawnSun',(0,0,1000),(-16,-42,0));lc=sun.get_component_by_class(u.DirectionalLightComponent);lc.set_editor_property('intensity',3.4);lc.set_editor_property('light_color',u.Color(255,218,173,255));lc.set_editor_property('atmosphere_sun_light',True)
    fill=spawn(u.SkyLight,'DawnFill',(0,0,500));fill.get_component_by_class(u.SkyLightComponent).set_editor_property('intensity',.65);fill.get_component_by_class(u.SkyLightComponent).set_editor_property('real_time_capture',True)
    fog=spawn(u.ExponentialHeightFog,'LakeMist',(0,900,10));fog.get_component_by_class(u.ExponentialHeightFogComponent).set_editor_property('fog_density',.018);fog.get_component_by_class(u.ExponentialHeightFogComponent).set_editor_property('fog_height_falloff',.25)
    ridge=need(path_model('SM_DistantRidge'))
    for i,(x,y,sx,sz) in enumerate(((-16000,20500,1.8,2.1),(-4000,19000,1.6,1.8),(7200,19800,1.5,2.5),(17000,21000,1.7,1.9))):
        static('DistantRidge_%d'%i,ridge,(x,y,-80),rotation=(0,(i-1)*8,0),scale=(sx,1.2,sz),collision=False)
    camera=spawn(u.CineCameraActor,'ArrivalCamera',(-750,-900,420),(-13.93,54.46,0));camera.get_cine_camera_component().set_editor_property('current_focal_length',32.)
    # Runtime controller owns ambience, volume settings and rewind cancellation.
    LIB.set_metadata_tag(world,'PathOfDawnVisualRevision','v8')
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Final map save failed; inspect the failed output before retrying')
    REPORT['created'].append(MAP)

def ensure_arrival_sequence():
    if LIB.does_asset_exist(BASE+'/Cinematics/LS_Arrival'):
        REPORT['preserved'].append(BASE+'/Cinematics/LS_Arrival');return
    if not LEVELS.load_level(MAP):raise RuntimeError('Cannot load final map to bind arrival camera')
    cameras=[actor for actor in ACTORS.get_all_level_actors() if isinstance(actor,u.CineCameraActor) and actor.get_actor_label()=='ArrivalCamera']
    if len(cameras)!=1:raise RuntimeError('Expected exactly one ArrivalCamera in the saved map')
    create_sequence(cameras[0])

def source_entries():
    return [(VISUAL_SOURCE/'Illustrations'/(x+'.png'),BASE+'/Illustrations/'+x) for x in IMAGES]+[(VISUAL_SOURCE/'Models'/(x+'.fbx'),path_model(x)) for x in MODELS]+[(SOURCE/'Audio'/(x+'.wav'),BASE+'/Audio/'+x) for x in SOUNDS]+[(VISUAL_SOURCE/'Models'/(x+'.png'),BASE+'/Environment/'+x) for x in ('T_LakeNormal','T_ShoreAlbedo','T_ShoreNormal')]+[(SOURCE/'Fonts/NotoSansKR.otf',BASE+'/UI/FF_Korean'),(SOURCE/'Narrative/episode.json',BASE+'/Narrative/DA_DawnNarrative')]

def verify():
    REPORT['stage']='verify:required-assets'
    required=[MAP,BASE+'/UI/F_Korean',BASE+'/Narrative/DA_DawnNarrative',BASE+'/Cinematics/LS_Arrival',BASE+'/Characters/BP_Traveler',BASE+'/Characters/BP_DawnGameMode']
    required += [BASE+'/Illustrations/'+x for x in IMAGES]+[path_model(x) for x in MODELS]+[BASE+'/Audio/'+x for x in SOUNDS]
    required += [BASE+'/Environment/'+x for x in ('T_LakeNormal','T_ShoreAlbedo','T_ShoreNormal','M_LakeWater','M_ShoreSurface')]
    for path in required:need(path)
    for path in (MAP,BASE+'/Environment/M_LakeWater',BASE+'/Environment/M_ShoreSurface'):
        if LIB.get_metadata_tag(need(path),'PathOfDawnVisualRevision')!='v8':
            raise RuntimeError('Older or untracked visual asset preserved: '+path+'. Extract v8 into a fresh folder without copying prior Content; existing maps/materials are never silently overwritten.')
    for filename,path in source_entries():
        action,_,_=source_plan(filename,path)
        if action in ('create','refresh'):raise RuntimeError('Persisted content is stale or missing: '+path+'. Run generation before verification/cook.')
    data=need(BASE+'/Narrative/DA_DawnNarrative');error=u.DawnAssetTools.validate_narrative(data)
    if error:raise RuntimeError(error)
    REPORT['stage']='verify:map-and-player'
    if not LEVELS.load_level(MAP):raise RuntimeError('Saved map cannot be loaded')
    # Check persisted Blueprint defaults as well as existence. A prior failed
    # generation may have saved a Blueprint before assigning its component mesh.
    traveler_class=need(BASE+'/Characters/BP_Traveler').generated_class()
    if not traveler_class:raise RuntimeError('BP_Traveler has no generated class; compile it in Editor')
    traveler_cdo=u.get_default_object(traveler_class)
    body=traveler_cdo.get_editor_property('traveler_body')
    expected_body=need(path_model('SM_Traveler'))
    if not body or body.get_editor_property('static_mesh')!=expected_body:
        raise RuntimeError('BP_Traveler default TravelerBody must reference SM_Traveler; existing Blueprint is preserved for Editor review')
    game_class=need(BASE+'/Characters/BP_DawnGameMode').generated_class()
    if not game_class:raise RuntimeError('BP_DawnGameMode has no generated class; compile it in Editor')
    if u.get_default_object(game_class).get_editor_property('default_pawn_class')!=traveler_class:
        raise RuntimeError('BP_DawnGameMode default pawn must reference BP_Traveler; existing Blueprint is preserved for Editor review')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if not world:raise RuntimeError('No Editor world after loading L_Galilee')
    if world.get_world_settings().get_editor_property('default_game_mode')!=game_class:
        raise RuntimeError('L_Galilee default game mode must reference BP_DawnGameMode; existing map is preserved for Editor review')
    REPORT['player_references']={'traveler_class':traveler_class.get_path_name(),'body_mesh':expected_body.get_path_name(),'game_mode_class':game_class.get_path_name()}
    REPORT['stage']='verify:interactables-and-font'
    ids=[]
    for a in ACTORS.get_all_level_actors():
        if isinstance(a,u.DawnInteractable):
            ids.append(str(a.get_editor_property('stable_id')))
            if not a.get_editor_property('mesh').get_editor_property('static_mesh'):raise RuntimeError('Empty interactable mesh')
    for name in ('Net','Boat','Stone','Simon','Jesus','Village'):
        if ids.count(name)!=1:raise RuntimeError('Expected one stable actor '+name+'. Existing maps are preserved; review and add the missing landmark in Editor instead of overwriting an edited map.')
    if not u.DawnAssetTools.has_runtime_font(need(BASE+'/UI/F_Korean')):
        raise RuntimeError('Composite font has no typeface')
    REPORT['required']=required;REPORT['stable_ids']=ids

try:
    INDEX=guard.load_index(INDEXFILE)
    if not VERIFY:
        for path in (MAP,BASE+'/Environment/M_LakeWater',BASE+'/Environment/M_ShoreSurface'):
            if LIB.does_asset_exist(path) and LIB.get_metadata_tag(need(path),'PathOfDawnVisualRevision')!='v8':
                raise RuntimeError('Existing older map/material preserved: '+path+'. Use a fresh v8 source folder without copying old Content, or perform a reviewed manual upgrade in Editor.')
        files=[filename for filename,_ in source_entries()]
        missing=[str(x) for x in files if not x.is_file()]
        if missing:raise RuntimeError('Missing authoring inputs: '+', '.join(missing))
        # Reject source/package conflicts before any import starts.
        for filename,path in source_entries():
            action,_,_=source_plan(filename,path)
            if path.endswith('/FF_Korean') and action=='refresh':raise RuntimeError('Korean font source changed; targeted font-face/composite-font review required')
        for x in IMAGES:import_file(VISUAL_SOURCE/'Illustrations'/(x+'.png'),BASE+'/Illustrations',x,'image')
        for x in MODELS:import_file(VISUAL_SOURCE/'Models'/(x+'.fbx'),path_model(x).rsplit('/',1)[0],x,'mesh')
        import_file(VISUAL_SOURCE/'Models/T_LakeNormal.png',BASE+'/Environment','T_LakeNormal','normal')
        import_file(VISUAL_SOURCE/'Models/T_ShoreNormal.png',BASE+'/Environment','T_ShoreNormal','normal')
        import_file(VISUAL_SOURCE/'Models/T_ShoreAlbedo.png',BASE+'/Environment','T_ShoreAlbedo','albedo')
        for x in SOUNDS:import_file(SOURCE/'Audio'/(x+'.wav'),BASE+'/Audio',x,'sound')
        face=import_file(SOURCE/'Fonts/NotoSansKR.otf',BASE+'/UI','FF_Korean','font')
        REPORT['stage']='composite-font'
        if not u.DawnAssetTools.create_composite_font(face,BASE+'/UI/F_Korean'):raise RuntimeError('Composite Korean font generation failed')
        create_narrative()
        bp=blueprint('BP_Traveler',u.DawnPlayerCharacter)
        if bp.get_path_name() in REPORT['created']:
            u.get_default_object(bp.generated_class()).get_editor_property('traveler_body').set_editor_property('static_mesh',need(path_model('SM_Traveler')))
            if not LIB.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Cannot save BP_Traveler default body mesh')
        blueprint('BP_DawnGameMode',u.DawnGameMode)
        create_map()
        ensure_arrival_sequence()
    verify();REPORT['stage']='complete';REPORT['status']='passed'
    u.log('POD_ASSETS_'+('VERIFIED' if VERIFY else 'GENERATED'))
except Exception as exc:
    REPORT['status']='failed';REPORT['error']=str(exc);REPORT['traceback']=traceback.format_exc();u.log_error(REPORT['traceback']);raise
finally:
    REPORTFILE.write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
