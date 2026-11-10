import bpy, math, random, json, sys, os
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.geometry import tessellate_polygon
import numpy as np

ROOT = Path(__file__).resolve().parent / 'generated_assets'
for sub in ['models/glb', 'models/fbx', 'models/lod1', 'textures', 'previews', 'source']:
    (ROOT/sub).mkdir(parents=True, exist_ok=True)
random.seed(741)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

# A shared, portable PBR atlas. No procedural shaders are needed by the GLBs.
PALETTE = {
 'cream':('#fff1d8',.87,'cloth'), 'white':('#fff7f0',.86,'fur'),
 'yellow':('#ffc846',.86,'fur'), 'gold_cloth':('#f3ac2e',.9,'cloth'),
 'ochre':('#d98a2f',.87,'fur'), 'spot':('#da872c',.85,'fur'),
 'pink':('#f58c9c',.9,'cloth'), 'inner_pink':('#ffb1bd',.9,'fur'),
 'blush':('#f6a3a7',.87,'fur'), 'red':('#ee4935',.88,'fur'),
 'red_cloth':('#d94031',.9,'cloth'), 'orange':('#ffae28',.85,'fur'),
 'horn':('#ffeac5',.8,'cloth'), 'mane':('#58454a',.88,'fur'),
 'mane_light':('#665055',.9,'fur'), 'brown_cloth':('#76503e',.9,'cloth'),
 'tan':('#e5a447',.85,'fur'), 'amber':('#e9b368',.87,'fur'),
 'snake_spot':('#9d694d',.86,'fur'), 'green':('#8b9848',.9,'cloth'),
 'leaf':('#78883d',.9,'cloth'), 'charcoal':('#494445',.88,'fur'),
 'charcoal_cloth':('#504b4c',.9,'cloth'), 'blue':('#779eea',.87,'fur'),
 'blue_cloth':('#658bd7',.9,'cloth'), 'wave':('#5c86ce',.89,'cloth'),
 'eye':('#342c30',.23,'smooth'), 'eye_brown':('#57392c',.29,'smooth'),
 'shine':('#ffffff',.24,'smooth'), 'mouth':('#763837',.7,'smooth'),
 'mouth_red':('#943c3d',.72,'smooth'), 'tongue':('#f87e8c',.69,'smooth'),
 'nose_pink':('#ea8998',.57,'smooth'), 'stitch':('#f6d7b4',.92,'cloth'),
 'hem_gold':('#dfa02e',.9,'cloth'), 'hem_pink':('#dd7d8b',.9,'cloth'),
 'hem_red':('#bb352b',.9,'cloth'), 'hem_brown':('#654435',.9,'cloth'),
 'hem_green':('#75813a',.9,'cloth'), 'hem_dark':('#3d383b',.9,'cloth'),
 'hem_blue':('#567ac3',.9,'cloth'), 'mountain':('#75503c',.9,'cloth'),
 'fire':('#ed6323',.88,'cloth'), 'fire_inner':('#ffbf35',.87,'cloth'),
 'gill':('#3d568a',.85,'fur'), 'teeth':('#fff6df',.65,'smooth'),
}
KEYS=list(PALETTE)
TILE=128; GRID=8; SIZE=TILE*GRID
rng=np.random.default_rng(4320)
base=np.ones((SIZE,SIZE,4),np.float32)
normal=np.ones_like(base); normal[:,:,:3]=[.5,.5,1]
orm=np.ones_like(base);orm[:,:,2]=0
for idx,key in enumerate(KEYS):
    hx,rough,kind=PALETTE[key]
    col=np.array([int(hx[j:j+2],16)/255 for j in (1,3,5)])
    y,x=np.mgrid[:TILE,:TILE]
    noise=rng.normal(0,1,(TILE,TILE))
    # Periodic low-frequency nap plus tiny threads, with no painted lighting.
    freqs=np.fft.fftfreq(TILE)
    f=np.sqrt(freqs[:,None]**2+freqs[None,:]**2)
    low=np.fft.ifft2(np.fft.fft2(noise)*np.exp(-f*f*380)).real
    low=low/(low.std()+1e-8)
    weave=np.sin(x*math.pi/2)*np.sin(y*math.pi/2)
    if kind=='smooth':
        mod=np.ones_like(noise); h=np.zeros_like(noise)
    elif kind=='cloth':
        mod=1+noise*.012+low*.013+weave*.008
        h=noise*.045+weave*.13+low*.06
    else:
        fibers=np.sin(x*.85+y*.38+low*.7)
        mod=1+noise*.011+low*.019+fibers*.008
        h=noise*.035+fibers*.12+low*.11
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*1.0
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))*1.0
    nn=np.stack([-dx,-dy,np.ones_like(h)],-1)
    nn=nn/np.linalg.norm(nn,axis=-1,keepdims=True)
    row,cc=divmod(idx,GRID); sl=np.s_[row*TILE:(row+1)*TILE,cc*TILE:(cc+1)*TILE]
    base[sl][:,:,:3]=np.clip(mod[:,:,None]*col,0,1)
    normal[sl][:,:,:3]=nn*.5+.5
    orm[sl][:,:,1]=np.clip(rough+noise*.007,0,1)

def save_tex(name,pixels,colorspace):
    im=bpy.data.images.new(name,width=SIZE,height=SIZE,alpha=True)
    im.colorspace_settings.name=colorspace
    im.pixels.foreach_set(pixels.ravel())
    im.filepath_raw=str(ROOT/'textures'/(name+'.png'));im.file_format='PNG';im.save()
    im.pack()
    return im

base_im=save_tex('plush_basecolor',base,'sRGB')
normal_im=save_tex('plush_normal',normal,'Non-Color')
orm_im=save_tex('plush_orm',orm,'Non-Color')
mat=bpy.data.materials.new('Plush_PBR_Atlas');mat.use_nodes=True
n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled')
bs.inputs['Roughness'].default_value=.85
bs.inputs['Specular IOR Level'].default_value=.28
bs.inputs['Sheen Weight'].default_value=.12
bt=n.new('ShaderNodeTexImage');bt.image=base_im;bt.label='sRGB / base color'
nt=n.new('ShaderNodeTexImage');nt.image=normal_im;nt.label='OpenGL tangent normal'
rt=n.new('ShaderNodeTexImage');rt.image=orm_im;rt.label='R=AO, G=roughness, B=metallic'
nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.48
sp=n.new('ShaderNodeSeparateColor');sp.mode='RGB'
l.new(bt.outputs['Color'],bs.inputs['Base Color']);l.new(nt.outputs['Color'],nm.inputs['Color'])
l.new(nm.outputs['Normal'],bs.inputs['Normal']);l.new(rt.outputs['Color'],sp.inputs[0])
l.new(sp.outputs['Green'],bs.inputs['Roughness']);l.new(bs.outputs[0],out.inputs[0])
bt.location=(-620,220);nt.location=(-620,-80);rt.location=(-620,-380)
nm.location=(-300,-60);sp.location=(-300,-340);bs.location=(0,120);out.location=(320,120)

COL=None; PARTS=[]
def mesh(name,vs,fs,key,uv=None,smooth=True):
    me=bpy.data.meshes.new(name+'_mesh');me.from_pydata(vs,[],fs);me.materials.append(mat);me.update()
    ob=bpy.data.objects.new(name,me);COL.objects.link(ob);PARTS.append(ob)
    for p in me.polygons:p.use_smooth=smooth
    if uv is None:
        xs=[v[0] for v in vs];zs=[v[2] for v in vs]
        ax,bx=min(xs),max(xs);az,bz=min(zs),max(zs)
        uv=[((v[0]-ax)/max(bx-ax,.001),(v[2]-az)/max(bz-az,.001)) for v in vs]
    idx=KEYS.index(key);row,col=divmod(idx,GRID)
    layer=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li in p.loop_indices:
            u,v=uv[me.loops[li].vertex_index]
            layer.data[li].uv=((col+.045+.91*u)/GRID,(row+.045+.91*v)/GRID)
    ob['part']=name;ob['palette_role']=key
    return ob

def pw(v,e):return math.copysign(abs(v)**e,v)
def ell(name,c,s,key,p=2.0,seg=28,rings=18,rot=None):
    e=2/p;vs=[(0,0,s[2])];uv=[(.5,1)]
    for j in range(1,rings):
        a=math.pi*j/rings
        for i in range(seg+1):
            b=2*math.pi*i/seg
            vs.append((s[0]*pw(math.sin(a),e)*pw(math.cos(b),e),s[1]*pw(math.sin(a),e)*pw(math.sin(b),e),s[2]*pw(math.cos(a),e)))
            uv.append((i/seg,1-j/rings))
    end=len(vs);vs.append((0,0,-s[2]));uv.append((.5,0));fs=[]
    for i in range(seg):fs.append((0,1+i,2+i))
    for j in range(rings-2):
        a=1+j*(seg+1)
        for i in range(seg):fs.append((a+i,a+seg+1+i,a+seg+2+i,a+1+i))
    a=1+(rings-2)*(seg+1)
    for i in range(seg):fs.append((a+i,end,a+i+1))
    ob=mesh(name,vs,fs,key,uv);ob.location=c
    if rot:ob.rotation_euler=rot
    return ob

def catmull(points,steps=5,closed=False):
    arr=[Vector(v) for v in points]
    if len(arr)<3:return arr
    out=[]
    count=len(arr) if closed else len(arr)-1
    for i in range(count):
        p0=arr[(i-1)%len(arr)] if closed or i else arr[0]
        p1=arr[i];p2=arr[(i+1)%len(arr)]
        p3=arr[(i+2)%len(arr)] if closed or i+2<len(arr) else arr[-1]
        for j in range(steps):
            t=j/steps
            out.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    if not closed:out.append(arr[-1])
    return out

def tube(name,points,r,key,steps=5,sides=10,taper=None,flat=1.0):
    pts=catmull(points,steps);vs=[];uv=[]
    for j,p in enumerate(pts):
        t=j/(len(pts)-1)
        tang=(pts[min(j+1,len(pts)-1)]-pts[max(j-1,0)]).normalized()
        ref=Vector((0,1,0))
        if abs(tang.dot(ref))>.95:ref=Vector((1,0,0))
        aa=ref.cross(tang).normalized();bb=tang.cross(aa).normalized()
        rad=r*(taper(t) if taper else 1)
        for i in range(sides):
            a=2*math.pi*i/sides
            v=p+rad*(math.cos(a)*aa+math.sin(a)*bb*flat)
            vs.append(tuple(v));uv.append((i/sides,t))
    fs=[]
    for j in range(len(pts)-1):
        for i in range(sides):
            a=j*sides+i;b=j*sides+(i+1)%sides
            fs.append((a,b,b+sides,a+sides))
    fs.append(tuple(reversed(range(sides))))
    fs.append(tuple((len(pts)-1)*sides+i for i in range(sides)))
    return mesh(name,vs,fs,key,uv)

def patch(name,outline,surf,key,smooth_outline=True,thick=.002,sub=1):
    pts=catmull(outline,4,closed=True) if smooth_outline else [Vector(p) for p in outline]
    xy=[(float(v[0]),float(v[1])) for v in pts]
    vec=[Vector((x,z,0)) for x,z in xy]
    inds={tuple(round(t,8) for t in v):i for i,v in enumerate(vec)}
    faces=[]
    for tri in tessellate_polygon([vec]):
        fs=tuple(v if isinstance(v,int) else inds[tuple(round(t,8) for t in v)] for v in tri)
        a,b,c=[xy[i] for i in fs]
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:fs=tuple(reversed(fs))
        faces.append(fs)
    # Split interior triangles so the applique follows curved plush surfaces.
    for _ in range(sub):
        cache={};nf=[]
        def mid(a,b):
            k=tuple(sorted((a,b)))
            if k not in cache:
                cache[k]=len(xy);xy.append(((xy[a][0]+xy[b][0])/2,(xy[a][1]+xy[b][1])/2))
            return cache[k]
        for a,b,c in faces:
            ab,bc,ca=mid(a,b),mid(b,c),mid(c,a)
            nf.extend([(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)])
        faces=nf
    vs=[(x,surf(x,z),z) for x,z in xy]
    # Closed thin applique rather than a coplanar, double-sided decal.
    nv=len(vs);vs.extend([(x,y+thick,z) for x,y,z in vs]);nf=faces.copy()
    nf.extend([tuple(nv+i for i in reversed(f)) for f in faces])
    for i in range(len(pts)):
        j=(i+1)%len(pts);nf.append((i,nv+i,nv+j,j))
    return mesh(name,vs,nf,key,smooth=True)

def oval_pts(cx,cz,rx,rz,n=32,angle=0,jitter=0):
    out=[]
    for i in range(n):
        a=2*math.pi*i/n;rr=1+jitter*(.4*math.sin(a*3+1)+.6*math.sin(a*5+.4))
        x=rx*math.cos(a)*rr;z=rz*math.sin(a)*rr
        out.append((cx+x*math.cos(angle)+z*math.sin(angle),cz-x*math.sin(angle)+z*math.cos(angle)))
    return out

def surface(c,s,p=2.5,offset=0):
    def fn(x,z):
        rem=max(.002,1-abs((x-c[0])/s[0])**p-abs((z-c[2])/s[2])**p)
        return c[1]-s[1]*rem**(1/p)-offset
    return fn

def line2(name,xzs,surf,r,key):return tube(name,[(x,surf(x,z),z) for x,z in xzs],r,key,steps=4,sides=8)

def eye(name,x,z,surf,scale=1,brown=True):
    y=surf(x,z)
    ell(name+'_sclera',(x,y-.005,z),(.061*scale,.017,.078*scale),'teeth',seg=24,rings=14)
    ell(name+'_iris',(x+.005,y-.019,z-.001),(.047*scale,.014,.065*scale),'eye_brown' if brown else 'eye',seg=24,rings=14)
    ell(name+'_pupil',(x+.006,y-.031,z),(.033*scale,.005,.050*scale),'eye',seg=20,rings=12)
    ell(name+'_glint',(x+.018*scale,y-.037,z+.034*scale),(.016*scale,.006,.019*scale),'shine',seg=16,rings=10)
    ell(name+'_tiny_glint',(x-.011*scale,y-.036,z-.031*scale),(.006*scale,.004,.007*scale),'shine',seg=12,rings=8)

def happy_eye(name,x,z,surf,scale=1):
    pts=[(x+(.5-t)*.12*scale,z+.052*scale*math.sin(math.pi*t)) for t in np.linspace(0,1,9)]
    line2(name,pts,lambda a,b:surf(a,b)-.013,.013*scale,'eye')
    for xx,zz in [pts[0],pts[-1]]:ell(name+'_end',(xx,surf(xx,zz)-.013,zz),(.010*scale,.009,.010*scale),'eye',seg=12,rings=8)

def mouth(name,cx,top,w,h,surf,key='mouth',tongue=True):
    z=top
    pts=[(cx-w,z+.012),(cx-w*.55,z-.013),(cx,z-.025),(cx+w*.55,z-.013),(cx+w,z+.012),
         (cx+w*.90,z-h*.47),(cx+w*.52,z-h*.92),(cx,z-h),(cx-w*.52,z-h*.92),(cx-w*.90,z-h*.47)]
    patch(name+'_cavity',pts,lambda x,z:surf(x,z)-.008,key,sub=2)
    if tongue:
        zz=top-h*.78;yy=surf(cx,zz)-.021
        ell(name+'_tongue',(cx,yy,zz),(w*.48,.014,h*.27),'tongue',seg=24,rings=14)
        line2(name+'_tongue_seam',[(cx,zz+h*.12),(cx,zz-h*.08)],lambda x,z:yy-.014,.0016,'nose_pink')
    return pts

def nose(name,x,z,surf,key='eye',size=.065):
    pts=[(x-size,z+.022),(x-size*.6,z+.046),(x+size*.6,z+.046),(x+size,z+.021),(x+size*.4,z-.018),(x,z-.036),(x-size*.4,z-.018)]
    patch(name,pts,lambda a,b:surf(a,b)-.016,key,thick=.012,sub=1)

torso_profile=[(.318,.20,.135),(.331,.267,.175),(.355,.285,.19),(.39,.286,.192),(.46,.277,.189),(.54,.262,.181),(.62,.246,.168),(.70,.229,.155),(.758,.219,.148),(.788,.183,.12),(.80,.12,.09)]
def body_dims(z):
    for i in range(len(torso_profile)-1):
        z0,x0,y0=torso_profile[i];z1,x1,y1=torso_profile[i+1]
        if z0<=z<=z1:
            t=(z-z0)/(z1-z0);return (x0+(x1-x0)*t,y0+(y1-y0)*t)
    return (.20,.14)
def body_front(x,z):
    rx,ry=body_dims(z)
    return -ry*max(.001,1-abs(x/rx)**2.7)**(1/2.7)-.005

def torso():
    vs=[];uv=[];fs=[];n=48
    for j,(z,rx,ry) in enumerate(torso_profile):
        for i in range(n+1):
            a=2*math.pi*i/n;vs.append((rx*pw(math.cos(a),2/2.7),ry*pw(math.sin(a),2/2.7),z));uv.append((i/n,j/(len(torso_profile)-1)))
    for j in range(len(torso_profile)-1):
        for i in range(n):
            a=j*(n+1)+i;fs.append((a,a+1,a+n+2,a+n+1))
    fs.append(tuple(reversed(range(n))));fs.append(tuple((len(torso_profile)-1)*(n+1)+i for i in range(n)))
    return vs,fs,uv

def outfit(color,hem,paw='cream'):
    vs,fs,uv=torso();mesh('Torso_Hoodie',vs,fs,color,uv)
    panel=[(-.175,.744),(-.215,.673),(-.245,.56),(-.267,.426),(-.256,.362),(-.15,.347),(0,.343),(.15,.347),(.256,.362),(.267,.426),(.245,.56),(.215,.673),(.175,.744),(0,.757)]
    patch('Torso_Cream_Panel',panel,lambda x,z:body_front(x,z)-.002,'cream',sub=2)
    # Rounded limbs and sewn cuffs; feet stay at Z=0.
    for sign,side in [(-1,'L'),(1,'R')]:
        ell('Leg_'+side,(sign*.153,.015,.218),(.121,.132,.186),color,p=3.5,seg=24,rings=16,rot=(0,sign*-.065,0))
        ell('Foot_'+side,(sign*.16,-.04,.070),(.133,.169,.070),paw,p=2.8,seg=28,rings=16)
        ell('Trouser_Cuff_'+side,(sign*.157,.006,.112),(.125,.134,.029),hem,p=3.1,seg=24,rings=10)
        sleeve=ell('Sleeve_'+side,(sign*.302,-.001,.592),(.117,.139,.204),color,p=2.5,seg=24,rings=16,rot=(0,sign*-.52,0))
        ell('Wrist_Cuff_'+side,(sign*.377,-.026,.468),(.105,.126,.032),hem,p=2.6,seg=24,rings=10,rot=(0,sign*-.52,0))
        ell('Paw_'+side,(sign*.399,-.040,.421),(.083,.095,.092),paw,p=2.4,seg=24,rings=14,rot=(0,sign*-.25,0))
        ell('Thumb_'+side,(sign*.358,-.105,.414),(.035,.035,.052),paw,seg=16,rings=12,rot=(0,sign*-.25,0))
        # A restrained trouser seam; close to the surface, not black linework.
        pts=[(sign*.23,-.088,.32),(sign*.243,-.094,.24),(sign*.245,-.098,.15)]
        tube('Trouser_Seam_'+side,pts,.0018,hem,sides=6,steps=3)
    ell('Hood_Back',(0,.068,.785),(.253,.17,.119),color,p=2.7,seg=32,rings=16)
    tube('Hood_Fold',[(-.232,-.065,.803),(-.17,-.155,.806),(0,-.165,.776),(.17,-.155,.806),(.232,-.065,.803)],.031,color,sides=12,steps=6)
    for sign,side in [(-1,'L'),(1,'R')]:
        x=sign*.088
        ell('Drawcord_Eyelet_'+side,(x,-.164,.755),(.019,.010,.022),'stitch',seg=16,rings=10)
        tube('Drawcord_'+side,[(x,-.175,.759),(x-sign*.006,-.197,.711),(x+sign*.003,-.209,.657)],.009,'cream',steps=6,sides=10)
        ell('Drawcord_Aglet_'+side,(x+sign*.003,-.209,.646),(.012,.012,.021),'stitch',p=2.5,seg=16,rings=10)
    # Hem topstitch is sampled on the actual curved garment.
    for sign in [-1,1]:
        pts=[]
        for x in np.linspace(0,.23,16):
            xx=sign*x;zz=.365+.006*(x/.23)**2;pts.append((xx,body_front(xx,zz)-.004,zz))
        tube('Hem_Topstitch',pts,.0017,'stitch',steps=1,sides=6)

def badge(kind):
    surf=lambda x,z:body_front(x,z)-.008
    if kind=='star':
        pts=[]
        for i in range(10):
            a=math.pi/2+2*math.pi*i/10;r=.093 if i%2==0 else .047
            pts.append((math.cos(a)*r,.52+math.sin(a)*r))
        patch('Badge_Star',pts,surf,'gold_cloth',False,sub=1)
    elif kind=='heart':
        pts=[]
        for t in np.linspace(0,2*math.pi,64,endpoint=False):
            pts.append((16*math.sin(t)**3*.0051,.535+(13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t))*.0051))
        patch('Badge_Heart',pts,surf,'pink',False,sub=1)
    elif kind=='fire':
        pts=[(-.075,.468),(-.079,.526),(-.045,.583),(-.038,.548),(-.003,.619),(.018,.66),(.029,.589),(.06,.615),(.079,.552),(.084,.505),(.062,.46),(.015,.444),(-.035,.446)]
        patch('Badge_Fire',pts,surf,'fire',True,sub=1)
        patch('Badge_Fire_Core',[(-.035,.475),(-.038,.506),(-.011,.554),(.0,.522),(.024,.565),(.037,.523),(.036,.487),(.017,.459),(-.014,.46)],lambda x,z:surf(x,z)-.002,'fire_inner',True)
    elif kind=='mountain':
        patch('Badge_Mountains',[(-.119,.453),(-.052,.595),(-.024,.564),(.018,.641),(.113,.454)],surf,'mountain',False,sub=2)
        patch('Badge_Snow',[(-.025,.565),(.018,.632),(.059,.55),(.024,.572),(.012,.553),(.001,.58)],lambda x,z:surf(x,z)-.002,'cream',False)
        patch('Badge_Snow_Small',[(-.077,.54),(-.052,.587),(-.028,.545),(-.051,.56)],lambda x,z:surf(x,z)-.002,'cream',False)
    elif kind=='leaf':
        pts=[(-.069,.468),(-.083,.513),(-.061,.575),(-.003,.605),(.076,.615),(.076,.554),(.041,.498),(-.011,.479)]
        patch('Badge_Leaf',pts,surf,'leaf',True,sub=2)
        line2('Badge_Leaf_Vein',[(-.078,.448),(-.021,.518),(.05,.586)],lambda x,z:surf(x,z)-.003,.0036,'cream')
    elif kind=='bamboo':
        patch('Badge_Bamboo_Stem',[(-.083,.46),(-.049,.447),(.062,.62),(.031,.638)],surf,'leaf',False,sub=1)
        for i,(x,z,sgn) in enumerate([(-.038,.514,-1),(.005,.574,1),(.035,.605,1),(-.005,.582,-1)]):
            pts=[(x,z),(x+sgn*.04,z+.005),(x+sgn*.073,z+.035),(x+sgn*.038,z+.052)]
            patch('Badge_Bamboo_Leaf_'+str(i),pts,lambda x,z:surf(x,z)-.002,'leaf',True)
        for z in [.495,.545,.597]:
            x=(z-.46)*.64-.068
            line2('Badge_Bamboo_Node',[(x-.01,z+.007),(x+.016,z-.009)],lambda x,z:surf(x,z)-.004,.0021,'cream')
    elif kind=='wave':
        pts=[(-.13,.46),(-.089,.499),(-.061,.562),(-.018,.603),(.03,.608),(.071,.579),(.046,.556),(.019,.566),(-.001,.548),(.005,.513),(.049,.486),(.093,.497),(.117,.517),(.106,.469),(.069,.45),(.0,.456),(-.06,.447)]
        patch('Badge_Wave',pts,surf,'wave',True,sub=1)

def giraffe():
    outfit('gold_cloth','hem_gold');badge('star')
    c=(0,0,1.173);s=(.397,.298,.371);head=surface(c,s,2.65)
    ell('Head',c,s,'yellow',p=2.65,seg=48,rings=30)
    for sign in [-1,1]:
        ell('Ear',(sign*.38,.013,1.47),(.141,.059,.092),'yellow',p=2.3,rot=(0,sign*.40,0))
        ell('Ear_Inner',(sign*.386,-.044,1.477),(.102,.014,.061),'inner_pink',rot=(0,sign*.40,0))
        tube('Ossicone',[(sign*.13,.004,1.49),(sign*.146,.006,1.641),(sign*.15,.005,1.723)],.039,'ochre',steps=5,sides=12,taper=lambda t:1-.18*t)
        ell('Ossicone_Pom',(sign*.15,.004,1.75),(.084,.079,.085),'ochre',seg=28,rings=18)
    for i,(x,z,rx,rz,a) in enumerate([(-.108,1.52,.071,.035,-.4),(.085,1.469,.057,.059,.4),(-.317,1.331,.038,.078,-.2),(-.326,1.115,.041,.077,.1),(-.281,.958,.038,.069,.2),(.31,1.326,.035,.062,-.2),(.329,1.11,.035,.068,0),(.282,.942,.031,.051,.2)]):
        patch('Head_Spot_'+str(i),oval_pts(x,z,rx,rz,22,a,.13),lambda x,z:head(x,z)-.002,'spot',False,sub=1)
    for i,(x,z,rx,rz) in enumerate([(-.20,1.36,.06,.08),(.13,1.37,.065,.057),(-.06,1.14,.064,.075),(.26,1.13,.043,.07),(-.25,.99,.038,.056),(.10,.95,.053,.038)]):
        patch('Back_Head_Spot_'+str(i),oval_pts(x,z,rx,rz,24,0,.16),lambda x,z:-head(x,z)+.003,'spot',False,sub=1)
    for sign in [-1,1]:
        eye('Eye',sign*.158,1.221,head,.96)
        line2('Eyebrow',[(sign*.223,1.393),(sign*.186,1.407),(sign*.152,1.394)],lambda x,z:head(x,z)-.012,.010,'ochre')
        patch('Blush',oval_pts(sign*.265,1.107,.047,.034),lambda x,z:head(x,z)-.004,'blush',False)
    mc=(0,-.264,1.017);ms=(.248,.098,.195);mu=surface(mc,ms,2.5)
    ell('Muzzle',mc,ms,'cream',p=2.5,seg=40,rings=24)
    mouth('Smile',0,1.067,.103,.163,mu)
    for sign in [-1,1]:
        patch('Nostril',oval_pts(sign*.067,1.157,.012,.017,20,sign*.6),lambda x,z:mu(x,z)-.004,'ochre',False)
    tube('Tail',[(0,.14,.36),(.12,.24,.26),(.25,.26,.22),(.30,.24,.26)],.022,'yellow',sides=10)
    ell('Tail_Tuft',(.30,.24,.27),(.041,.043,.064),'ochre',rot=(0,.4,0),seg=20,rings=14)

def rabbit():
    outfit('pink','hem_pink');badge('heart')
    for sign in [-1,1]:
        rot=(0,sign*.17,0)
        ell('Ear',(sign*.155,.025,1.533),(.128,.071,.347),'white',p=2.3,seg=36,rings=24,rot=rot)
        ell('Ear_Inner',(sign*.165,-.039,1.553),(.083,.017,.272),'inner_pink',p=2.3,seg=32,rings=22,rot=rot)
    c=(0,-.004,1.083);s=(.397,.28,.303);head=surface(c,s,2.65)
    ell('Head',c,s,'white',p=2.65,seg=48,rings=30)
    for sign in [-1,1]:
        # Small overlapping cheek scallops soften the silhouette without hair particles.
        for j in range(4):
            z=.925+j*.046;x=sign*(.328+.017*math.sin(j*.8))
            ell('Cheek_Fluff',(x,-.04,z),(.055,.16,.065),'white',seg=20,rings=12,rot=(0,sign*.4,0))
        happy_eye('Closed_Eye',sign*.157,1.12,head)
        patch('Blush',oval_pts(sign*.257,1.029,.049,.033),lambda x,z:head(x,z)-.004,'blush',False)
    mouth('Smile',0,1.009,.072,.132,head,'mouth_red')
    for sign in [-1,1]:ell('Muzzle',(sign*.050,head(0,1.047)-.005,1.041),(.075,.035,.052),'white',seg=24,rings=16)
    nose('Nose',0,1.077,lambda x,z:head(x,z)-.030,'nose_pink',.035)
    line2('Philtrum',[(0,1.056),(0,1.022)],lambda x,z:head(x,z)-.040,.0044,'nose_pink')
    ell('Tail_Pom',(0,.20,.372),(.112,.109,.108),'white',seg=28,rings=18)

def dragon():
    outfit('red_cloth','hem_red');badge('fire')
    for sign in [-1,1]:
        for i,z in enumerate([1.30,1.16,1.02]):
            pts=[(sign*.32,z+.08),(sign*(.43+.02*(i==1)),z+.012),(sign*.35,z-.09)]
            patch('Cheek_Fin',pts,lambda x,z:.038,'orange',True,thick=.09,sub=1)
        ear=[(sign*.24,1.40),(sign*.405,1.50),(sign*.36,1.36),(sign*.30,1.31)]
        patch('Ear',ear,lambda x,z:-.014,'orange',True,thick=.08)
        patch('Ear_Inner',[(sign*.29,1.407),(sign*.374,1.468),(sign*.345,1.374)],lambda x,z:-.018,'red',True,thick=.008)
        tube('Antler_Main',[(sign*.17,.015,1.43),(sign*.207,.018,1.57),(sign*.234,.016,1.68),(sign*.224,.02,1.765)],.043,'horn',sides=12,steps=5,taper=lambda t:1-.55*t)
        tube('Antler_Outer_Branch',[(sign*.211,.018,1.607),(sign*.286,.015,1.66),(sign*.30,.015,1.705)],.029,'horn',sides=10,steps=5,taper=lambda t:1-.65*t)
        tube('Antler_Inner_Branch',[(sign*.204,.018,1.59),(sign*.154,.014,1.649),(sign*.148,.013,1.691)],.027,'horn',sides=10,steps=5,taper=lambda t:1-.65*t)
        ell('Antler_Base',(sign*.184,-.003,1.478),(.062,.053,.060),'yellow',seg=24,rings=14,rot=(0,sign*.2,0))
    for x,z,ss in [(-.073,1.465,.078),(0,1.49,.122),(.075,1.465,.075)]:
        ell('Crown_Spike',(x,.028,z),(.045,.045,ss),'orange',seg=24,rings=16,rot=(0,x*2.8,0))
    c=(0,0,1.131);s=(.377,.293,.327);head=surface(c,s,2.6)
    ell('Head',c,s,'red',p=2.6,seg=48,rings=30)
    for sign in [-1,1]:
        eye('Eye',sign*.151,1.206,head,.96)
        line2('Determined_Brow',[(sign*.227,1.333),(sign*.175,1.317),(sign*.112,1.285)],lambda x,z:head(x,z)-.015,.013,'charcoal')
        patch('Blush',oval_pts(sign*.257,1.084,.044,.031),lambda x,z:head(x,z)-.005,'blush',False)
        patch('Forehead_Scale',oval_pts(sign*.111,1.405,.028,.014,20,sign*.5),lambda x,z:head(x,z)-.003,'orange',False)
    mc=(0,-.257,.993);ms=(.257,.115,.185);mu=surface(mc,ms,2.6)
    ell('Muzzle',mc,ms,'cream',p=2.6,seg=40,rings=24)
    mouth('Smile',0,1.057,.137,.161,mu,'mouth_red')
    for sign in [-1,1]:
        # Soft triangular upper fangs and smaller lower fangs.
        patch('Upper_Fang',[(sign*.105,1.043),(sign*.066,1.041),(sign*.080,.998)],lambda x,z:mu(x,z)-.016,'teeth',True,thick=.007)
        patch('Lower_Fang',[(sign*.093,.929),(sign*.059,.924),(sign*.077,.950)],lambda x,z:mu(x,z)-.018,'teeth',True,thick=.005)
        patch('Nostril',oval_pts(sign*.068,1.122,.017,.011,20,sign*.2),lambda x,z:mu(x,z)-.006,'red_cloth',False)
        tube('Golden_Whisker',[(sign*.158,-.351,1.09),(sign*.255,-.347,1.043),(sign*.355,-.31,1.057),(sign*.409,-.27,1.132),(sign*.425,-.26,1.117)],.021,'yellow',steps=7,sides=12,taper=lambda t:.9+.18*math.sin(math.pi*t)-.40*t)
    tube('Tail',[(0,.15,.35),(.13,.27,.32),(.30,.34,.40),(.38,.35,.56)],.065,'red',steps=6,sides=14,taper=lambda t:1-.85*t)
    for i in range(4):
        t=i/4;ell('Tail_Scale',(.16+t*.22,.31,.36+t*.19),(.033,.035,.045),'orange',seg=16,rings=10,rot=(0,.6,0))

def lion():
    outfit('brown_cloth','hem_brown','tan');badge('mountain')
    ell('Mane_Core',(0,.015,1.14),(.45,.28,.412),'mane',p=2.35,seg=40,rings=28)
    for layer in range(2):
        count=18 if layer==0 else 14
        for i in range(count):
            a=2*math.pi*(i+.25*layer)/count
            x=(.374 if layer==0 else .324)*math.cos(a)
            z=1.14+(.325 if layer==0 else .302)*math.sin(a)
            yy=.005 if layer==0 else -.111
            # Long radial locks overlap like a sewn, sculpted mane.
            rot=(0,math.pi/2-a+.15*math.sin(i*1.7),0)
            ell('Mane_Lock_%d_%02d'%(layer,i),(x,yy,z),(.085 if layer==0 else .073,.119,.148 if layer==0 else .116),'mane_light' if (i+layer)%5==0 else 'mane',p=2.1,seg=20,rings=14,rot=rot)
    c=(0,-.11,1.16);s=(.323,.228,.288);head=surface(c,s,2.65)
    ell('Face',c,s,'mane',p=2.65,seg=40,rings=26)
    for sign in [-1,1]:
        ell('Ear',(sign*.28,.022,1.43),(.086,.059,.081),'mane',seg=24,rings=16)
        happy_eye('Closed_Eye',sign*.137,1.22,head,.9)
        ell('Golden_Brow',(sign*.118,head(sign*.118,1.347)-.012,1.347),(.054,.022,.043),'tan',seg=24,rings=16,rot=(0,sign*.35,0))
    mc=(0,-.292,.997);ms=(.256,.095,.187);mu=surface(mc,ms,2.65)
    ell('Chin',mc,ms,'tan',p=2.65,seg=40,rings=24)
    mouth('Smile',0,1.067,.100,.171,mu,'mouth')
    for sign in [-1,1]:
        ell('Muzzle_Lobe',(sign*.09,-.351,1.09),(.111,.054,.088),'tan',p=2.2,seg=28,rings=18)
    nose('Nose',0,1.145,lambda x,z:-.394,'eye',.068)
    tube('Nose_To_Mouth',[(0,-.416,1.109),(0,-.412,1.062)],.0055,'eye_brown',steps=3,sides=8)
    tube('Tail',[(0,.15,.36),(.14,.24,.27),(.27,.25,.31),(.31,.25,.40)],.023,'tan',steps=5,sides=10)
    ell('Tail_Tuft',(.31,.25,.415),(.057,.054,.078),'mane',seg=24,rings=14)

def snake():
    outfit('green','hem_green');badge('leaf')
    c=(0,0,1.066);s=(.392,.283,.285);head=surface(c,s,2.75)
    ell('Head',c,s,'amber',p=2.75,seg=48,rings=30)
    specs=[(-.12,1.317,.061,.041,.4),(.013,1.276,.09,.06,-.3),(.19,1.31,.063,.043,.2),(-.30,1.21,.041,.059,.3),(.315,1.19,.038,.068,-.2),(-.341,1.03,.027,.046,.2),(.32,1.005,.035,.053,0)]
    for i,(x,z,rx,rz,a) in enumerate(specs):
        patch('Head_Pattern_'+str(i),oval_pts(x,z,rx,rz,26,a,.19),lambda x,z:head(x,z)-.003,'snake_spot',False,sub=1)
    for i,(x,z,rx,rz) in enumerate([(-.17,1.22,.073,.05),(.13,1.20,.085,.069),(-.07,.99,.073,.067),(.26,1.02,.035,.058)]):
        patch('Back_Head_Pattern_'+str(i),oval_pts(x,z,rx,rz,26,0,.21),lambda x,z:-head(x,z)+.003,'snake_spot',False,sub=1)
    eye('Open_Eye',-.165,1.108,head,.97)
    happy_eye('Wink',.164,1.091,head,.95)
    mc=(0,-.249,.942);ms=(.288,.108,.148);mu=surface(mc,ms,2.8)
    ell('Muzzle',mc,ms,'cream',p=2.8,seg=40,rings=24)
    mouth('Smile',0,.982,.123,.117,mu,'mouth_red',tongue=False)
    for sign in [-1,1]:
        patch('Nostril',oval_pts(sign*.066,1.026,.012,.018,20,sign*.6),lambda x,z:mu(x,z)-.006,'snake_spot',False)
    tube('Tongue_Stem',[(0,-.367,.928),(0,-.383,.866),(-.002,-.390,.813)],.021,'tongue',steps=6,sides=12,flat=.43)
    for sign in [-1,1]:
        tube('Tongue_Fork',[(0,-.389,.835),(sign*.018,-.395,.789),(sign*.037,-.393,.765)],.015,'tongue',steps=6,sides=10,flat=.40,taper=lambda t:1-.68*t)
    tube('Tail',[(0,.16,.38),(.13,.26,.30),(.28,.26,.31),(.33,.24,.40),(.27,.21,.45)],.060,'amber',steps=6,sides=14,taper=lambda t:1-.85*t)

def panda():
    outfit('charcoal_cloth','hem_dark');badge('bamboo')
    for sign in [-1,1]:
        ell('Ear',(sign*.279,.008,1.428),(.12,.073,.122),'charcoal',seg=32,rings=20,rot=(0,sign*.2,0))
        ell('Ear_Inner',(sign*.281,-.057,1.43),(.075,.017,.077),'mane',seg=24,rings=16)
    c=(0,0,1.112);s=(.401,.288,.324);head=surface(c,s,2.7)
    ell('Head',c,s,'white',p=2.7,seg=48,rings=30)
    for sign in [-1,1]:
        patch('Eye_Patch',oval_pts(sign*.168,1.174,.093,.132,36,sign*-.28),lambda x,z:head(x,z)-.004,'charcoal',False,sub=2)
        eye('Eye',sign*.157,1.183,lambda x,z:head(x,z)-.006,.81,brown=False)
        patch('Blush',oval_pts(sign*.258,1.013,.044,.031),lambda x,z:head(x,z)-.004,'blush',False)
    mouth('Smile',0,1.006,.079,.129,head,'mouth_red')
    for sign in [-1,1]:ell('Muzzle_Lobe',(sign*.048,head(0,1.055)-.008,1.051),(.073,.034,.056),'white',seg=24,rings=16)
    nose('Nose',0,1.079,lambda x,z:head(x,z)-.031,'eye',.042)
    line2('Philtrum',[(0,1.05),(0,1.012)],lambda x,z:head(x,z)-.042,.004,'eye')
    ell('Tail',(0,.208,.365),(.081,.079,.075),'white',seg=24,rings=16)

def shark():
    outfit('blue_cloth','hem_blue');badge('wave')
    # A thick, swept-back dorsal fin: an actual volume, visible from every angle.
    finpts=[(.025,1.43),(.052,1.65),(.133,1.737),(.203,1.75),(.211,1.685),(.166,1.494)]
    patch('Dorsal_Fin',finpts,lambda x,z:.005,'blue',True,thick=.122,sub=2)
    c=(0,0,1.132);s=(.418,.302,.323);head=surface(c,s,2.75)
    ell('Head',c,s,'blue',p=2.75,seg=48,rings=30)
    mc=(0,-.247,.987);ms=(.357,.112,.192);mu=surface(mc,ms,2.8)
    ell('Jaw',mc,ms,'cream',p=2.8,seg=44,rings=26)
    for sign in [-1,1]:
        eye('Eye',sign*.191,1.242,head,.83,brown=False)
        line2('Determined_Brow',[(sign*.263,1.329),(sign*.207,1.301),(sign*.139,1.281)],lambda x,z:head(x,z)-.015,.012,'gill')
    mouth('Grin',0,1.099,.241,.213,mu,'mouth_red')
    for i,x in enumerate([-.179,-.108,-.036,.036,.108,.179]):
        zz=1.085+.012*abs(x)/.18
        patch('Upper_Tooth_'+str(i),[(x-.031,zz),(x+.031,zz),(x,zz-.056)],lambda x,z:mu(x,z)-.018,'teeth',True,thick=.006)
    for i,x in enumerate([-.157,-.078,0,.078,.157]):
        zz=.908+.044*(abs(x)/.18)**1.8
        patch('Lower_Tooth_'+str(i),[(x-.030,zz),(x,zz+.047),(x+.030,zz)],lambda x,z:mu(x,z)-.020,'teeth',True,thick=.006)
    for sign in [-1,1]:
        patch('Nostril',oval_pts(sign*.067,1.166,.008,.006,16),lambda x,z:head(x,z)-.006,'gill',False)
        for i in range(3):
            x=sign*(.324+i*.024);z=1.15-i*.009
            pts=[(x-sign*.004,z+.055),(x+sign*.015,z+.014),(x+sign*.013,z-.035)]
            line2('Gill',pts,lambda x,z:head(x,z)-.006,.0055,'gill')
    tube('Tail_Stem',[(0,.16,.38),(0,.32,.39),(0,.45,.46)],.055,'blue',steps=6,sides=12,taper=lambda t:1-.30*t)
    for sign in [-1,1]:
        patch('Tail_Fin',[(0,.42),(sign*.20,.60),(sign*.15,.40),(sign*.05,.35)],lambda x,z:.435,'blue',True,thick=.065,sub=1)

BUILDERS=[('01_giraffe','长颈鹿',giraffe),('02_rabbit','兔子',rabbit),('03_dragon','中国龙',dragon),('04_lion','狮子',lion),('05_snake','蛇',snake),('06_panda','熊猫',panda),('07_shark','鲨鱼',shark)]
CHARACTERS=[];stats=[]
for i,(slug,cn,fn) in enumerate(BUILDERS):
    print('BUILDING',slug,flush=True)
    COL=bpy.data.collections.new(slug);scene.collection.children.link(COL);PARTS=[];fn()
    # Slightly wider heads match the reference's broad chibi silhouettes.
    garment_prefixes=('Torso','Leg_','Foot_','Trouser','Sleeve','Wrist','Paw_','Thumb_','Hood_','Drawcord','Hem_','Badge_','Tail')
    if slug!='04_lion':
        for ob in PARTS:
            if ob.name.startswith(garment_prefixes):continue
            m=ob.matrix_world.copy();inv=m.inverted()
            for v in ob.data.vertices:
                w=m@v.co;w.x*=1.06;v.co=inv@w
    # Group components at a foot-level pivot; preserve all editable construction parts.
    root=bpy.data.objects.new(slug+'_ROOT',None);COL.objects.link(root)
    for ob in PARTS:ob.parent=root
    root['character']=cn;root['static_asset']=True;root['front']='Blender -Y / glTF +Z';root['units']='metres'
    CHARACTERS.append((slug,root,list(PARTS),COL))

def tri_count(ob):
    ob.data.calc_loop_triangles();return len(ob.data.loop_triangles)

def export_character(slug,parts):
    bpy.ops.object.select_all(action='DESELECT')
    copies=[]
    for ob in parts:
        new=ob.copy();new.data=ob.data.copy();scene.collection.objects.link(new)
        new.parent=None;new.matrix_world=ob.matrix_world.copy()
        new.select_set(True);copies.append(new)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join();game=bpy.context.object;game.name=slug
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # Keep a consistent origin on the floor between the feet.
    scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    # Remove duplicate pole vertices and any zero-area construction triangles.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=.000001);bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    initial=tri_count(game)
    if initial>30000:
        mod=game.modifiers.new('Game mesh reduction','DECIMATE');mod.ratio=30000/initial;mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    game.data.validate(verbose=True);game.data.update()
    maintris=tri_count(game)
    game['asset_type']='Static textured character';game['rigged']=False
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'models/glb'/(slug+'.glb')),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_materials='EXPORT')
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'models/fbx'/(slug+'.fbx')),use_selection=True,object_types={'MESH'},use_mesh_modifiers=True,mesh_smooth_type='FACE',axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False,path_mode='RELATIVE',embed_textures=False,add_leaf_bones=False)
    dims=list(game.dimensions)
    mod=game.modifiers.new('LOD1 mesh reduction','DECIMATE');mod.ratio=min(1,11000/maintris);mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name);game.data.validate(verbose=True);game.data.update();game.name=slug+'_LOD1';lodtris=tri_count(game)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'models/lod1'/(slug+'_lod1.glb')),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    bpy.data.objects.remove(game,do_unlink=True)
    return {'id':slug,'triangles':maintris,'lod1_triangles':lodtris,'dimensions_blender_xyz_m':dims,'materials':1,'rigged':False,'animations':0,'source_triangles':initial}

for slug,root,parts,col in CHARACTERS:
    print('EXPORTING',slug,flush=True)
    bpy.context.view_layer.update();st=export_character(slug,parts);stats.append(st);print('STATS',json.dumps(st),flush=True)

# A simple studio in the source file. Cameras and lights are excluded from all exports.
COL=bpy.data.collections.new('STUDIO');scene.collection.children.link(COL);PARTS=[]
for i,(slug,root,parts,col) in enumerate(CHARACTERS):root.location.x=(i-3)*1.16
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001));floor=bpy.context.object;floor.name='Studio_Floor'
fm=bpy.data.materials.new('Studio_Warm_White');fm.diffuse_color=(.73,.67,.66,1);fm.use_nodes=True
fm.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.73,.67,.66,1)
fm.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.85;floor.data.materials.append(fm)
world=bpy.data.worlds.new('Warm_Studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.62,.65,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.world=world
def area(name,loc,power,color,size,target):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
area('Large_Softbox',(-3,-5,6),1050,(1,.89,.80),5,(0,0,1))
area('Cool_Fill',(4,-3,3.8),750,(.84,.90,1),4,(0,0,1))
area('Top_Rim',(1,3,5.5),1100,(1,.90,.86),4,(0,0,1))
camd=bpy.data.cameras.new('Lineup_Camera');cam=bpy.data.objects.new('Lineup_Camera',camd);scene.collection.objects.link(cam)
cam.location=(0,-15,3.15);target=Vector((0,0,.90));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=8.35;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=False
scene.render.resolution_x=2040;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-1.1
scene.render.image_settings.file_format='PNG'
scene['asset_note']='Locally modeled from the supplied front-view lineup. Static, stylized reconstruction; rear details are inferred. GLB/FBX exports use only portable texture-backed PBR materials.'
(ROOT/'asset_manifest.json').write_text(json.dumps({'characters':stats,'texture_atlas_size':SIZE,'model_units':'metres','gltf_up':'+Y','gltf_front':'+Z','origin':'floor midpoint between feet','rigged':False,'animations':False,'method':'local Blender procedural modeling from supplied reference; no cloud generation'},ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source'/'Animal_Companions.blend'))
if '--skip-render' not in sys.argv:
    scene.render.filepath=str(ROOT/'previews'/'lineup_source.png');bpy.ops.render.render(write_still=True)
print('BUILD_COMPLETE',flush=True)
