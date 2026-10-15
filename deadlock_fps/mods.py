"""Bounded, transactional imports; recognize supported VPKs by their contents."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,os,sys,zipfile
from .core import atomic,vpk_entries
from .settings import MODS
HASHES={
 'daylock':'93bdf68bb2a7fb84ce335db6e12ad679ad8dbe0fa36a5cf792bab13b14520d3e',
 'names':'8e4732f026ba7f9f7072dab893546bebb2140a4b059d3565e6113e78685d98e9',
 'health':'c9379dbef8cbb518d74363d55e39b7a811546cf45f2ad4eeac5ce15f2167539d',
 'sinner':'98f0f8eb81a2e143d547e0fe29e35127104006f75e26378dad1ef294722fc7b7',
}
MAX_FILE=64*1024*1024
MAX_TOTAL=256*1024*1024

class ImportCancelled(ValueError):pass

@dataclass
class ImportReport:
    matched:set
    ignored:list

class ModLibrary:
    def __init__(self,cache):self.cache=Path(cache)
    def verify(self,path,key):
        try:
            if path.is_symlink():return False
            stat=path.stat()
            if not 12<=stat.st_size<=MAX_FILE:return False
            # Some filesystems retain identical stat timestamps for rapid edits.
            # Four bounded known files are checked on user actions, never polled.
            with path.open('rb') as stream:data=stream.read(MAX_FILE+1)
            return 12<=len(data)<=MAX_FILE and hashlib.sha256(data).hexdigest()==HASHES[key]
        except OSError:return False
    def available(self):return {k for k,(name,_,_) in MODS.items() if self.verify(self.cache/name,k)}
    def installed(self,root):
        return {k for k,(name,_,_) in MODS.items() if self.verify(Path(root)/'game/citadel/fps_studio'/name.split(' - ')[0],k)} if root else set()
    def import_sources(self,paths):return self.import_report(paths).matched
    def import_report(self,paths,cancel=None,progress=None):
        matched={};ignored=[];total=0;visited=0
        def stop():
            if cancel and cancel.is_set():raise ImportCancelled('أُلغي الاستيراد؛ لم تتغير ملفات اللعبة.')
        def accept(stream,name):
            nonlocal total
            stop();chunks=[];size=0
            while chunk:=stream.read(256*1024):
                stop();size+=len(chunk);total+=len(chunk)
                if size>MAX_FILE or total>MAX_TOTAL:raise ValueError('الحزمة أكبر من المسموح. اختر ملفات المودات فقط.')
                chunks.append(chunk)
            data=b''.join(chunks);sha=hashlib.sha256(data).hexdigest();key=next((k for k,h in HASHES.items() if sha==h),None)
            if key:vpk_entries(data);matched[key]=data
            elif len(ignored)<12:ignored.append(name)
            if progress:progress(('read',name))
        def files(source):
            nonlocal visited
            if not source.exists():raise ValueError('الملف أو المجلد غير موجود: '+source.name)
            if source.is_symlink():raise ValueError('اختر الملفات الأصلية بدل الروابط الرمزية.')
            if source.is_file():yield source;return
            for base,dirs,names in os.walk(source,followlinks=False):
                stop();visited+=len(names)+len(dirs)
                if visited>4096:raise ValueError('المجلد كبير جدًا؛ اختر مجلد MODS أو الحزمة مباشرة.')
                if len(Path(base).relative_to(source).parts)>=4:dirs[:]=[]
                for name in names:
                    if '.vpk' in name.lower() or name.lower().endswith('.zip'):yield Path(base)/name
        for source in dict.fromkeys(map(Path,paths)):
            for path in files(source):
                stop()
                if path.is_symlink():continue
                if path.suffix.lower()=='.zip':
                    with zipfile.ZipFile(path) as archive:
                        members=archive.infolist()
                        if len(members)>4096:raise ValueError('الحزمة تحتوي ملفات كثيرة جدًا؛ اختر حزمة MODS الأصلية.')
                        for entry in members:
                            if entry.is_dir() or '.vpk' not in Path(entry.filename).name.lower():continue
                            if entry.file_size>MAX_FILE or total+entry.file_size>MAX_TOTAL:raise ValueError('ملف مود أكبر من الحد المسموح.')
                            with archive.open(entry) as stream:accept(stream,Path(entry.filename).name)
                else:
                    if path.stat().st_size>MAX_FILE:raise ValueError('ملف المود أكبر من 64 MB.')
                    with path.open('rb') as stream:accept(stream,path.name)
        stop()
        if not matched:raise ValueError('لم أجد مودًا مدعومًا. أضف حزمة MODS الأصلية أو ملفاتها؛ يُتعرف عليها حتى لو تغيّر الاسم.')
        if progress:progress(('commit',''))
        previous={};written=[]
        try:
            for key,data in matched.items():
                target=self.cache/MODS[key][0]
                if target.is_symlink():raise ValueError('ملف المكتبة يشير إلى رابط رمزي؛ اختر مكتبة سليمة.')
                old=target.read_bytes() if target.exists() else None;previous[target]=old
                if old!=data:atomic(target,data);written.append(target)
        except Exception:
            for target in reversed(written):
                if previous[target] is None:target.unlink(missing_ok=True)
                else:atomic(target,previous[target])
            raise
        return ImportReport(set(matched),ignored)
    def discover(self):
        bases=[Path.cwd(),Path(__file__).resolve().parents[2],Path(sys.executable).resolve().parent,Path.home()/'Downloads']
        if getattr(sys,'frozen',False):bases+=list(Path(sys.executable).resolve().parents)[:4]
        candidates=[]
        for base in dict.fromkeys(bases):
            if not base.is_dir():continue
            if (base/'MODS').is_dir():candidates.append(base/'MODS')
            candidates.extend(base.glob('MODS*.zip'))
        return list(dict.fromkeys(candidates))
