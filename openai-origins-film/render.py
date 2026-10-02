"""Original deterministic OpenGL motion design. No stock footage or templates."""
import os
os.environ.setdefault('LP_NUM_THREADS','12')
import argparse, json, math, subprocess, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont, ImageDraw
import moderngl

ROOT=Path(__file__).resolve().parent
W,H=1920,1080
STORY=json.loads((ROOT/('timing.json' if (ROOT/'timing.json').exists() else 'story.json')).read_text())
SCENES=STORY['scenes']
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
LATIN='/usr/share/fonts/truetype/lato/Lato-Regular.ttf'
LIGHT='/usr/share/fonts/truetype/lato/Lato-Light.ttf'
WHITE=(239,241,232); MUTED=(150,166,169); GOLD=(244,187,113); CYAN=(133,223,215)

VERT='''#version 330
in vec2 in_pos; out vec2 uv;
void main(){uv=in_pos*.5+.5;gl_Position=vec4(in_pos,0,1);}
'''
PARTICLE_VERT='''#version 330
in vec4 rnd;
uniform float time; uniform float local; uniform float blend;
uniform int scene; uniform int previous;
uniform vec2 resolution;
out vec3 color; out float opacity;
const float PI=3.14159265359;
mat3 rx(float a){float c=cos(a),s=sin(a);return mat3(1,0,0,0,c,s,0,-s,c);}
mat3 ry(float a){float c=cos(a),s=sin(a);return mat3(c,0,-s,0,1,0,s,0,c);}
mat3 rz(float a){float c=cos(a),s=sin(a);return mat3(c,s,0,-s,c,0,0,0,1);}
vec3 shape(int k,vec4 r){
 float a=r.x*2.*PI,b=r.y*2.*PI; vec3 p;
 if(k==0||k==9){
  float R=1.20+.43*cos(3.*a);
  vec3 c=vec3(R*cos(2.*a),R*sin(2.*a),.6*sin(3.*a));
  vec3 tangent=normalize(vec3(-2.*R*sin(2.*a)-1.29*sin(3.*a)*cos(2.*a),2.*R*cos(2.*a)-1.29*sin(3.*a)*sin(2.*a),1.8*cos(3.*a)));
  vec3 n=normalize(cross(tangent,vec3(0,0,1)));vec3 bt=cross(tangent,n);
  p=c+.16*(cos(b)*n+sin(b)*bt)*(.83+.17*r.z);
  p=ry(time*.075)*rx(.35)*p;
  if(k==0)p*=mix(.012,1.,smoothstep(.0,5.8,time));
  if(k==9)p*=.64;
 }else if(k==1){
  float n=floor(r.x*8.);float theta=n/8.*2.*PI;
  vec3 c=vec3(cos(theta)*1.18,sin(theta)*1.18,.35*sin(theta*2.));
  float z=2.*r.z-1.,rad=sqrt(1.-z*z);
  p=c+.26*vec3(rad*cos(b),rad*sin(b),z);
  if(r.w>.56){float aa=fract(r.x*8.)*2.*PI; p=vec3((1.18+.1*sin(b*4.))*cos(aa),(1.18+.1*sin(b*4.))*sin(aa),.32*sin(2.*aa)+.08*cos(b));}
  p=ry(time*.055)*rx(.38)*p;
 }else if(k==2){
  float layer=floor(r.x*9.);float x=fract(r.x*9.)*2.-1.; float y=r.y*2.-1.;
  p=vec3((layer-4.)*.28,x*1.13,y*1.2);
  p.y+=.17*sin(y*3.+layer*.45+time);p.z+=.13*sin(x*3.+time*.8);
  p=rz(-.2)*ry(-.54+sin(time*.12)*.1)*rx(.20)*p;
 }else if(k==3){
  float side=floor(r.x*4.); float a=fract(r.x*4.); float z=(fract(r.z+time*.065)-.5)*8.;
  if(side<1.)p=vec3(-1.3,(r.y-.5)*2.6,z);
  else if(side<2.)p=vec3(1.3,(r.y-.5)*2.6,z);
  else if(side<3.)p=vec3((r.y-.5)*2.6,-1.3,z);
  else p=vec3((r.y-.5)*2.6,1.3,z);
  p.xy+=.02*sin(a*90.+time);
  p=rz(.23)*ry(-.24)*rx(.08)*p;
 }else if(k==4){
  float group=floor(r.x*3.);float aa=fract(r.x*3.)*2.*PI;
  vec3 c=vec3((group-1.)*.95,.45*sin(group*2.1),0);
  p=vec3((.52+.12*cos(b))*cos(aa),(.52+.12*cos(b))*sin(aa),.12*sin(b));
  p=ry(time*.25+group)*rx(group*.7+.4)*p+c;
  p=rz(-.18)*p;
 }else if(k==5){
  float ring=floor(r.z*9.);float rad=.3+ring*.19+fract(time*.19)*.15;
  p=vec3(rad*cos(a),rad*sin(a),.10*sin(a*6.+time)+.02*sin(b));
  p=ry(.55)*rx(.2)*p;
 }else if(k==6){
  float x=(r.x-.5)*3.8;float z=(r.y-.5)*2.1;
  float env=exp(-x*x*.48);float y=sin(x*5.-time*2.4+z*2.)*env*.48+sin(x*10.+time*1.4)*.15*env;
  p=vec3(x,y+(.5-r.z)*.055,z);p=rz(-.2)*rx(.45)*p;
 }else if(k==7){
  float z=2.*r.y-1.; float rad=sqrt(1.-z*z);
  p=vec3(rad*cos(a),z,rad*sin(a))*1.32;
  p.x+=sign(p.x)*(.075+.04*sin(time));
  if(r.w>.8){p*=1.2;p.y*=.09; p=rx(.4)*rz(.25)*p;}
  p=ry(time*.09)*rz(-.2)*p;
 }else{
  float z=2.*r.y-1.,rad=sqrt(1.-z*z);
  p=vec3(rad*cos(a),z,rad*sin(a))*1.48;
  float cells=sin(a*13.+sin(z*10.)*2.)*cos(z*21.+sin(a*5.));
  p*=1.+.008*cells;
  p=rz(-.15)*ry(time*.065)*p;
 }
 return p;
}
void main(){
 vec3 p=mix(shape(previous,rnd),shape(scene,rnd),blend);
 float drift=.018*sin(time*.28+rnd.w*6.);
 p.xy+=drift;
 float depth=5.9-p.z;
 float scale=2.7/depth;
 vec2 center=vec2(.38,.015);
 if(scene==9)center=mix(vec2(.38,.015),vec2(0.,.26),blend);
 if(previous==9)center=vec2(0.,.26);
 vec2 q=vec2(p.x/(resolution.x/resolution.y),p.y)*scale+center;
 gl_Position=vec4(q,0.,1.);
 float blur=abs(p.z-.2)*1.0;
 gl_PointSize=clamp((1.2+rnd.w*1.5+blur)*1080./resolution.y,1.,7.);
 vec3 gold=vec3(1.,.65,.30),mint=vec3(.31,.88,.82),blue=vec3(.39,.52,1.);
 float warm=.5+.5*sin(rnd.x*6.28+time*.10);
 color=mix(mint,gold,warm);
 if(scene==2||scene==3)color=mix(blue,mint,rnd.y);
 if(scene==4||scene==6)color=mix(vec3(.52,.47,.98),mint,rnd.x);
 if(scene==7)color=mix(mint,gold,step(.5,rnd.x));
 if(scene>=8)color=mix(gold,vec3(.89,.95,1.),rnd.y*.7);
 float front=clamp((p.z+2.)/4.,.18,1.);
 opacity=(.22+.78*front)*(.35+.65*rnd.w);
 if(scene==3)opacity*=.65+.35*sin(rnd.z*100.+time*3.);
 if(scene==8){float land=sin(rnd.x*75.+sin(rnd.y*20.)*2.)*cos(rnd.y*55.+sin(rnd.x*32.));opacity*=.32+.68*smoothstep(-.4,.5,land);}
 if(scene==5)opacity*=.30;
 opacity*=mix(.85,1.1,sin(time*.6)*.5+.5);
}
'''
PARTICLE_FRAG='''#version 330
in vec3 color;in float opacity;out vec4 frag;
void main(){float d=length(gl_PointCoord-.5)*2.;if(d>1.)discard;
float core=exp(-d*d*7.);float halo=pow(max(0.,1.-d),1.5)*.18;
frag=vec4(color*(core+halo)*opacity,1.);}
'''
FILAMENT_FRAG='''#version 330
in vec3 color;in float opacity;uniform float gain;out vec4 frag;
void main(){frag=vec4(color*opacity*gain,1.);}
'''
LINE_VERT='''#version 330
in vec3 pos;in vec3 col;uniform float time;uniform vec2 resolution;uniform float alpha;uniform int scene;out vec3 c;
void main(){float a=time*.065;mat3 R=mat3(cos(a),0,-sin(a),0,1,0,sin(a),0,cos(a));
vec3 p=R*pos;float depth=5.9-p.z;vec2 q=vec2(p.x/(resolution.x/resolution.y),p.y)*2.7/depth+vec2(.38,.015);
if(scene==9)q=vec2(p.x/(resolution.x/resolution.y),p.y)*2.7/depth+vec2(0.,.26);
gl_Position=vec4(q,0,1);c=col*alpha*(.4+.6*clamp((p.z+2.)/4.,0.,1.));}
'''
LINE_FRAG='''#version 330
in vec3 c;out vec4 frag;void main(){frag=vec4(c,1);}
'''
BG='''#version 330
in vec2 uv;out vec4 frag;uniform float time;uniform int scene;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
void main(){
 vec2 p=(uv-.5)*vec2(1.7778,1.);
 vec2 c=vec2(.34,.04);if(scene==9)c=vec2(0.,.16);
 float r=length(p-c);
 vec3 base=vec3(.005,.011,.021);
 vec3 hue=vec3(.014,.054,.063);if(scene==3)hue=vec3(.018,.032,.075);if(scene>=8)hue=vec3(.055,.035,.017);
 base+=hue*exp(-r*r*3.8);
 base+=vec3(.016,.015,.013)*exp(-pow(p.y+.22,2.)*110.)*exp(-p.x*p.x*.5);
 vec2 g=floor(uv*vec2(360.,202.));float h=hash(g);
 float star=step(.9965,h)*pow(max(0.,1.-length(fract(uv*vec2(360.,202.))-.5)*2.),3.);
 base+=star*.18*(.6+.4*sin(time*.6+h*80.));
 float flare=exp(-abs(p.y-.013)*360.)*exp(-abs(p.x-.33)*6.);
 base+=flare*vec3(.17,.09,.035)*(.5+.5*sin(time*.2));
 frag=vec4(base,1);
}
'''
BLUR='''#version 330
in vec2 uv;out vec4 frag;uniform sampler2D tex;uniform vec2 direction;
void main(){vec3 c=texture(tex,uv).rgb*.227027;
c+=(texture(tex,uv+direction*1.384615).rgb+texture(tex,uv-direction*1.384615).rgb)*.316216;
c+=(texture(tex,uv+direction*3.230769).rgb+texture(tex,uv-direction*3.230769).rgb)*.070270;
frag=vec4(c,1.);}
'''
POST='''#version 330
in vec2 uv;out vec4 frag;uniform sampler2D base;uniform sampler2D bloom;uniform float time;uniform float flash;
float hash(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
void main(){vec3 c=texture(base,uv).rgb+texture(bloom,uv).rgb*1.65;
c=vec3(1.)-exp(-c*1.12);
c=pow(c,vec3(.86));c*=1.-.27*pow(length((uv-.5)*1.22),2.);
c+=flash*vec3(.06,.11,.12)*exp(-pow(uv.x-.66,2.)*5.);
c+=(hash(uv*2000.+fract(time)*123.)-.5)*.008;
float letter= smoothstep(.066,.074,uv.y)*smoothstep(.066,.074,1.-uv.y);c*=letter;
frag=vec4(c,1.);}
'''
TEXT_VERT='''#version 330
in vec2 in_pos;uniform vec4 rect;uniform vec2 resolution;out vec2 uv;
void main(){uv=in_pos*.5+.5;vec2 p=rect.xy+uv*rect.zw;gl_Position=vec4(p.x/resolution.x*2.-1.,1.-p.y/resolution.y*2.,0,1);}
'''
TEXT_FRAG='''#version 330
in vec2 uv;uniform sampler2D tex;uniform float alpha;out vec4 frag;
void main(){vec4 c=texture(tex,uv);frag=vec4(c.rgb,c.a*alpha);}
'''

def ease(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)

class Renderer:
    def __init__(self):
        self.ctx=moderngl.create_standalone_context(backend='egl')
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.quad=self.ctx.buffer(np.array([-1,-1,1,-1,-1,1,1,1],dtype='f4').tobytes())
        def prog(fragment,vertex=VERT):
            p=self.ctx.program(vertex_shader=vertex,fragment_shader=fragment)
            v=self.ctx.vertex_array(p,[(self.quad,'2f','in_pos')]);return p,v
        self.bg,self.bgva=prog(BG);self.post,self.postva=prog(POST);self.blur,self.blurva=prog(BLUR)
        self.tp,self.tva=prog(TEXT_FRAG,TEXT_VERT);self.tp['resolution']=(W,H)
        self.pp=self.ctx.program(vertex_shader=PARTICLE_VERT,fragment_shader=PARTICLE_FRAG)
        rnd=np.random.default_rng(4271).uniform(0,1,(56000,4)).astype('f4')
        self.pb=self.ctx.buffer(rnd.tobytes());self.pva=self.ctx.vertex_array(self.pp,[(self.pb,'4f','rnd')])
        self.pp['resolution']=(W,H)
        self.fp=self.ctx.program(vertex_shader=PARTICLE_VERT,fragment_shader=FILAMENT_FRAG)
        self.fp['resolution']=(W,H)
        filaments=[]
        for j in range(25):
            u=np.linspace(0,1,550,dtype='f4')
            row=np.column_stack([u,np.full_like(u,(j+.5)/25),np.full_like(u,.53),np.full_like(u,.74)])
            filaments.append(np.stack([row[:-1],row[1:]],axis=1).reshape(-1,4))
        self.fib=self.ctx.buffer(np.concatenate(filaments).astype('f4').tobytes())
        self.fiva=self.ctx.vertex_array(self.fp,[(self.fib,'4f','rnd')])
        self.lp=self.ctx.program(vertex_shader=LINE_VERT,fragment_shader=LINE_FRAG)
        self.lp['resolution']=(W,H)
        self.lines={}
        for k in range(10):
            data=self.make_lines(k)
            if len(data):
                b=self.ctx.buffer(np.asarray(data,dtype='f4').tobytes())
                self.lines[k]=(b,self.ctx.vertex_array(self.lp,[(b,'3f 3f','pos','col')]))
        self.base=self.ctx.texture((W,H),4,dtype='f2');self.fb=self.ctx.framebuffer([self.base])
        self.small=[self.ctx.texture((W//4,H//4),4,dtype='f2') for _ in range(2)]
        self.sfb=[self.ctx.framebuffer([t]) for t in self.small]
        self.out=self.ctx.texture((W,H),3);self.ofb=self.ctx.framebuffer([self.out])
        self.cache={};self.fonts={}
        print('Renderer:',self.ctx.info['GL_RENDERER'],flush=True)

    def make_lines(self,k):
        lines=[]
        def curve(p,color):
            for a,b in zip(p[:-1],p[1:]):lines.extend([list(a)+list(color),list(b)+list(color)])
        a=np.linspace(0,2*np.pi,240)
        if k in (1,7,8,9):
            if k==1:
                pts=[np.array([1.18*np.cos(i*np.pi/4),1.18*np.sin(i*np.pi/4),.35*np.sin(i*np.pi/2)]) for i in range(8)]
                for i in range(8):
                    for j in range(i+1,8):
                        if (j-i)%3==0 or j-i==1:
                            p=np.array([pts[i]*(1-v)+pts[j]*v+np.array([0,0,.3*np.sin(v*np.pi)]) for v in np.linspace(0,1,40)])
                            curve(p,(.19,.48,.45))
            elif k==8:
                for lat in np.linspace(-1.3,1.3,9):
                    curve(np.array([np.cos(a)*np.cos(lat),np.full_like(a,np.sin(lat)),np.sin(a)*np.cos(lat)]).T*1.5,(.26,.23,.16))
                for phi in np.linspace(0,np.pi,10,endpoint=False):
                    curve(np.array([np.cos(a)*np.cos(phi),np.sin(a),np.cos(a)*np.sin(phi)]).T*1.5,(.20,.25,.25))
                for i in range(7):
                    ang=i*.88
                    p=np.array([1.57*np.cos(a),1.57*np.sin(a)*np.sin(ang),1.57*np.sin(a)*np.cos(ang)]).T
                    curve(p[:130],(.45,.31,.15))
            else:
                for i in range(3):
                    r=1.7 if k==7 else 1.23
                    theta=.4+i*.73
                    curve(np.array([r*np.cos(a),r*np.sin(a)*np.cos(theta),r*np.sin(a)*np.sin(theta)]).T,(.23,.35,.34))
        elif k==2:
            for i in range(9):
                x=(i-4)*.28
                p=np.array([[x,-1.12,-1.2],[x,1.12,-1.2],[x,1.12,1.2],[x,-1.12,1.2],[x,-1.12,-1.2]])
                ry=np.array([[.86,0,-.51],[0,1,0],[.51,0,.86]])
                curve(p@ry,(.15,.30,.39))
        return lines

    def text_texture(self,text,size,color=WHITE,bold=False,latin=False):
        latin=latin and not any('\u2e80'<=c<='\uffef' for c in text)
        key=(text,size,color,bold,latin)
        if key not in self.cache:
            fp=(LATIN if bold else LIGHT) if latin else (BOLD if bold else FONT)
            fk=(fp,size)
            if fk not in self.fonts:self.fonts[fk]=ImageFont.truetype(fp,size,index=2 if not latin else 0)
            f=self.fonts[fk];box=f.getbbox(text);width=max(1,box[2]-box[0]+8);height=box[3]-box[1]+8
            im=Image.new('RGBA',(width,height));d=ImageDraw.Draw(im)
            d.text((4-box[0],4-box[1]),text,font=f,fill=(*color,255))
            texture=self.ctx.texture(im.size,4,im.tobytes());texture.filter=(moderngl.LINEAR,moderngl.LINEAR)
            self.cache[key]=(texture,width,height)
        return self.cache[key]

    def text(self,text,x,y,size=30,color=WHITE,alpha=1,bold=False,latin=False,anchor='left'):
        if alpha<.002 or not text:return
        tex,w,h=self.text_texture(text,size,color,bold,latin)
        if anchor=='center':x-=w/2
        if anchor=='right':x-=w
        self.tp['rect']=(x,y,w,h);self.tp['alpha']=alpha;tex.use(0);self.tp['tex']=0;self.tva.render(moderngl.TRIANGLE_STRIP)

    def rect(self,x,y,w,h,color=(255,255,255),alpha=1):
        if 'solid' not in self.cache:
            tx=self.ctx.texture((1,1),4,bytes([255,255,255,255]));self.cache['solid']=tx
        key=('solid',color)
        if key not in self.cache:self.cache[key]=self.ctx.texture((1,1),4,bytes([*color,255]))
        self.cache[key].use(0);self.tp['rect']=(x,y,w,h);self.tp['alpha']=alpha;self.tp['tex']=0;self.tva.render(moderngl.TRIANGLE_STRIP)

    def interface(self,k,l,alpha):
        if k==5:
            # Deliberately composed illustrative dialogue, not a product screenshot.
            x,y,w,h=1090,295,660,426
            self.rect(x,y,w,h,(12,24,31),alpha*.93)
            self.rect(x,y,w,1,CYAN,alpha*.35);self.rect(x,y+h,w,1,CYAN,alpha*.2)
            self.text('ChatGPT',x+35,y+28,32,alpha=alpha,latin=True,bold=True)
            self.text('交互示意',x+w-35,y+37,17,MUTED,alpha,anchor='right')
            self.rect(x+32,y+89,w-64,1,MUTED,alpha*.16)
            self.text('你',x+35,y+121,23,GOLD,alpha)
            prompt='帮我理解一个新的想法。'
            self.text(prompt[:max(0,int((l-1.8)*9))],x+35,y+169,31,WHITE,alpha)
            if l>5:
                a=alpha*ease((l-5)*2)
                self.text('ChatGPT',x+35,y+238,23,CYAN,a,latin=True,bold=True)
                answer='当然。我们从一个简单的例子开始。'
                shown=answer[:max(0,int((l-5.4)*8))]
                self.text(shown[:17],x+35,y+284,28,WHITE,a)
                if len(shown)>17:self.text(shown[17:],x+35,y+325,28,WHITE,a)
            self.rect(x+35,y+h-28,w-70,1,MUTED,alpha*.2)
        if k==6:
            for j,(txt,en) in enumerate([('文字','TEXT'),('图像','VISION'),('声音','AUDIO')]):
                a=alpha*ease((l-.8-j*.8)/1.0)
                self.text(txt,1110+j*225,740,27,WHITE,a,anchor='center')
                self.text(en,1110+j*225,784,15,MUTED,a,latin=True,anchor='center')

    def type_scene(self,k,t,external=1):
        s=SCENES[k];l=t-s['start'];remaining=s['end']-t
        a=ease((l-(1.7 if k==0 else 0))/.8)*ease(remaining/.65)*external
        if a<.002:return
        self.text(s['label'],145,171,21,CYAN,a,latin=True,bold=True)
        self.rect(145,220,54,2,GOLD,a)
        if k!=9:
            if s['year']:self.text(s['year'],141,263,82,GOLD,a,latin=True)
            base=391 if s['year'] else 342
            for j,line in enumerate(s['title']):
                reveal=ease((l-.3-j*.14)/1.0)
                self.text(line,140,base+j*111+(1-reveal)*26,91 if k!=8 else 112,WHITE,a*reveal,bold=True)
            detail_y=base+len(s['title'])*111+41
            self.text(s['detail'],145,detail_y,26,MUTED,a*ease((l-1.0)/.8))
            if k==1:
                self.text('Sam Altman  /  Elon Musk',145,766,21,MUTED,a*ease((l-2)/1),latin=True)
                self.text('Ilya Sutskever  /  Greg Brockman  等',145,802,20,MUTED,a*ease((l-2.4)/1))
            if k==3:self.text('Microsoft · 投资与计算平台合作',145,784,22,MUTED,a*ease((l-2)/1))
            if k==4:
                for j,(tag,tx) in enumerate([('01','语言'),('02','开发'),('03','图像')]):
                    xx=146+j*187;aa=a*ease((l-1.8-j*.3))
                    self.rect(xx,755,142,1,CYAN,aa*.3)
                    self.text(tag,xx,776,16,GOLD,aa,latin=True)
                    self.text(tx,xx+39,771,24,WHITE,aa)
            if k==7:self.text('使命是一项承诺，也是一道持续的考题。',145,696,24,MUTED,a*ease((l-2.1)))
            if k==8:
                for j,txt in enumerate(['创造','学习','发现']):
                    self.text(txt,147+j*159,658,27,GOLD,a*ease((l-1.8-j*.4)))
        else:
            self.text('OpenAI',960,631,99,WHITE,a*ease((l-.6)/1.2),latin=True,bold=True,anchor='center')
            self.text(s['detail'],960,757,29,GOLD,a*ease((l-1.6)/1.3),anchor='center')
            self.text('关键节点 2015—2024  ·  原创概念短片',960,851,19,MUTED,a*ease((l-4)/1.2),anchor='center')
            self.text('历史资料：OpenAI 官方公告与宪章  /  完整出处见随片文档',960,887,17,MUTED,a*ease((l-4)/1.2),anchor='center')
        self.interface(k,l,a*ease((l-.7)/.8))

    def draw(self,t):
        k=next((i for i,s in enumerate(SCENES) if s['start']<=t<s['end']),9)
        s=SCENES[k];l=t-s['start'];blend=ease(l/1.6);prev=max(0,k-1)
        self.ctx.disable(moderngl.BLEND);self.fb.use();self.ctx.viewport=(0,0,W,H)
        self.bg['time']=t;self.bg['scene']=k;self.bgva.render(moderngl.TRIANGLE_STRIP)
        self.ctx.enable(moderngl.BLEND);self.ctx.blend_func=(moderngl.ONE,moderngl.ONE)
        self.pp['time']=t;self.pp['blend']=blend;self.pp['scene']=k;self.pp['previous']=prev
        self.pva.render(moderngl.POINTS)
        self.fp['time']=t;self.fp['blend']=blend;self.fp['scene']=k;self.fp['previous']=prev
        self.fp['gain']=[.33,.1,.07,.06,.23,.018,.22,.075,.075,.35][k]
        self.fiva.render(moderngl.LINES)
        if k in self.lines:
            self.lp['time']=t;self.lp['scene']=k;self.lp['alpha']=blend*.56
            self.lines[k][1].render(moderngl.LINES)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.viewport=(0,0,W//4,H//4)
        self.sfb[0].use();self.base.use(0);self.blur['tex']=0;self.blur['direction']=(1/W,0);self.blurva.render(moderngl.TRIANGLE_STRIP)
        for n in range(3):
            self.sfb[1].use();self.small[0].use(0);self.blur['direction']=(4/W*(1+n),0);self.blurva.render(moderngl.TRIANGLE_STRIP)
            self.sfb[0].use();self.small[1].use(0);self.blur['direction']=(0,4/H*(1+n));self.blurva.render(moderngl.TRIANGLE_STRIP)
        self.ofb.use();self.ctx.viewport=(0,0,W,H);self.base.use(0);self.small[0].use(1)
        self.post['base']=0;self.post['bloom']=1;self.post['time']=t
        self.post['flash']=math.exp(-l*4)*(.22 if k else 0)
        self.postva.render(moderngl.TRIANGLE_STRIP)
        self.ctx.enable(moderngl.BLEND);self.ctx.blend_func=(moderngl.SRC_ALPHA,moderngl.ONE_MINUS_SRC_ALPHA)
        self.type_scene(k,t)
        # Restrained film furniture, chapter rail, and human-readable subtitles.
        global_a=ease(t/1.8)*ease((120-t)/1.8)
        self.text('向所有人',145,102,24,WHITE,global_a,bold=True)
        self.text('A LIGHT FOR EVERYONE',285,108,16,MUTED,global_a,latin=True,bold=True)
        self.text('OpenAI  /  ORIGINS & IDEALS',1775,109,16,MUTED,global_a,latin=True,anchor='right')
        if k!=9:
            yy=884;self.rect(145,yy,1630,1,MUTED,global_a*.18)
            self.rect(145,yy,1630*t/120,1,GOLD,global_a*.8)
            for j,ss in enumerate(SCENES[:-1]):
                xx=145+1630*ss['start']/120
                self.rect(xx,yy-2,4,5,GOLD if j<=k else MUTED,global_a*(.9 if j<=k else .35))
            self.text(f'{k+1:02d} / 10',1775,843,17,MUTED,global_a,latin=True,anchor='right')
        vs=s.get('voice_start',s['start']+1.15);vd=s.get('voice_duration',s['end']-s['start']-2)
        if vs-.1<t<vs+vd+.35:
            caps=s['captions'];weights=[max(1,len(c)) for c in caps];progress=(t-vs)/vd
            acc=0;idx=0
            for j,wt in enumerate(weights):
                acc+=wt/sum(weights)
                if progress<=acc:idx=j;break
                idx=j
            aa=ease((t-vs+.1)/.2)*ease((vs+vd+.35-t)/.3)*global_a
            text=caps[idx];_,tw,th=self.text_texture(text,29)
            self.rect((W-tw)/2-23,937,tw+46,th+18,(3,8,13),aa*.70)
            self.text(text,W/2,945,29,WHITE,aa,anchor='center')
        if t<1.3:self.rect(0,0,W,H,(0,0,0),1-ease(t/1.3))
        if t>118:self.rect(0,0,W,H,(0,0,0),ease((t-118)/2))
        return self.ofb.read(components=3,alignment=1)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stills',action='store_true');parser.add_argument('--start',type=float,default=0);parser.add_argument('--end',type=float,default=120);parser.add_argument('--output',default='picture.mp4');parser.add_argument('--fps',type=int,default=30)
    args=parser.parse_args();r=Renderer()
    if args.stills:
        (ROOT/'stills').mkdir(exist_ok=True)
        for t in [5.7,16.5,28.5,41,53,67,80,92,104,114.5]:
            data=r.draw(t);im=Image.frombytes('RGB',(W,H),data).transpose(Image.Transpose.FLIP_TOP_BOTTOM);im.save(ROOT/'stills'/f'{t:05.1f}.jpg',quality=95)
        print('Stills complete.');return
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(args.fps),'-i','-','-vf','vflip','-an','-c:v','libx264','-preset','fast','-crf','17','-threads','8','-pix_fmt','yuv420p','-movflags','+faststart',str(ROOT/args.output)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE);start=time.time();frames=round((args.end-args.start)*args.fps)
    for frame in range(frames):
        t=args.start+frame/args.fps;p.stdin.write(r.draw(t))
        if frame%150==0:print(f'{frame}/{frames} frames | t={t:.1f}s | {frame/max(.001,time.time()-start):.1f} fps',flush=True)
    p.stdin.close()
    if p.wait():raise RuntimeError('ffmpeg failed')
    print(f'Finished in {time.time()-start:.1f}s',flush=True)

if __name__=='__main__':main()
