"""Preview-first file operations with immutable originals and transactional rollback."""
from pathlib import Path
import hashlib, json, os, re, shutil, struct, tempfile
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import psutil
from . import kv
from .settings import values, MODS

ASSETS=Path(__file__).resolve().parent.parent/'assets'

def digest(b): return hashlib.sha256(b).hexdigest()
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.fps-')
    try:
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def game_root(path):
    if not str(path).strip():raise ValueError('اربط اللعبة أولًا: اختر مجلد Deadlock من صفحة ابدأ هنا.')
    p=Path(path).expanduser().resolve()
    for candidate in [p,p.parent,p.parent.parent]:
        if (candidate/'game/citadel/gameinfo.gi').is_file():return candidate
    if not (p/'game/citadel/gameinfo.gi').is_file(): raise ValueError('اختر مجلد Deadlock الذي يحتوي game/citadel/gameinfo.gi')
    return p

def steam_roots():
    home=Path.home(); roots=[home/'.local/share/Steam',home/'.steam/steam',home/'.var/app/com.valvesoftware.Steam/.local/share/Steam']
    if os.name=='nt':
        import winreg
        for hive,key in [(winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam'),(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Valve\Steam')]:
            try:
                with winreg.OpenKey(hive,key) as k:
                    for value in ['SteamPath','InstallPath']:
                        try: roots.append(Path(winreg.QueryValueEx(k,value)[0]))
                        except OSError: pass
            except OSError: pass
        roots += [Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Steam',Path('C:/Steam')]
    return list(dict.fromkeys(p.resolve() for p in roots if p.exists()))

def detect_games():
    libraries=[]
    for root in steam_roots():
        libraries.append(root)
        f=root/'steamapps/libraryfolders.vdf'
        if f.exists():
            for p in re.findall(r'"path"\s*"([^"]+)"',f.read_text(errors='replace')):
                libraries.append(Path(p.replace('\\\\','\\')))
    return list(dict.fromkeys(p/'steamapps/common/Deadlock' for p in libraries if (p/'steamapps/common/Deadlock/game/citadel/gameinfo.gi').exists()))

def video_files(root):
    roots=steam_roots()
    # Also support Steam libraries on another drive, while userdata stays in the main Steam folder.
    if root.parent.name=='common' and root.parent.parent.name=='steamapps': roots.append(root.parent.parent.parent)
    result=[]
    for p in roots:
        for f in (p/'userdata').glob('*/1422450/local/cfg/video.txt'):
            result.append(f.resolve())
    local=root/'game/citadel/cfg/video.txt'
    if local.exists(): result.append(local.resolve())
    return sorted(set(result))

def ensure_closed():
    for p in psutil.process_iter(['name']):
        if (p.info['name'] or '').lower() in {'deadlock','deadlock.exe','citadel','citadel.exe','project8','project8.exe'}:
            raise ValueError('أغلق Deadlock قبل التطبيق أو الاسترجاع.')

def vpk_entries(path):
    b=path if isinstance(path,bytes) else path.read_bytes()
    if len(b)<12: raise ValueError('VPK header truncated')
    magic,version,size=struct.unpack_from('<III',b)
    if magic!=0x55AA1234 or version not in (1,2): raise ValueError('Invalid VPK header')
    offset=12 if version==1 else 28
    end=offset+size
    if end>len(b): raise ValueError('VPK tree truncated')
    pos=offset; entries=[]
    def string():
        nonlocal pos
        stop=b.find(b'\0',pos,end)
        if stop<0: raise ValueError('Invalid VPK tree string')
        s=b[pos:stop].decode('utf-8'); pos=stop+1; return s
    while True:
        ext=string()
        if not ext: break
        while True:
            directory=string()
            if not directory: break
            while True:
                name=string()
                if not name: break
                if pos+18>end: raise ValueError('VPK entry truncated')
                crc,preload,archive,start,length,terminator=struct.unpack_from('<IHHIIH',b,pos); pos+=18
                if terminator!=0xffff or archive!=0x7fff or pos+preload>end or end+start+length>len(b):
                    raise ValueError('VPK requires external files or has invalid offsets')
                pos+=preload
                entries.append(f'{directory}/{name}.{ext}')
    return entries


# Resolution, render scale and upscaler identity belong exclusively to the player.
RESOLUTION_KEYS = frozenset({
    'setting.defaultres', 'setting.defaultresheight', 'setting.recommendedheight',
    'setting.mat_viewportscale', 'setting.r_citadel_upscaling',
    'setting.r_citadel_dlss_settings_mode', 'setting.r_dlss_preset',
    'setting.r_citadel_fsr_rcas_sharpness', 'setting.r_citadel_fsr2_sharpness',
    'setting.refreshrate_numerator', 'setting.refreshrate_denominator',
    'setting.aspectratiomode', 'setting.fullscreen', 'setting.nowindowborder',
    'setting.monitor_index', 'setting.high_dpi',
})

def keep_resolution(base, current):
    """Keep current protected values even when upgrading from a 1.0.0 backup."""
    old=base.decode('utf-8-sig');live=current.decode('utf-8-sig')
    before=[n for n in kv.section(old,['video.cfg']).children if n.key in RESOLUTION_KEYS]
    after=[n for n in kv.section(live,['video.cfg']).children if n.key in RESOLUTION_KEYS]
    if [(n.key,n.value) for n in before]==[(n.key,n.value) for n in after]:return base
    for n in reversed(before):old=old[:n.start]+old[n.end:]
    node=kv.section(old,['video.cfg'])
    entries=''.join('\n\t'+live[n.start:n.end] for n in after)
    return (old[:node.close]+entries+'\n'+old[node.close:]).encode()

def equivalent(a,b):
    if a is None or b is None:return a==b
    a=str(a).lower();b=str(b).lower()
    a={'true':'1','false':'0'}.get(a,a);b={'true':'1','false':'0'}.get(b,b)
    try:return Decimal(a)==Decimal(b)
    except InvalidOperation:return a==b

def flat(text,path):return {n.key:n.value for n in kv.section(text,path).children if n.value is not None}
def remove_keys(text,path,keys):
    nodes=kv.section(text,path).children
    for n in reversed(nodes):
        if n.key in keys and n.value is not None:text=text[:n.start]+text[n.end:]
    return text

def scopes_for(path):
    if path.name=='video.txt':return [['video.cfg']]
    if path.name=='gameinfo.gi':return [['GameInfo','ConVars'],['GameInfo','SceneSystem']]
    return []

LEGACY_VIDEO_KEYS={'setting.r_texture_stream_mip_bias','setting.r_citadel_shadow_quality',
 'setting.r_citadel_fog_quality','setting.r_citadel_ssao_quality','setting.r_effects_bloom',
 'setting.r_post_bloom','setting.r_depth_of_field','setting.r_citadel_motion_blur',
 'setting.mat_vsync','setting.r_low_latency','setting.r_particle_max_detail_level',
 'setting.useadvanced','setting.fps_max'}

def footprint(original,expected,path):
    result=[]
    for scope in scopes_for(path):
        before=flat(original,scope);after=flat(expected,scope)
        keys=[k for k,v in after.items() if k not in RESOLUTION_KEYS and not equivalent(before.get(k),v)]
        result.append((scope,keys))
    return result

def clean_base(original,current,owned):
    # Retain the newest unrelated game fields while undoing only our recorded keys.
    for scope,keys in owned:
        previous=flat(original,scope)
        current=remove_keys(current,scope,[k for k in keys if k not in previous])
        current=kv.update(current,scope,{k:previous[k] for k in keys if k in previous})
    if any(n.key.lower()=='gameinfo' for n in kv.parse(original)):
        paths=kv.section(original,['GameInfo','FileSystem','SearchPaths']).children
        if not any(n.key.lower()=='game' and n.value=='citadel/fps_studio' for n in paths):
            for n in reversed(kv.section(current,['GameInfo','FileSystem','SearchPaths']).children):
                if n.key.lower()=='game' and n.value=='citadel/fps_studio':current=current[:n.start]+current[n.end:]
    return current

class Studio:
    def __init__(self,root,video=None):
        self.root=game_root(root)
        self.video=Path(video).resolve() if video else None
        if self.video and self.video not in video_files(self.root): raise ValueError('اختر ملف الفيديو من حسابات Steam المكتشفة.')
        self.store=self.root/'.deadlock-fps-studio'
        self.manifest=self.store/'state.json'
    def state(self):
        return json.loads(self.manifest.read_text()) if self.manifest.exists() else {'files':{}}
    @staticmethod
    def graphics_managed(state):
        if 'graphics_managed' in state:return bool(state['graphics_managed'])
        return any(Path(name).name=='video.txt' or any(keys and scope in (['GameInfo','ConVars'],['GameInfo','SceneSystem']) for scope,keys in entry.get('owned',[])) for name,entry in state.get('files',{}).items())
    def checked_path(self,p):
        p=Path(p)
        resolved=p.resolve()
        if not resolved.is_relative_to(self.root) and resolved not in video_files(self.root): raise ValueError('Unsafe managed path')
        if p.is_symlink(): raise ValueError('Symlink targets are not supported')
        return resolved
    def baseline(self,p,state):
        entry=state['files'].get(str(p))
        if not entry:return p.read_bytes() if p.exists() else None
        original=(self.store/entry['backup']).read_bytes() if entry['existed'] else None
        current=p.read_bytes() if p.exists() else None
        if (digest(current) if current is not None else None)==entry['applied']:return original
        if p.name=='video.txt' and current is not None and original is not None:
            text=current.decode('utf-8-sig')
            if entry.get('expected'):
                expected=(self.store/entry['expected']).read_text(encoding='utf-8-sig')
                owned=entry.get('owned',footprint(original.decode('utf-8-sig'),expected,p))
                expected_values=flat(expected,['video.cfg']);keys=owned[0][1]
            else:
                from .settings import Settings
                expected_values=values(Settings.from_dict(state.get('settings',{})))[0]
                keys=LEGACY_VIDEO_KEYS & expected_values.keys()
                owned=[(['video.cfg'],list(keys))]
            actual=flat(text,['video.cfg'])
            if all(equivalent(actual.get(k),expected_values.get(k)) for k in keys):
                return clean_base(original.decode('utf-8-sig'),text,owned).encode()
        raise ValueError(f'تغيّرت تعديلات {p.name}. اضغط إصلاح رجوع الإعدادات؛ ستُحفظ الحالة الحالية قبل الدمج.')
    def drift(self):
        state=self.state();changed=[]
        for name,e in state['files'].items():
            p=self.checked_path(name)
            try:self.baseline(p,state)
            except ValueError:changed.append(p.name)
        return changed
    def repair(self,mod_folder):
        """Reapply the saved recipe on current files; never revert a whole patched gameinfo."""
        from .settings import Settings
        ensure_closed();state=self.state()
        if not state.get('settings'):return 'طبّق مستوى التخفيف أولًا لحفظه.'
        settings=Settings.from_dict(state['settings']);new=json.loads(json.dumps(state))
        if settings.mods:
            from .mods import ModLibrary
            from .mod_inspector import require_mods
            require_mods(ModLibrary(mod_folder),self.root,settings.mods)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        archive=self.store/'history'/stamp
        atomic(archive/'state.json',json.dumps(state,indent=2).encode())
        for name,e in new['files'].items():
            p=self.checked_path(name);current=p.read_bytes() if p.exists() else None
            if current is not None:atomic(archive/(digest(name.encode())+'.bin'),current)
            if current is not None and e['existed'] and scopes_for(p):
                original=(self.store/e['backup']).read_bytes()
                if e.get('owned'):owned=e['owned']
                else:
                    # Migration: only the old version's known graphics keys are owned.
                    v,c,scene=values(settings)
                    owned=[(['video.cfg'],list(LEGACY_VIDEO_KEYS))] if p.name=='video.txt' else [(['GameInfo','ConVars'],list(c)),(['GameInfo','SceneSystem'],list(scene))]
                base=clean_base(original.decode('utf-8-sig'),current.decode('utf-8-sig'),owned).encode()
                backup='rebased/'+stamp+'-'+digest(name.encode())+'.bin';atomic(self.store/backup,base);e['backup']=backup
            e['applied']=digest(current) if current is not None else None
        try:
            atomic(self.manifest,json.dumps(new,indent=2).encode())
            graphics=self.graphics_managed(state)
            plan=self.plan(settings,mod_folder) if graphics else self.plan_mods(settings.mods,mod_folder)
            result=self.apply(plan,settings,mod_only=not graphics)
        except Exception:
            atomic(self.manifest,json.dumps(state,indent=2).encode());raise
        return 'تم إصلاح التعديلات على الملفات الحالية مع حفظ الدقة وتغييرات تحديث اللعبة. '+result
    def plan(self,s,mod_folder=None):
        ensure_closed(); state=self.state(); planned={}
        video,convars,scene=values(s)
        gi=self.checked_path(self.root/'game/citadel/gameinfo.gi')
        text=self.baseline(gi,state).decode('utf-8-sig')
        if s.engine:
            text=kv.update(text,['GameInfo','ConVars'],convars)
            text=kv.update(text,['GameInfo','SceneSystem'],scene)
        elif s.aspect_ratio is not None:
            text=kv.update(text,['GameInfo','ConVars'],{'r_aspectratio':f'{s.aspect_ratio:.2f}'})
        if s.mods: text=kv.add_search_path(text)
        planned[gi]=text.encode()
        if self.video:
            source=self.baseline(self.video,state)
            if source is None: raise ValueError('Video config not found')
            source=keep_resolution(source,self.video.read_bytes())
            planned[self.video]=kv.update(source.decode('utf-8-sig'),['video.cfg'],video).encode()
        else: raise ValueError('شغل اللعبة مرة واحدة ثم اختر حساب Steam الذي تريد تعديل إعداداته.')
        moddir=self.root/'game/citadel/fps_studio'
        for key,(filename,_,_) in MODS.items():
            target=self.checked_path(moddir/filename.split(' - ')[0])
            if key in s.mods:
                folder=Path(mod_folder or '')
                source=folder/filename
                if not source.exists(): source=folder/'MODS'/filename
                if not source.exists(): source=folder/filename.split(' - ')[0]
                if not source.exists() and target.exists(): source=target
                if not source.exists(): raise ValueError(f'استورد المود أولًا من صفحة المودات: {filename}')
                vpk_entries(source); self.baseline(target,state); planned[target]=source.read_bytes()
            elif str(target) in state['files']: planned[target]=self.baseline(target,state)
        # Revert previously managed files that are no longer selected (e.g. another Steam account).
        for p in state['files']:
            path=self.checked_path(p)
            if path not in planned:
                base=self.baseline(path,state)
                planned[path]=keep_resolution(base,path.read_bytes()) if path.name=='video.txt' and base is not None and path.exists() else base
        return {p:b for p,b in planned.items() if str(p) not in state['files'] or (p.read_bytes() if p.exists() else None)!=b}
    def plan_mods(self,mods,folder):
        """Install/remove selected mods without touching any video or graphics setting."""
        from .settings import Settings
        Settings(mods=mods).validate();ensure_closed();state=self.state();planned={}
        gi=self.checked_path(self.root/'game/citadel/gameinfo.gi')
        original=self.baseline(gi,state).decode('utf-8-sig')
        current=gi.read_bytes();text=current.decode('utf-8-sig')
        if mods:text=kv.add_search_path(text)
        else:
            original_paths=kv.section(original,['GameInfo','FileSystem','SearchPaths']).children
            if not any(n.key.lower()=='game' and n.value=='citadel/fps_studio' for n in original_paths):
                paths=kv.section(text,['GameInfo','FileSystem','SearchPaths']).children
                for n in reversed(paths):
                    if n.key.lower()=='game' and n.value=='citadel/fps_studio':text=text[:n.start]+text[n.end:]
        if text!=current.decode('utf-8-sig'):planned[gi]=text.encode()
        for key,(filename,_,_) in MODS.items():
            target=self.checked_path(self.root/'game/citadel/fps_studio'/filename.split(' - ')[0])
            base=self.baseline(target,state)
            if key in mods:
                source=Path(folder)/filename
                if not source.exists() and target.exists():source=target
                if not source.exists():raise ValueError(f'استورد المود أولًا: {MODS[key][1]}')
                vpk_entries(source);data=source.read_bytes()
                if (target.read_bytes() if target.exists() else None)!=data:planned[target]=data
            elif str(target) in state['files'] and (target.read_bytes() if target.exists() else None)!=base:planned[target]=base
        return planned
    def apply(self,plan,s,mod_only=False):
        ensure_closed()
        if not plan:
            state=self.state();state['graphics_managed']=not mod_only or self.graphics_managed(state);state['settings']=s.to_dict();atomic(self.manifest,json.dumps(state,indent=2).encode())
            return 'الإعدادات مطبقة بالفعل.'
        state=self.state(); previous={}; new=json.loads(json.dumps(state))
        self.store.mkdir(parents=True,exist_ok=True)
        for p,b in plan.items():
            p=self.checked_path(p); self.baseline(p,state)
            previous[p]=p.read_bytes() if p.exists() else None
            if str(p) not in new['files']:
                name='originals/'+digest(str(p).encode())+'.bin'
                if previous[p] is not None: atomic(self.store/name,previous[p])
                new['files'][str(p)]={'backup':name,'existed':previous[p] is not None,'applied':None}
            entry=new['files'][str(p)]
            entry['applied']=digest(b) if b is not None else None
            if b is not None and scopes_for(p):
                expected='applied/'+digest(b)+'.bin';atomic(self.store/expected,b);entry['expected']=expected
                original=(self.store/entry['backup']).read_text(encoding='utf-8-sig') if entry['existed'] else ''
                prior=state['files'].get(str(p),{}).get('owned')
                entry['owned']=prior if mod_only and prior else footprint(original,b.decode('utf-8-sig'),p)
                if not mod_only:
                    v,c,scene=values(s)
                    if not s.engine:
                        c={'r_aspectratio':c['r_aspectratio']} if s.aspect_ratio is not None else {};scene={}
                    entry['owned']=[(['video.cfg'],list(v))] if p.name=='video.txt' else [(['GameInfo','ConVars'],list(c)),(['GameInfo','SceneSystem'],list(scene))]
        new['schema']=2;new['graphics_managed']=not mod_only or self.graphics_managed(state);new['settings']=s.to_dict(); new['updated']=datetime.now(timezone.utc).isoformat()
        try:
            for p,b in plan.items(): self.write(p,b)
            atomic(self.manifest,json.dumps(new,indent=2).encode())
        except Exception:
            for p,b in previous.items(): self.write(p,b)
            raise
        return f'تم تطبيق الإعدادات وحفظ النسخ الأصلية ({len(plan)} ملفات).'
    @staticmethod
    def write(p,b):
        if b is None: p.unlink(missing_ok=True)
        else: atomic(p,b)
    def restore(self,preserve_changes=False):
        ensure_closed(); state=self.state(); originals={}; current={}
        for name,e in state['files'].items():
            p=self.checked_path(name); current[p]=p.read_bytes() if p.exists() else None
            original=(self.store/e['backup']).read_bytes() if e['existed'] else None
            if (digest(current[p]) if current[p] is not None else None)!=e['applied']:
                try:original=self.baseline(p,state)
                except ValueError:
                    if not preserve_changes:raise ValueError('توجد تغييرات فعلية خارج البرنامج. استخدم الإصلاح أو خيار حفظ الحالة الحالية قبل الاسترجاع.')
            originals[p]=original
            if p.name=='video.txt' and originals[p] is not None and current[p] is not None:
                originals[p]=keep_resolution(originals[p],current[p])
        if not originals: return 'لا توجد نسخة تحتاج إلى الاسترجاع.'
        # Preserve every current file before restoration, including patch changes.
        archive=self.store/'history'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        for p,b in current.items():
            if b is not None: atomic(archive/(digest(str(p).encode())+'.bin'),b)
        atomic(archive/'state.json',json.dumps(state,indent=2).encode())
        try:
            for p,b in originals.items(): self.write(p,b)
            atomic(self.manifest,b'{"files":{}}')
        except Exception:
            for p,b in current.items(): self.write(p,b)
            raise
        return 'تم استرجاع الملفات الأصلية وحفظ نسخة من الحالة السابقة.'
