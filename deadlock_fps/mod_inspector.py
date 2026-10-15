"""Read-only structural/hash diagnostics for known mods and their load order overlaps."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib
from .core import game_root,vpk_entries
from .settings import MODS
from .mods import HASHES,MAX_FILE

@dataclass(frozen=True)
class Finding:
    severity:str
    title:str
    detail:str
    key:str=''

@dataclass
class Inspection:
    rows:list
    findings:list
    @property
    def errors(self):return [f for f in self.findings if f.severity=='error']
    def to_dict(self):return dict(rows=self.rows,findings=[asdict(f) for f in self.findings])

def checked_vpk(path):
    if path.is_symlink():raise ValueError('روابط الملفات الرمزية غير مدعومة.')
    size=path.stat().st_size
    if not 12<=size<=MAX_FILE:raise ValueError('حجم VPK غير صالح أو يتجاوز 64 MB.')
    value=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(256*1024):value.update(chunk)
    return value.hexdigest(),set(vpk_entries(path))

def inspect_mods(library,root=None,selected=(),cancel=None):
    root=game_root(root) if root else None;selected=set(selected);rows=[];findings=[];trees={};installed_trees={}
    if not selected<=MODS.keys():raise ValueError('مود غير مدعوم في الاختيار.')
    if {'names','health'}<=selected:findings.append(Finding('error','تعارض معروف','Remove Name Tags وOld Healthbars لا يعملان معًا.'))
    installed_root=root/'game/citadel/fps_studio' if root else None
    if installed_root and installed_root.is_symlink():raise ValueError('مجلد المودات يشير إلى مجلد خارجي؛ الفحص متوقف.')
    for key,(filename,title,_) in MODS.items():
        if cancel and cancel.is_set():return None
        cache=Path(library.cache)/filename;target=installed_root/filename.split(' - ')[0] if installed_root else None
        states={};valid_paths={}
        for label,path in [('library',cache),('installed',target)]:
            if not path or not path.exists():states[label]='غير موجود';continue
            try:
                sha,tree=checked_vpk(path)
                if sha!=HASHES[key]:raise ValueError('بصمة الملف تختلف عن المود المرجعي المدعوم.')
                states[label]='سليم • SHA-256';valid_paths[label]=tree
                if label=='installed':installed_trees[key]=tree
            except (OSError,ValueError) as e:
                states[label]='تالف أو معدل';findings.append(Finding('error' if key in selected and (label=='library' or not cache.exists()) else 'warning',title+' / '+label,str(e),key))
        if key in selected:
            source='library' if cache.exists() else 'installed'
            if source not in valid_paths and not any(f.key==key and f.severity=='error' for f in findings):findings.append(Finding('error',title+' غير جاهز','استورد الملف المرجعي من صفحة المودات قبل التطبيق.',key))
            if source in valid_paths:trees[key]=valid_paths[source]
        rows.append(dict(key=key,name=title,selected=key in selected,library=states['library'],installed=states['installed']))
    if {'names','health'}<=installed_trees.keys():findings.append(Finding('warning','تعارض في المودات المركبة','Remove Name Tags وOld Healthbars موجودان معًا في مجلد المودات. راجع الملفات المركبة قبل اللعب.'))
    seen=set()
    for context,values in [('اختيارك',trees),('المودات المركبة',installed_trees)]:
        keys=list(values)
        for i,a in enumerate(keys):
            for b in keys[i+1:]:
                overlap=sorted(values[a]&values[b]);signature=(a,b,tuple(overlap))
                if overlap and signature not in seen:
                    seen.add(signature);findings.append(Finding('warning','تداخل ملفات '+context+': '+MODS[a][1]+' + '+MODS[b][1],f'{len(overlap)} ملفات مشتركة؛ قد يطغى مود على الآخر حسب ترتيب التحميل.\n'+'\n'.join(overlap[:8])))
    return Inspection(rows,findings)

def require_mods(library,root,selected):
    if not selected:return
    result=inspect_mods(library,root,selected)
    if result.errors:raise ValueError('\n'.join(f.title+': '+f.detail for f in result.errors))
