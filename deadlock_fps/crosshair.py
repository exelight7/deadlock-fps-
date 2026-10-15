"""Native modern Deadlock reticles: validated models, sharing, scoped transactions."""
from dataclasses import dataclass,asdict,replace
from pathlib import Path
import base64,json,math,re,uuid,zlib
from . import kv3
from .core import atomic,digest,ensure_closed,equivalent,game_root,video_files

# UI values correspond to actual crosshair_* properties in citadel_hero_settings.lst.
NUMBERS={
 'width':('crosshair_pip_width',0,32), 'length':('crosshair_pip_height',0,128),
 'gap':('crosshair_pip_gap',-64,128), 'opacity':('crosshair_pip_opacity',0,1),
 'border':('crosshair_pip_outline_border',0,16), 'border_gap':('crosshair_pip_outline_gap',0,32),
 'border_opacity':('crosshair_pip_outline_opacity',0,1), 'dot':('crosshair_dot_size',0,64),
 'dot_opacity':('crosshair_dot_opacity',0,1), 'dot_border':('crosshair_dot_outline_border',0,16),
 'dot_border_gap':('crosshair_dot_outline_gap',0,32), 'dot_border_opacity':('crosshair_dot_outline_opacity',0,1),
}
BOOLEANS={'static':'crosshair_pip_gap_static','collapse':'crosshair_pip_gap_collapse','themed':'crosshair_themed'}
# These dimensions are int32 fields in the native CustomCrosshairSettings_t.
PIXELS=('width','length','border','border_gap','dot','dot_border','dot_border_gap')

@dataclass(frozen=True)
class Crosshair:
    width:float=4
    length:float=16
    gap:float=4
    opacity:float=.5
    border:float=1
    border_gap:float=0
    border_opacity:float=.7
    dot:float=4
    dot_opacity:float=.7
    dot_border:float=2
    dot_border_gap:float=0
    dot_border_opacity:float=.7
    static:bool=False
    collapse:bool=False
    themed:bool=False
    color:str='#ffffff'
    outline:str='#000000'
    def validate(self):
        for key,(_,lo,hi) in NUMBERS.items():
            v=getattr(self,key)
            if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid value: '+key)
        for key in BOOLEANS:
            if type(getattr(self,key)) is not bool:raise ValueError('Invalid option: '+key)
        for key in ('color','outline'):
            if not isinstance(getattr(self,key),str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',getattr(self,key)):raise ValueError('Invalid color.')
        return self
    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or set(data)-cls.__dataclass_fields__.keys():raise ValueError('Invalid design or unsupported fields.')
        return cls(**data).validate()
    def native(self):
        design=self.normalized();result={native:format(getattr(design,k),'.6g') for k,(native,_,_) in NUMBERS.items()}
        result.update({native:str(getattr(self,k)).lower() for k,native in BOOLEANS.items()})
        for key,prefix in [('color','crosshair_color_'),('outline','crosshair_outline_color_')]:
            rgb=getattr(self,key)[1:]
            for i,component in enumerate('rgb'):result[prefix+component]=str(int(rgb[i*2:i*2+2],16))
        return result
    def normalized(self):
        self.validate();return replace(self,**{k:math.floor(getattr(self,k)+.5) for k in PIXELS})
    @classmethod
    def from_native(cls,values):
        values={k:v for k,v in values.items() if k.startswith('crosshair_')};default=cls();data={}
        for key,(native,_,_) in NUMBERS.items():
            if native in values:data[key]=float(values[native])
        for key,native in BOOLEANS.items():
            if native in values:
                v=str(values[native]).lower()
                if v not in ('true','false','0','1'):raise ValueError('Unknown crosshair option: '+native)
                data[key]=v in ('true','1')
        for key,prefix in [('color','crosshair_color_'),('outline','crosshair_outline_color_')]:
            rgb=[]
            for i,c in enumerate('rgb'):
                v=float(values.get(prefix+c,int(getattr(default,key)[1+i*2:3+i*2],16)))
                if not v.is_integer() or not 0<=v<=255:raise ValueError('Color is out of range.')
                rgb.append(int(v))
            data[key]='#'+''.join(f'{v:02x}' for v in rgb)
        return cls.from_dict(data)

PRESETS={
 'صليب صغير':Crosshair(width=2,length=6,gap=3,opacity=1,border=1,border_opacity=.8,dot=0,dot_opacity=0,dot_border_opacity=0,static=True,color='#aaff78'),
 'نقطة خضراء':Crosshair(width=0,length=0,opacity=0,border_opacity=0,dot=4,dot_opacity=1,dot_border=1,dot_border_opacity=.8,static=True,color='#aaff78'),
 'صليب سماوي':Crosshair(width=2,length=9,gap=4,opacity=1,border_opacity=1,dot=2,dot_opacity=1,dot_border=0,dot_border_opacity=0,static=True,color='#73e8ff'),
 'دائرة':Crosshair(width=0,length=0,opacity=0,border_opacity=0,dot=8,dot_opacity=0,dot_border=1,dot_border_opacity=1,static=True,outline='#aaff78'),
 'صليب كلاسيكي':Crosshair(),
}

def export_design(design):return {'format':'deadlock-toolbox-crosshair','version':1,'design':asdict(design.validate())}
def import_design(data):
    if not isinstance(data,dict) or set(data)!={'format','version','design'} or data['format']!='deadlock-toolbox-crosshair' or type(data['version']) is not int or data['version']!=1:raise ValueError('Unsupported design file.')
    return Crosshair.from_dict(data['design'])
def share_code(design):
    raw=json.dumps(export_design(design),sort_keys=True,separators=(',',':')).encode()
    return 'DLTB1.'+base64.urlsafe_b64encode(zlib.compress(raw,9)).decode().rstrip('=')
def read_code(code):
    code=code.strip()
    if len(code)>4096 or not re.fullmatch(r'DLTB1\.[A-Za-z0-9_-]+',code):raise ValueError('Paste a Toolbox code starting with DLTB1. Native DL codes are not supported here.')
    try:
        value=code[6:];packed=base64.b64decode(value+'='*(-len(value)%4),altchars=b'-_',validate=True)
        decoder=zlib.decompressobj();raw=decoder.decompress(packed,8193)
        if len(raw)>8192 or not decoder.eof or decoder.unused_data:raise ValueError('Code is too large or damaged.')
        return import_design(json.loads(raw))
    except (ValueError,zlib.error,UnicodeDecodeError,TypeError) as error:
        raise ValueError('Invalid design code. Copy the complete code from Toolbox.') from error

@dataclass
class Change:
    path:Path
    before:bytes
    after:bytes
    scopes:tuple
@dataclass
class Plan:
    changes:list
    restoring:bool=False

class CrosshairStore:
    def __init__(self,root,video=None):
        self.root=game_root(root);self.video=Path(video).resolve() if video else None
        if self.video and self.video not in video_files(self.root):raise ValueError('Choose a Steam account in Overview.')
        self.folder=self.root/'.deadlock-fps-studio/crosshair';self.latest=self.folder/'latest.json'
    def paths(self):
        paths=[self.root/'game/citadel/cfg/citadel_hero_settings.lst']
        if self.video and self.video.parent.parent.name=='local':paths.append(self.video.parent.parent.parent/'remote/cfg/citadel_hero_settings.lst')
        for p in paths:
            if p.is_symlink():raise ValueError('Symbolic links to hero settings are not supported.')
        return tuple(dict.fromkeys(paths))
    @staticmethod
    def read(path):
        with path.open('rb') as f:raw=f.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('The hero settings file is too large.')
        text=raw.decode('utf-8');kv3.section(text,['base']);return raw,text
    def current(self):
        found=[p for p in self.paths() if p.is_file()]
        if not found:raise ValueError('Change your crosshair once inside Deadlock, close the game, then click Read from Game.')
        # Prefer the explicitly selected Steam account's cloud source.
        path=found[-1];_,text=self.read(path)
        return Crosshair.from_native(kv3.fields(text,['base'])),tuple(found)
    def plan(self,design,all_heroes=False):
        values=design.native();_,paths=self.current();changes=[]
        for p in paths:
            before,text=self.read(p);scopes=[('base',)]
            if all_heroes:
                heroes=kv3.section(text,['heroes'])
                for n in heroes.children:
                    if n.kind!='object':raise ValueError('Invalid hero settings.')
                    scopes.append(('heroes',n.key))
            output=text
            for scope in scopes:
                existing=kv3.fields(output,scope)
                patch={k:v for k,v in values.items() if not equivalent(existing.get(k),v)}
                output=kv3.update(output,scope,patch)
            after=output.encode('utf-8')
            if after!=before:changes.append(Change(p,before,after,tuple(scopes)))
        return Plan(changes)
    def can_restore(self):
        if not self.latest.exists():return False
        data=json.loads(self.latest.read_text());return bool(data.get('snapshot'))
    def restore_plan(self):
        if not self.can_restore():raise ValueError('No crosshair change is available to restore for this folder.')
        name=json.loads(self.latest.read_text())['snapshot']
        if not isinstance(name,str) or not re.fullmatch('[0-9a-f]{32}',name):raise ValueError('Invalid backup record.')
        folder=self.folder/name
        if folder.is_symlink():raise ValueError('Invalid backup path.')
        manifest=json.loads((folder/'manifest.json').read_text());allowed=set(self.paths());changes=[];seen=set()
        if manifest.get('schema')!=1 or not isinstance(manifest.get('records'),list):raise ValueError('Invalid backup.')
        for i,record in enumerate(manifest['records']):
            p=Path(record['path'])
            if p not in allowed or p in seen:raise ValueError('This backup belongs to a different folder or account. Select the previous account first.')
            seen.add(p)
            old=(folder/f'{i}.before').read_bytes();applied=(folder/f'{i}.after').read_bytes()
            if digest(old)!=record['before_hash'] or digest(applied)!=record['after_hash']:raise ValueError('The backup is damaged.')
            current,text=self.read(p);output=text;scopes=[]
            for scope in record['scopes']:
                if scope!=['base'] and not (len(scope)==2 and scope[0]=='heroes' and re.fullmatch('[A-Za-z0-9_.-]+',scope[1])):raise ValueError('Invalid restore scope.')
                before_fields=kv3.fields(old.decode('utf-8'),scope);after_fields=kv3.fields(applied.decode('utf-8'),scope)
                patch={k:before_fields.get(k) for k in after_fields if k in Crosshair().native() and not equivalent(before_fields.get(k),after_fields.get(k))}
                output=kv3.update(output,scope,patch);scopes.append(tuple(scope))
            after=old if current==applied else output.encode('utf-8')
            if after!=current:changes.append(Change(p,current,after,tuple(scopes)))
        return Plan(changes,restoring=True)
    def apply(self,plan):
        ensure_closed();allowed=set(self.paths())
        if self.folder.resolve().is_relative_to(self.root) is False:raise ValueError('Invalid backup folder.')
        for change in plan.changes:
            if change.path not in allowed or change.path.is_symlink():raise ValueError('Invalid settings path.')
            if change.path.read_bytes()!=change.before:raise ValueError('The file changed during review. Read from Game and try again.')
        if not plan.changes:
            if plan.restoring:atomic(self.latest,b'{"snapshot":null}')
            return 'This crosshair is already applied. No game files changed.'
        folder=self.folder/uuid.uuid4().hex;records=[]
        for i,c in enumerate(plan.changes):
            atomic(folder/f'{i}.before',c.before);atomic(folder/f'{i}.after',c.after)
            records.append({'path':str(c.path),'scopes':c.scopes,'before_hash':digest(c.before),'after_hash':digest(c.after)})
        atomic(folder/'manifest.json',json.dumps({'schema':1,'records':records},indent=2).encode())
        written=[]
        try:
            for c in plan.changes:
                ensure_closed()
                if c.path.read_bytes()!=c.before:raise ValueError('A file changed before writing. Review the changes again.')
                atomic(c.path,c.after);written.append(c)
            atomic(self.latest,json.dumps({'snapshot':None if plan.restoring else folder.name}).encode())
        except Exception:
            for c in reversed(written):atomic(c.path,c.before)
            raise
        return ('The last crosshair change was restored.' if plan.restoring else 'Crosshair saved with a backup. Start Deadlock and test it in training.')
