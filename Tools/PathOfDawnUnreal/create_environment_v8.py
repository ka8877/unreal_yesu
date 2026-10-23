"""Create original, material-colored Galilee environment meshes using Blender 4.3+.

blender -b --python-exit-code 1 --python Tools/PathOfDawnUnreal/create_environment_v8.py -- --render
Outputs are preserved: use a fresh --output-dir for a new revision. These are
source models and Blender review images, not generated Unreal assets/screenshots.
All geometry/materials are authored here; no external textures or downloaded art.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
P = argparse.ArgumentParser(description=__doc__)
P.add_argument('--output-dir', type=Path, default=ROOT/'SourceArt/PathOfDawnUnreal/VisualV8/Models')
P.add_argument('--render', action='store_true')
A = P.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT = A.output_dir.resolve()
IDS = ['SM_Boat', 'SM_Net', 'SM_NetPrepared', 'SM_Jar', 'SM_StoneWall',
       'SM_Canopy', 'SM_ShoreRock', 'SM_OliveTree', 'SM_ReedClump', 'SM_PathSlab', 'SM_ShoreGround', 'SM_DistantRidge']
protected = [OUT/(n+'.fbx') for n in IDS]+[OUT/'EnvironmentV8.blend', OUT/'environment-manifest.json', OUT/'EnvironmentPreview.png', OUT/'T_LakeNormal.png', OUT/'T_ShoreAlbedo.png', OUT/'T_ShoreNormal.png']
if any(p.exists() for p in protected):
    raise SystemExit('Preserved existing environment sources. Choose a fresh --output-dir.')
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
RNG = random.Random(5081108)


def mat(name, color, rough=.85):
    m = bpy.data.materials.new('V8_'+name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough
    return m


M = {}
for key, color in {
    'WoodHoney': (.33,.225,.132), 'WoodWarm': (.275,.172,.095),
    'WoodFaded': (.42,.32,.213), 'WoodPale': (.385,.292,.193),
    'WoodDark': (.17,.115,.068), 'WoodEnd': (.23,.145,.077),
    'IronOxide': (.095,.075,.052), 'Rope': (.36,.29,.18),
    'RopeLight': (.52,.445,.30), 'Linen': (.72,.655,.49),
    'LinenShade': (.58,.52,.375), 'LinenLight': (.79,.73,.57),
    'WovenBlue': (.215,.315,.31), 'Clay': (.42,.225,.125),
    'ClayLight': (.54,.315,.19), 'ClayInner': (.28,.155,.09),
    'Limestone': (.57,.515,.405), 'LimestoneCream': (.64,.585,.47),
    'LimestoneGrey': (.48,.465,.39), 'LimestoneOchre': (.55,.48,.36),
    'LimestoneLight': (.69,.64,.53), 'Mortar': (.39,.365,.29),
    'Sand': (.50,.443,.327), 'SandPale': (.56,.502,.38),
    'SandDark': (.44,.395,.29), 'SandWarm': (.52,.455,.337),
    'DampShore': (.305,.305,.25), 'OliveBark': (.24,.225,.16),
    'OliveBarkPale': (.37,.345,.25), 'OliveLeaf': (.22,.29,.16),
    'OliveLeafLight': (.32,.38,.22), 'OliveLeafSilver': (.43,.47,.32),
    'ReedGreen': (.32,.375,.18), 'ReedPale': (.52,.48,.25),
    'ReedHead': (.275,.22,.12), 'LakePreview': (.20,.335,.33),
    'DistantRidge': (.31,.365,.36), 'DistantRidgePale': (.37,.41,.395),
}.items():
    M[key] = mat(key, color, .3 if key=='LakePreview' else .87)
WOOD = ['WoodHoney','WoodWarm','WoodFaded','WoodPale']
STONE = ['Limestone','LimestoneCream','LimestoneGrey','LimestoneOchre','LimestoneLight']


class Mesh:
    """Accumulate one material-aware mesh without thousands of Blender objects."""
    def __init__(self):
        self.v, self.f, self.mi, self.sm = [], [], [], []
        self.mats = list(M)

    def add(self, verts, faces, material, smooth=True):
        start=len(self.v)
        self.v.extend(tuple(v) for v in verts)
        for i,face in enumerate(faces):
            self.f.append(tuple(i+start for i in face))
            self.mi.append(self.mats.index(material[i] if isinstance(material,list) else material))
            self.sm.append(smooth)

    def tube(self, points, radii, material, sides=8, caps=True):
        points=[Vector(p) for p in points]
        if isinstance(radii, (int,float)): radii=[radii]*len(points)
        v=[]
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            ref=Vector((0,0,1)) if abs(tangent.z)<.92 else Vector((0,1,0))
            u=tangent.cross(ref).normalized(); w=tangent.cross(u).normalized()
            for k in range(sides):
                t=k*math.tau/sides
                v.append(p+radii[i]*(u*math.cos(t)+w*math.sin(t)))
        f=[]
        for i in range(len(points)-1):
            for j in range(sides):
                a=i*sides+j; b=i*sides+(j+1)%sides
                f.append((a,b,b+sides,a+sides))
        if caps:
            f += [tuple(reversed(range(sides))), tuple(range((len(points)-1)*sides,len(points)*sides))]
        self.add(v,f,material)

    def ellipsoid(self, center, scale, material, seg=14, rings=9, wobble=0):
        c=Vector(center); v=[]
        for j in range(rings+1):
            a=math.pi*j/rings
            for i in range(seg):
                t=i*math.tau/seg
                q=1+wobble*math.sin(a)*(math.sin(3*t+2*a)*.45+math.cos(5*t-3*a)*.35)
                v.append(c+Vector((scale[0]*math.sin(a)*math.cos(t)*q,
                                   scale[1]*math.sin(a)*math.sin(t)*q,
                                   scale[2]*math.cos(a)*q)))
        f=[]
        for j in range(rings):
            for i in range(seg):
                a=j*seg+i; b=j*seg+(i+1)%seg
                f.append((a,b,b+seg,a+seg))
        self.add(v,f,material)

    def board(self, points, widths, thickness, material):
        """Solid plank following a strip; each center sample has local cross vector."""
        v=[]
        for p,w in zip(points,widths):
            p=Vector(p); w=Vector(w)
            v += [p-w/2+Vector((0,0,thickness/2)),p+w/2+Vector((0,0,thickness/2)),
                  p+w/2-Vector((0,0,thickness/2)),p-w/2-Vector((0,0,thickness/2))]
        f=[(3,2,1,0)]
        for i in range(len(points)-1):
            for j in range(4):f.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
        f.append(tuple(range(4*(len(points)-1),4*len(points))))
        self.add(v,f,material)

    def rock(self, center, scale, material, phase=0, seg=13, rings=7):
        v=[]; c=Vector(center)
        for j in range(rings+1):
            a=math.pi*j/rings
            for i in range(seg):
                t=i*math.tau/seg
                q=1+math.sin(a)*(.095*math.sin(t*3+a*2+phase)+.06*math.cos(t*5-a*3+phase))
                z=math.cos(a)
                z=max(-.72,z)
                v.append(c+Vector((scale[0]*math.sin(a)*math.cos(t)*q,
                                   scale[1]*math.sin(a)*math.sin(t)*q,scale[2]*z*q)))
        f=[]
        for j in range(rings):
            for i in range(seg):
                a=j*seg+i;b=j*seg+(i+1)%seg
                f.append((a,b,b+seg,a+seg))
        self.add(v,f,material)

    def limestone_block(self, center, scale, material):
        # Three irregular bevel rings, naturally chipped corners and tilted top.
        cx,cy,cz=center; sx,sy,sz=scale
        outline=[(-.34,-.5),(.32,-.5),(.5,-.28),(.5,.31),(.32,.5),(-.32,.5),(-.5,.31),(-.5,-.29)]
        v=[]
        jitter=[(RNG.uniform(-.075,.075),RNG.uniform(-.09,.09)) for _ in outline]
        for k,(h,shrink) in enumerate([(-.5,.83),(-.36,1),(.32,.97),(.5,.79)]):
            for i,(x,y) in enumerate(outline):
                jx,jy=jitter[i]
                v.append((cx+(x+jx)*sx*shrink,cy+(y+jy)*sy*shrink,cz+(h+RNG.uniform(-.065,.065))*sz))
        f=[tuple(reversed(range(8))),tuple(range(24,32))]
        for k in range(3):
            for i in range(8):
                a=k*8+i;b=k*8+(i+1)%8;f.append((a,b,b+8,a+8))
        self.add(v,f,material,False)

    def leaf(self, base, tip, width, material, roll=0):
        a,b=Vector(base),Vector(tip); d=b-a
        u=d.cross(Vector((0,0,1)))
        if u.length<.001:u=Vector((1,0,0))
        u.normalize(); n=d.normalized().cross(u).normalized()
        u=u*math.cos(roll)+n*math.sin(roll); n=d.normalized().cross(u).normalized()
        # Closed slender lens: both sides visible in UE's one-sided materials.
        centers=[a,a+d*.24+n*.012,a+d*.58+n*.019,b]
        widths=[.002,width*.40,width*.5,.001]
        v=[]
        for c,w in zip(centers,widths):v += [c-u*w,c+n*.002,c+u*w,c-n*.002]
        f=[]
        for k in range(3):
            for j in range(4):f.append((k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j))
        f += [(3,2,1,0),(12,13,14,15)]
        self.add(v,f,material)

    def object(self,name):
        mesh=bpy.data.meshes.new(name+'_Geometry');mesh.from_pydata(self.v,[],self.f);mesh.update()
        o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
        for key in self.mats:mesh.materials.append(M[key])
        for i,p in enumerate(mesh.polygons):p.material_index=self.mi[i];p.use_smooth=self.sm[i]
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        # Remove unused slots before FBX so imports do not create irrelevant materials.
        bpy.ops.object.material_slot_remove_unused()
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=.000005);bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        if name=='SM_StoneWall':
            rounded=o.modifiers.new('Weathered stone faces','SUBSURF');rounded.levels=1;rounded.render_levels=1
            bpy.ops.object.modifier_apply(modifier=rounded.name)
        tri=o.modifiers.new('Explicit portable triangles','TRIANGULATE');tri.keep_custom_normals=True
        bpy.ops.object.modifier_apply(modifier=tri.name)
        return o


def boat():
    m=Mesh(); stations=33
    def hull(t,a,inset=0):
        width=.715*(max(.0001,1-t*t)**.57)+.008
        rise=.115+.34*abs(t)**3
        return Vector((t*2.05,math.sin(a)*(width-inset),rise+(1-math.cos(a))*.62))
    # Narrow shaped hull planks, actual thickness and visible caulk gaps.
    for side in (-1,1):
        for row in range(7):
            low=(row/7)*1.39+.009; high=((row+1)/7)*1.39-.009
            v=[]
            for j in range(stations):
                t=-1+2*j/(stations-1)
                for a,inside in [(low,0),(high,0),(high,.026),(low,.026)]:
                    p=hull(t,side*a,inside)
                    if inside:p.z+=.023
                    v.append(p)
            f=[(3,2,1,0)]
            for j in range(stations-1):
                for k in range(4):f.append((4*j+k,4*j+(k+1)%4,4*(j+1)+(k+1)%4,4*(j+1)+k))
            f.append(tuple(range(4*(stations-1),4*stations)))
            m.add(v,f,WOOD[(row+(1 if side<0 else 0))%len(WOOD)])
        pts=[hull(-1+2*j/48,side*1.39)+Vector((0,0,.018)) for j in range(49)]
        m.tube(pts,.034,'WoodPale',10)
        m.tube([p+Vector((0,side*.022,-.048)) for p in pts],.013,'WoodDark',6)
    m.tube([hull(-1+2*j/36,0)-Vector((0,0,.026)) for j in range(37)],.042,'WoodDark',8)
    # Bent internal ribs and small wooden fasteners, all visible in close inspection.
    for j,t in enumerate([-.86,-.68,-.48,-.25,0,.25,.48,.68,.86]):
        points=[hull(t,-1.35+2.70*k/20,.036)+Vector((0,0,.033)) for k in range(21)]
        m.tube(points,.022,'WoodEnd',7)
        for a in [-1.25,-.84,-.42,.42,.84,1.25]:
            p=hull(t,a,-.006)
            m.ellipsoid(p,(.009,.009,.009),'IronOxide',6,4)
    # Worn footboards follow boat bottom; stern/bow seats stop clear of the hull.
    for i in range(5):
        y=(i-2)*.115
        pts=[(x,y,.205+.07*(abs(x)/1.55)**3) for x in [-1.52,-1,-.5,0,.5,1,1.52]]
        m.board(pts,[(0,.107,0)]*len(pts),.027,WOOD[(i+1)%4])
    for x in [-1.13,.10,1.12]:
        width=1.12 if abs(x)<.2 else .98
        m.board([(x,-width/2,.535),(x,0,.537),(x,width/2,.535)],[(.245,0,0)]*3,.045,'WoodFaded')
        for y in [-width*.4,width*.4]:
            m.ellipsoid((x,y,.563),(.009,.009,.006),'IronOxide',6,4)
    # One shaped oar; paddle is tapered, not a rectangular block.
    m.tube([(-1.55,.47,.66),(-.6,.43,.655),(.8,.36,.64)], [.022,.022,.027],'WoodPale',10)
    m.board([(.76,.365,.641),(1.10,.347,.641),(1.62,.32,.64),(1.75,.313,.64)],
            [(0,.05,0),(0,.14,0),(0,.19,0),(0,.12,0)],.025,'WoodPale')
    # A softly coiled mooring rope at the bow.
    pts=[]
    for i in range(181):
        t=i/180*math.tau*3.3;r=.09+.10*i/180
        pts.append((-1.43+math.cos(t)*r,math.sin(t)*r,.46+.014*i/180))
    m.tube(pts,.009,'RopeLight',5)
    return m


def net(prepared=False):
    m=Mesh(); nx=27; ny=17
    def point(i,j):
        u=i/nx; v=j/ny
        x=(u-.5)*2.35;y=(v-.5)*1.52
        if prepared:
            z=.025+.018*math.sin(u*12)*math.sin(v*9)+.055*math.exp(-((u-.82)/.12)**2)
            y+=.035*math.sin(u*13)*(1-v)
        else:
            x+=.065*math.sin(v*11+u*4)
            y*=.78+.11*math.sin(u*9)
            z=.055+.18*math.exp(-((u-.27)/.16)**2)+.11*math.exp(-((v-.25)/.15)**2)
            z+=.035*math.sin(u*16+v*5)**2
        return Vector((x,y,z))
    # Diagonal diamond weave follows drape continuously rather than hard square sticks.
    for i in range(nx+1):
        pts=[point(i+.43*math.sin(j*math.pi/2),j) for j in range(ny+1)]
        if not prepared and i in [11,12]:
            m.tube(pts[:8],.0038,'Rope',5);m.tube(pts[10:],.0038,'Rope',5)
        else:m.tube(pts,.0038,'Rope',5)
    for j in range(ny+1):
        pts=[point(i,j+.36*math.sin(i*math.pi/2)) for i in range(nx+1)]
        if not prepared and j in [8,9]:
            m.tube(pts[:11],.0038,'RopeLight',5);m.tube(pts[13:],.0038,'RopeLight',5)
        else:m.tube(pts,.0038,'RopeLight',5)
    for border in [[point(i,0) for i in range(nx+1)],[point(i,ny) for i in range(nx+1)],
                   [point(0,j) for j in range(ny+1)],[point(nx,j) for j in range(ny+1)]]:
        m.tube(border,.011,'Rope',7)
    for i in range(1,nx,3):
        p=point(i,0)+Vector((0,-.012,.014));m.ellipsoid(p,(.045,.025,.023),'WoodFaded',10,6,.06)
    for i in range(2,nx,5):
        p=point(i,ny);m.ellipsoid(p,(.022,.018,.014),'LimestoneGrey',8,5,.15)
    if prepared:
        patch=[]
        for i in range(25):
            t=i/24; patch.append(point(10+t*4,7.5+1.5*math.sin(t*math.tau*2))+Vector((0,0,.009)))
        m.tube(patch,.006,'LinenLight',6)
        # Cloth repair tie: small cream linen accent makes state perceptible.
        m.tube([point(12,9)+Vector((-.06,0,.03)),point(12,9)+Vector((0,0,.04)),point(12,9)+Vector((.07,.015,.02))],.014,'LinenLight',6)
    else:
        pts=[]
        for i in range(80):
            t=i/79*math.tau*2.3;r=.065+.065*i/79
            pts.append((1.12+r*math.cos(t),.34+r*math.sin(t),.025+.004*i/79))
        m.tube(pts,.011,'RopeLight',6)
    return m


def jar():
    m=Mesh();seg=48
    # Continuous outside, rolled mouth, inside and interior floor: genuinely open vessel.
    profile=[(.11,.015),(.155,.045),(.21,.13),(.245,.28),(.232,.43),(.19,.53),
             (.127,.61),(.11,.66),(.126,.685),(.13,.708),(.117,.72),
             (.095,.71),(.091,.68),(.092,.65),(.108,.60),(.173,.52),
             (.213,.425),(.225,.28),(.19,.14),(.12,.065),(.025,.062)]
    v=[]
    for j,(radius,z) in enumerate(profile):
        for i in range(seg):
            t=i*math.tau/seg
            r=radius*(1+.015*math.sin(t*3+z*4)+.008*math.cos(t*7))
            # Fine wheel-thrown rings are modeled, not a texture dependency.
            v.append((math.cos(t)*r,math.sin(t)*r,z+.002*math.sin(t*2)))
    f=[];face_mats=[]
    for j in range(len(profile)-1):
        for i in range(seg):
            a=j*seg+i;b=j*seg+(i+1)%seg;f.append((a,b,b+seg,a+seg))
            face_mats.append('Clay' if j<8 else 'ClayLight' if j<12 else 'ClayInner')
    f.extend([tuple(reversed(range(seg))),tuple(range((len(profile)-1)*seg,len(profile)*seg))]);face_mats.extend(['ClayInner']*2)
    m.add(v,f,face_mats)
    for s in [-1,1]:
        pts=[]
        for i in range(23):
            t=i/22*math.pi
            pts.append((s*(.119+.15*math.sin(t)),0,.505+.145*math.cos(t)))
        m.tube(pts,[.021+.004*math.sin(i/22*math.pi) for i in range(23)],'ClayLight',9)
    for z,r in [(.655,.112),(.60,.132),(.12,.207)]:
        m.tube([(r*math.cos(i*math.tau/64),r*math.sin(i*math.tau/64),z) for i in range(65)],.0028,'ClayLight',5)
    return m


def wall():
    m=Mesh()
    # Cut a dry-stone wall into independently weathered polygonal limestone pieces.
    # Voronoi packing gives fitted rubble of varied size, with no rectangular rows.
    seeds=[]
    while len(seeds)<43:
        p=Vector((RNG.uniform(-1.97,1.97),RNG.uniform(.03,1.76)))
        if all((p-q).length>.245 for q in seeds):seeds.append(p)
    def clip(poly,normal,bound):
        out=[]
        for i,a in enumerate(poly):
            b=poly[(i+1)%len(poly)];da=a.dot(normal)-bound;db=b.dot(normal)-bound
            if da<=0:out.append(a)
            if (da<=0)!=(db<=0):out.append(a+(b-a)*(da/(da-db)))
        return out
    for si,p in enumerate(seeds):
        poly=[Vector((-2,0)),Vector((2,0)),Vector((2,1.80)),Vector((-2,1.80))]
        for j,q in enumerate(seeds):
            if si==j:continue
            poly=clip(poly,q-p,(q.dot(q)-p.dot(p))*.5)
            if not poly:break
        if len(poly)<3:continue
        center=sum(poly,Vector((0,0)))/len(poly)
        poly=[center+(v-center)*.94 for v in poly];n=len(poly)
        depth=RNG.uniform(.43,.55);front=-depth*.5+RNG.uniform(-.035,.035)
        # Bevel is asymmetric and each face has a shallow irregular ridge.
        verts=[]
        for y,shrink in [(front,.91),(front+.026,1),(depth*.5-.026,1),(depth*.5,.91)]:
            for v in poly:
                q=center+(v-center)*shrink
                verts.append((q.x,y+RNG.uniform(-.012,.012),q.y))
        facecenter=len(verts);verts.append((center.x,front-RNG.uniform(.004,.012),center.y))
        faces=[]
        for i in range(n):faces.append((facecenter,i,(i+1)%n))
        for ring in range(3):
            for i in range(n):faces.append((ring*n+i,ring*n+(i+1)%n,(ring+1)*n+(i+1)%n,(ring+1)*n+i))
        faces.append(tuple(reversed(range(3*n,4*n))))
        m.add(verts,faces,RNG.choice(STONE),True)
    return m


def canopy():
    m=Mesh();nx=27;ny=21
    for x in [-1.38,1.38]:
        for y in [-1.02,1.02]:
            m.tube([(x,y,.015),(x-.025,y+.012,1.05),(x+.012,y,2.19)], [.043,.037,.026],'WoodFaded',9)
            m.tube([(x-.055,y,2.08),(x+.065,y,2.13)],.018,'WoodDark',7)
            # Rope wraps around supports; modest guy lines remain inside asset footprint.
            pts=[(x+.045*math.cos(i*.7),y+.045*math.sin(i*.7),2.10+i*.002) for i in range(26)]
            m.tube(pts,.006,'Rope',5)
    for y in [-1.02,1.02]:m.tube([(-1.4,y,2.13),(0,y,2.15),(1.4,y,2.13)],.028,'WoodHoney',8)
    def cloth(i,j):
        u=i/nx;v=j/ny;x=(u-.5)*2.94;y=(v-.5)*2.20
        z=2.16-.21*math.sin(u*math.pi)-.13*math.sin(v*math.pi)
        z+=.032*math.sin(u*math.pi*8+.3)*math.sin(v*math.pi)+.013*math.sin(u*17+v*8)
        # Loose scalloped overhang at every exposed edge.
        edge=max(abs(u-.5)*2,abs(v-.5)*2)
        z-=.075*max(0,(edge-.87)/.13)
        return Vector((x,y,z))
    v=[cloth(i,j) for j in range(ny+1) for i in range(nx+1)]
    offset=len(v);v += [p-Vector((0,0,.006)) for p in v]
    f=[];face_mats=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=b+nx+1;d=a+nx+1
            material='WovenBlue' if i in [3,4,22,23] else 'LinenLight' if i%5==0 else 'Linen'
            f.extend([(a,b,c,d),(d+offset,c+offset,b+offset,a+offset)]);face_mats.extend([material]*2)
    m.add(v,f,face_mats)
    for boundary in [[cloth(i,0) for i in range(nx+1)],[cloth(i,ny) for i in range(nx+1)],
                     [cloth(0,j) for j in range(ny+1)],[cloth(nx,j) for j in range(ny+1)]]:
        m.tube(boundary,.009,'LinenShade',5)
    return m


def shore_rock():
    m=Mesh();m.rock((0,0,.22),(.46,.35,.30),'LimestoneGrey',1.7,23,12)
    return m


def olive():
    m=Mesh()
    # Gnarled, leaning old trunk composed of merging twists and roots.
    trunk=[(0,0,0),(.04,.025,.35),(-.025,.035,.85),(.13,0,1.30),(.07,-.035,1.75),(.19,.025,2.18)]
    m.tube(trunk,[.23,.185,.145,.13,.095,.045],'OliveBark',12)
    for k in range(5):
        a=k*math.tau/5
        root=[(.43*math.cos(a),.43*math.sin(a),.015),(.23*math.cos(a+.2),.23*math.sin(a+.2),.09),(.08*math.cos(a+.5),.08*math.sin(a+.5),.36)]
        m.tube(root,[.012,.043,.067],'OliveBark',8)
    for k in range(7):
        pts=[]
        for j in range(15):
            z=j/14*1.7;r=.185*(1-z/2.3);a=k*math.tau/7+z*.66
            pts.append((.05+math.cos(a)*r,.01+math.sin(a)*r,z+.03))
        m.tube(pts,[.016]*(len(pts)),'OliveBarkPale' if k%3==0 else 'OliveBark',6)
    # Curved branch hierarchy with clustered individual leaves; avoid radial broom silhouette.
    for k in range(8):
        angle=k*2.399963
        start=Vector((.10,0,1.28+(k%4)*.24))
        end=Vector((math.cos(angle)*RNG.uniform(1.0,1.48),math.sin(angle)*RNG.uniform(1.0,1.40),RNG.uniform(2.8,3.34)))
        mid=start.lerp(end,.60)+Vector((0,0,.32))
        m.tube([start,start.lerp(mid,.42)+Vector((.08,.04,0)),mid,end],[.057,.043,.022,.005],'OliveBark',8)
        for j in range(8):
            t=.22+j*.11
            base=mid.lerp(end,t)
            a=angle+(-1 if j%2 else 1)*RNG.uniform(.48,1.15)
            tip=base+Vector((math.cos(a)*RNG.uniform(.28,.53),math.sin(a)*RNG.uniform(.28,.53),RNG.uniform(-.08,.36)))
            m.tube([base,base.lerp(tip,.5)+Vector((0,0,.06)),tip],[.012,.007,.002],'OliveBarkPale',6)
            for q in range(16):
                along=.02+q/16*.97
                center=base.lerp(tip,along)
                for side in [-1,1]:
                    direction=Vector((math.cos(a+side*1.2),math.sin(a+side*1.2),RNG.uniform(-.35,.7)))
                    leaf_end=center+direction*RNG.uniform(.13,.20)
                    m.leaf(center,leaf_end,RNG.uniform(.037,.052),RNG.choice(['OliveLeaf','OliveLeafLight','OliveLeafSilver']),RNG.uniform(-.8,.8))
            # Small offshoots make the foliage occupy a volume instead of a flat fern.
            for q in range(2):
                center=base.lerp(tip,.40+q*.35)
                a2=a+(-1 if q==0 else 1)*1.0
                end2=center+Vector((math.cos(a2)*.24,math.sin(a2)*.24,.18))
                m.tube([center,end2],[.005,.001],'OliveBarkPale',5)
                for n in range(9):
                    p=center.lerp(end2,n/8)
                    for side in [-1,1]:
                        d=Vector((math.cos(a2+side*1.1),math.sin(a2+side*1.1),RNG.uniform(-.1,.5)))
                        m.leaf(p,p+d*RNG.uniform(.12,.18),RNG.uniform(.033,.047),RNG.choice(['OliveLeaf','OliveLeafLight','OliveLeafSilver']),RNG.uniform(-.8,.8))
    return m


def reeds():
    m=Mesh()
    for k in range(31):
        a=RNG.random()*math.tau;r=math.sqrt(RNG.random())*.32
        base=Vector((math.cos(a)*r,math.sin(a)*r,0))
        height=RNG.uniform(.62,1.61);lean=Vector((RNG.uniform(-.17,.17),RNG.uniform(-.18,.18),0))
        pts=[base+Vector((0,0,height*t))+lean*t*t for t in [0,.25,.5,.75,1]]
        material='ReedPale' if k%4==0 else 'ReedGreen'
        m.tube(pts,[.007,.006,.005,.004,.002],material,5)
        if k%3==0:
            tip=pts[-1];m.tube([tip,tip+Vector((0,0,.12)),tip+Vector((0,0,.18))],[.018,.021,.006],'ReedHead',7)
        for j in range(3):
            h=.18+j*.17
            p=base+Vector((0,0,height*h))+lean*h*h
            d=Vector((math.cos(a+j*1.9)*.33,math.sin(a+j*1.9)*.33,height*.40))
            m.leaf(p,p+d,RNG.uniform(.035,.055),material,RNG.uniform(-.6,.6))
    return m


def path_slab():
    m=Mesh();m.limestone_block((0,0,.035),(.87,.65,.09),'LimestoneCream')
    return m


def ground():
    m=Mesh();nx=64;ny=44;v=[]
    for j in range(ny+1):
        t=j/ny
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*46
            shore=13.25+.95*math.sin(x*.22)+.30*math.sin(x*.73)
            south=-14.4+.18*math.sin(x*.32)
            y=south+(shore-south)*t
            z=-.19*max(0,(t-.925)/.075)**1.4
            # Large central playable surface remains exactly flat; soft shore slope only.
            v.append((x,y,z))
    f=[];face_mats=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=b+nx+1;d=a+nx+1
            x,y,z=v[a]
            wave=math.sin(x*.31+y*.25)+.45*math.cos(x*.82-y*.35)
            # No square color patches: a continuous UE material supplies fine ground detail.
            key='DampShore' if j>=ny-2 else 'Sand'
            f.append((a,b,c,d));face_mats.append(key)
    m.add(v,f,face_mats,False)
    # Closed perimeter to avoid open cut edges from low camera angles.
    boundary=[i for i in range(nx+1)]+[j*(nx+1)+nx for j in range(1,ny+1)]
    boundary += [ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    vv=[Vector(v[i]) for i in boundary];n=len(vv);vv += [p-Vector((0,0,.65)) for p in vv]
    f=[]
    for i in range(n):j=(i+1)%n;f.append((i,j,j+n,i+n))
    m.add(vv,f,'SandDark',False)
    return m


def distant_ridge():
    m=Mesh();nx=72;ny=14;v=[]
    for j in range(ny+1):
        t=j/ny;y=(t-.5)*20
        for i in range(nx+1):
            x=(i/nx-.5)*90
            envelope=math.sin(math.pi*i/nx)**.52
            ridge=(7.5+2.9*math.sin(x*.12+.7)+1.35*math.sin(x*.36)+.55*math.sin(x*.83))*envelope
            shape=math.sin(math.pi*t)**.62
            z=max(0,ridge*shape+.35*math.sin(x*.52+t*9)*shape)
            v.append((x,y,z))
    f=[];face_mats=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=b+nx+1;d=a+nx+1
            f.append((a,b,c,d));face_mats.append('DistantRidgePale' if (i//5+j//4)%3==0 else 'DistantRidge')
    m.add(v,f,face_mats)
    return m


CREATORS=[boat,lambda:net(False),lambda:net(True),jar,wall,canopy,shore_rock,olive,reeds,path_slab,ground,distant_ridge]
models=[];manifest=[]
for name,creator in zip(IDS,CREATORS):
    print('POD_ENV_CREATING',name,flush=True)
    o=creator().object(name);models.append(o)
    if name=='SM_ShoreGround':
        uv=o.data.uv_layers.new(name='UV0')
        for loop in o.data.loops:
            co=o.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv=((co.x+23)/46,(co.y+14.5)/29)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
                             add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',
                             apply_unit_scale=True,mesh_smooth_type='FACE',use_mesh_modifiers=True)
    dimensions=[round(float(v),4) for v in o.dimensions]
    bounds=[[round(min((o.matrix_world@v.co)[axis] for v in o.data.vertices),4),
             round(max((o.matrix_world@v.co)[axis] for v in o.data.vertices),4)] for axis in range(3)]
    manifest.append({'asset_id':name,'file':str((OUT/(name+'.fbx')).relative_to(ROOT)) if OUT.is_relative_to(ROOT) else str(OUT/(name+'.fbx')),
                     'sha256':hashlib.sha256((OUT/(name+'.fbx')).read_bytes()).hexdigest(),
                     'source':'Original geometry authored in create_environment_v8.py; Blender '+bpy.app.version_string,
                     'license':'Project-created; no external geometry, images, or textures', 'temporary':False,
                     'dimensions_m':dimensions,'bounds_m':bounds,'vertices':len(o.data.vertices),'triangles':len(o.data.polygons),
                     'materials':[s.name for s in o.data.materials],
                     'origin_m':[0,0,0],'orientation':'Z up; boat long axis X; ground lake edge +Y',
                     'runtime_path':'/Game/PathOfDawn/Environment/'+name,
                     'modifications':'V8 rebuilt curved and worn surfaces, explicit triangles, FBX face smoothing, material colors',
                     'limitations':'Static mesh source; Unreal import, collision, Lumen and runtime appearance require Windows verification.'})
    o.hide_render=True;o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'EnvironmentV8.blend'))
(OUT/'environment-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Original seamless tangent-space normal texture derived from periodic ripple slopes.
# Integer frequencies make both axes repeat exactly; DirectX/Unreal green convention.
size=512;pixels=[]
waves=[(2,7,.012,.4),(3,-11,.008,1.1),(-5,19,.004,2.4),(11,23,.002,4.1),(17,-13,.0015,.7)]
for y in range(size):
    for x in range(size):
        u=x/size;v=y/size;dx=dy=0
        for fx,fy,amp,phase in waves:
            c=amp*math.cos(math.tau*(fx*u+fy*v)+phase)
            dx+=fx*c;dy+=fy*c
        n=Vector((-dx,dy,1)).normalized()
        pixels.extend((n.x*.5+.5,n.y*.5+.5,n.z*.5+.5,1))
normal=bpy.data.images.new('T_LakeNormal',width=size,height=size,alpha=False)
normal.colorspace_settings.name='Non-Color';normal.pixels.foreach_set(pixels)
normal.filepath_raw=str(OUT/'T_LakeNormal.png');normal.file_format='PNG';normal.save()
(OUT/'lake-normal-metadata.json').write_text(json.dumps({'file':'T_LakeNormal.png','width':size,'height':size,
    'source':'Original periodic ripple normal texture authored mathematically in create_environment_v8.py',
    'license':'Project-created; no external image','color_space':'Non-Color (sRGB disabled)',
    'compression':'TC_Normalmap','normal_convention':'DirectX tangent-space (green -Y relative to OpenGL)',
    'tiling':'Seamless periodic U and V; wrap sampler','runtime_path':'/Game/PathOfDawn/Environment/T_LakeNormal',
    'temporary':False,'sha256':hashlib.sha256((OUT/'T_LakeNormal.png').read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf-8')

# Original tileable ground textures: periodic noise with small grains and pebbles.
size=1024;rng=np.random.default_rng(5081108)
freq=np.fft.fftfreq(size);fx,fy=np.meshgrid(freq,freq);radius=np.sqrt(fx*fx+fy*fy)
def periodic_noise(scale):
    base=np.fft.fft2(rng.standard_normal((size,size)))
    smooth=np.fft.ifft2(base*np.exp(-(radius*scale)**2)).real
    return smooth/(smooth.std()+1e-10)
broad=periodic_noise(84);medium=periodic_noise(14);fine=periodic_noise(2.2)
pebbles=np.zeros((size,size),dtype=np.float64)
for _ in range(1250):
    px=int(rng.integers(0,size));py=int(rng.integers(0,size));r=float(rng.uniform(1.0,3.5))
    for yy in range(-4,5):
        for xx in range(-4,5):
            d=(xx/r)**2+(yy/(r*.67))**2
            if d<1:pebbles[(py+yy)%size,(px+xx)%size]+=float(rng.uniform(.45,.8))*(1-d)**.5
variation=.016*broad+.014*medium+.012*fine+.038*pebbles
base=np.array([.58,.519,.415])[None,None,:]
rgb=np.clip(base+variation[:,:,None]*np.array([1,.92,.76]),0,1)
height=.00012*medium+.000055*fine+.00072*pebbles
dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*size*.5
dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*size*.5
norm=np.stack((-dx,dy,np.ones_like(dx)),axis=2);norm/=np.linalg.norm(norm,axis=2)[:,:,None]
normal_rgb=norm*.5+.5
textures=[]
for name,pixels,color_space in [('T_ShoreAlbedo',rgb,'sRGB'),('T_ShoreNormal',normal_rgb,'Non-Color')]:
    im=bpy.data.images.new(name,width=size,height=size,alpha=False)
    # PNG values are authored in the declared display/normal space; no baked lighting.
    im.colorspace_settings.name='Non-Color'
    rgba=np.concatenate((pixels,np.ones((size,size,1))),axis=2).astype(np.float32)
    im.pixels.foreach_set(rgba.reshape(-1));im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save()
    textures.append({'file':name+'.png','width':size,'height':size,'runtime_path':'/Game/PathOfDawn/Environment/'+name,
        'source':'Original periodic Fourier-filtered micrograin/pebble texture, create_environment_v8.py',
        'license':'Project-created; no external imagery','color_space':color_space,'sRGB':color_space=='sRGB',
        'normal_convention':'DirectX tangent space' if color_space=='Non-Color' else None,
        'uv':'SM_ShoreGround UV0 uses x=46m/y=29m; multiply UV by (46,29) for 1m repeats',
        'lighting_baked':False,'temporary':False,'sha256':hashlib.sha256((OUT/(name+'.png')).read_bytes()).hexdigest()})
(OUT/'shore-texture-metadata.json').write_text(json.dumps(textures,indent=2)+'\n',encoding='utf-8')

# Reimport all exported files into a separate scene and verify actual FBX payloads.
source_scene=bpy.context.scene
validation_scene=bpy.data.scenes.new('FBX roundtrip validation')
bpy.context.window.scene=validation_scene
checks=[]
for row in manifest:
    name=row['asset_id'];before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_anim=False)
    imported=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in imported if o.type=='MESH']
    assert len(meshes)==1,(name,'expected one mesh',len(meshes))
    o=meshes[0]
    assert len(o.data.polygons)>0 and len(o.data.materials)>0,name
    assert all(abs(float(o.dimensions[i])-row['dimensions_m'][i])<.003 for i in range(3)),(name,list(o.dimensions))
    assert all(math.isfinite(component) for v in o.data.vertices for component in v.co),name
    assert all(len(p.vertices)==3 for p in o.data.polygons),name
    checks.append({'asset_id':name,'single_mesh':True,'roundtrip_dimensions_m':[round(float(v),4) for v in o.dimensions],
                   'triangles':len(o.data.polygons),'material_slots':len(o.data.materials),'finite_coordinates':True,
                   'UV0':bool(o.data.uv_layers),'passed':True})
    if name=='SM_ShoreGround':assert len(o.data.uv_layers)==1,'Ground UV0 missing in FBX'
    for obj in imported:bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.window.scene=source_scene
bpy.data.scenes.remove(validation_scene)
(OUT/'environment-validation.json').write_text(json.dumps({'tool':'Blender '+bpy.app.version_string,'test':'FBX roundtrip import; not Unreal validation','passed':len(checks),'assets':checks},indent=2)+'\n',encoding='utf-8')

if A.render:
    locations={'SM_Boat':(-1.6,-.8,0),'SM_Net':(-.15,-2.25,0),'SM_NetPrepared':(-2.7,2.1,0),
               'SM_Jar':(2.25,1.7,0),'SM_StoneWall':(1.9,4,0),'SM_Canopy':(-3,3.6,0),
               'SM_ShoreRock':(3.4,-1.7,0),'SM_OliveTree':(4.4,3.3,0),'SM_ReedClump':(4.2,7.7,0),
               'SM_PathSlab':(1.5,-2.2,0),'SM_ShoreGround':(0,0,-.015),'SM_DistantRidge':(0,85,-.2)}
    for o in models:
        o.hide_render=False;o.hide_set(False);o.location=locations[o.name]
    # Preview the same source textures through the ground UVs used by Unreal.
    ground_material=mat('ShorePreviewOnly',(.5,.44,.33))
    nodes=ground_material.node_tree.nodes;links=ground_material.node_tree.links
    uv=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(46,29,1)
    links.new(uv.outputs['UV'],mapping.inputs[0])
    albedo=nodes.new('ShaderNodeTexImage');albedo.image=bpy.data.images.load(str(OUT/'T_ShoreAlbedo.png'));albedo.image.colorspace_settings.name='sRGB'
    normal_tex=nodes.new('ShaderNodeTexImage');normal_tex.image=bpy.data.images.load(str(OUT/'T_ShoreNormal.png'));normal_tex.image.colorspace_settings.name='Non-Color'
    links.new(mapping.outputs[0],albedo.inputs['Vector']);links.new(mapping.outputs[0],normal_tex.inputs['Vector'])
    links.new(albedo.outputs['Color'],nodes['Principled BSDF'].inputs['Base Color'])
    normal_node=nodes.new('ShaderNodeNormalMap');normal_node.inputs['Strength'].default_value=.65
    links.new(normal_tex.outputs['Color'],normal_node.inputs['Color']);links.new(normal_node.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
    ground_object=next(o for o in models if o.name=='SM_ShoreGround')
    for slot in ground_object.material_slots:slot.material=ground_material
    for name,positions in {
        'SM_Jar':[(2.7,1.9,0),(-3.6,3.5,0)],
        'SM_ShoreRock':[(-3.9,-1.5,-.08),(4.2,7.3,-.07),(5.1,8.1,-.1),(-4,9,-.05)],
        'SM_ReedClump':[(3.6,8.1,0),(4.8,8.4,0),(-4,9.2,0),(-4.5,8.9,0)],
        'SM_PathSlab':[(1.8,-1.4,0),(2.1,-.6,0),(2.3,.2,0),(2.5,1,0)],
    }.items():
        original=next(o for o in models if o.name==name)
        for k,pos in enumerate(positions):
            o=original.copy();o.data=original.data;bpy.context.collection.objects.link(o)
            o.location=pos;o.rotation_euler.z=.27*(k+1);o.scale=(.86+.1*(k%3),)*3
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,60,-.21));lake=bpy.context.object
    lake.name='Preview only lake';lake.data.materials.append(M['LakePreview'])
    # Preview uses simple physically based lighting. No post-painted details.
    bpy.ops.object.light_add(type='AREA',location=(-7,-4,10));light=bpy.context.object
    light.data.energy=1350;light.data.shape='DISK';light.data.size=7;light.data.color=(1,.80,.54)
    bpy.ops.object.light_add(type='SUN',location=(-5,3,9));sun=bpy.context.object
    sun.rotation_euler=(math.radians(22),math.radians(-25),math.radians(-35));sun.data.energy=2.2;sun.data.angle=.12;sun.data.color=(1,.79,.54)
    bpy.ops.object.camera_add(location=(10.3,-13.2,7.2));cam=bpy.context.object
    cam.rotation_euler=(Vector((0,1.8,1.15))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=44;cam.data.clip_end=400;bpy.context.scene.camera=cam
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=40
    # Debian headless builds may omit OpenImageDenoise; plain Cycles works on CPU.
    scene.cycles.use_denoising=False;scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.43,.52,.60,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
    scene.render.filepath=str(OUT/'EnvironmentPreview.png');bpy.ops.render.render(write_still=True)
print('POD_ENV_COMPLETE',len(models),str(OUT),flush=True)
