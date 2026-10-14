"""Preview-first file operations with immutable originals and transactional rollback."""
from pathlib import Path
import hashlib, json, os, re, shutil, struct, tempfile
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
    p=Path(path).expanduser().resolve()
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
    b=path.read_bytes()
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

class Studio:
    def __init__(self,root,video=None):
        self.root=game_root(root)
        self.video=Path(video).resolve() if video else None
        if self.video and self.video not in video_files(self.root): raise ValueError('اختر ملف الفيديو من حسابات Steam المكتشفة.')
        self.store=self.root/'.deadlock-fps-studio'
        self.manifest=self.store/'state.json'
    def state(self):
        return json.loads(self.manifest.read_text()) if self.manifest.exists() else {'files':{}}
    def checked_path(self,p):
        p=Path(p)
        resolved=p.resolve()
        if not resolved.is_relative_to(self.root) and resolved not in video_files(self.root): raise ValueError('Unsafe managed path')
        if p.is_symlink(): raise ValueError('Symlink targets are not supported')
        return resolved
    def baseline(self,p,state):
        entry=state['files'].get(str(p))
        if entry:
            if (digest(p.read_bytes()) if p.exists() else None)!=entry['applied']:
                raise ValueError(f'الملف تغير خارج البرنامج: {p.name}. احفظ تغييراتك ثم استخدم الاسترجاع مع الاحتفاظ بالتغييرات الحالية.')
            return (self.store/entry['backup']).read_bytes() if entry['existed'] else None
        return p.read_bytes() if p.exists() else None
    def plan(self,s,mod_folder=None):
        ensure_closed(); state=self.state(); planned={}
        video,convars,scene=values(s)
        gi=self.checked_path(self.root/'game/citadel/gameinfo.gi')
        text=self.baseline(gi,state).decode('utf-8-sig')
        if s.engine:
            text=kv.update(text,['GameInfo','ConVars'],convars)
            text=kv.update(text,['GameInfo','SceneSystem'],scene)
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
        return {p:b for p,b in planned.items() if (p.read_bytes() if p.exists() else None)!=b}
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
    def apply(self,plan,s):
        ensure_closed()
        if not plan: return 'الإعدادات مطبقة بالفعل.'
        state=self.state(); previous={}; new=json.loads(json.dumps(state))
        self.store.mkdir(parents=True,exist_ok=True)
        for p,b in plan.items():
            p=self.checked_path(p); self.baseline(p,state)
            previous[p]=p.read_bytes() if p.exists() else None
            if str(p) not in new['files']:
                name='originals/'+digest(str(p).encode())+'.bin'
                if previous[p] is not None: atomic(self.store/name,previous[p])
                new['files'][str(p)]={'backup':name,'existed':previous[p] is not None,'applied':None}
            new['files'][str(p)]['applied']=digest(b) if b is not None else None
        new['settings']=s.to_dict(); new['updated']=datetime.now(timezone.utc).isoformat()
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
            if (digest(current[p]) if current[p] is not None else None)!=e['applied']:
                if not preserve_changes: raise ValueError('توجد تغييرات خارج البرنامج. اختر الاحتفاظ بنسخة من الحالة الحالية ثم الاسترجاع.')
            originals[p]=(self.store/e['backup']).read_bytes() if e['existed'] else None
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
