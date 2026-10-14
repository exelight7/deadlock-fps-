"""Import a folder, original ZIP or renamed VPK into a persistent local library."""
from pathlib import Path
import hashlib, sys, zipfile
from .core import atomic, vpk_entries
from .settings import MODS
HASHES={
 'daylock':'93bdf68bb2a7fb84ce335db6e12ad679ad8dbe0fa36a5cf792bab13b14520d3e',
 'names':'8e4732f026ba7f9f7072dab893546bebb2140a4b059d3565e6113e78685d98e9',
 'health':'c9379dbef8cbb518d74363d55e39b7a811546cf45f2ad4eeac5ce15f2167539d',
 'sinner':'98f0f8eb81a2e143d547e0fe29e35127104006f75e26378dad1ef294722fc7b7',
}
MAX_FILE=64*1024*1024
MAX_TOTAL=256*1024*1024
class ModLibrary:
    def __init__(self,cache):self.cache=Path(cache)
    def available(self):
        return {k for k,(name,_,_) in MODS.items() if (self.cache/name).is_file() and hashlib.sha256((self.cache/name).read_bytes()).hexdigest()==HASHES[k]}
    def import_sources(self,paths):
        matched={};total=0
        def accept(data):
            nonlocal total
            total+=len(data)
            if total>MAX_TOTAL:raise ValueError('حزمة المودات أكبر من الحد المسموح.')
            key=next((k for k,h in HASHES.items() if hashlib.sha256(data).hexdigest()==h),None)
            if key:matched[key]=data
        for source in map(Path,paths):
            if source.is_dir():
                files=list(source.glob('*'))
                if (source/'MODS').is_dir():files+=list((source/'MODS').glob('*'))
            else:files=[source]
            for p in files:
                if not p.is_file():continue
                if p.suffix.lower()=='.zip':
                    with zipfile.ZipFile(p) as z:
                        for entry in z.infolist():
                            # Read only VPK members; no archive paths are extracted.
                            if '.vpk' not in Path(entry.filename).name.lower() or entry.is_dir():continue
                            if entry.file_size>MAX_FILE or total+entry.file_size>MAX_TOTAL:raise ValueError('ملف المود أكبر من الحد المسموح.')
                            accept(z.read(entry))
                elif '.vpk' in p.name.lower():
                    if p.stat().st_size>MAX_FILE:raise ValueError('ملف المود أكبر من الحد المسموح.')
                    accept(p.read_bytes())
        if not matched:raise ValueError('لم أجد مودًا مدعومًا. اختر حزمة MODS الأصلية أو ملفات VPK المرفقة، حتى لو تغير اسمها.')
        for key,data in matched.items():
            target=self.cache/MODS[key][0];atomic(target,data);vpk_entries(target)
        return set(matched)
    def discover(self):
        bases=[Path.cwd(),Path(__file__).resolve().parents[2],Path(sys.executable).resolve().parent,Path.home()/'Downloads']
        if getattr(sys,'frozen',False):bases+=list(Path(sys.executable).resolve().parents)[:4]
        candidates=[]
        for base in dict.fromkeys(bases):
            if not base.is_dir():continue
            if (base/'MODS').is_dir():candidates.append(base/'MODS')
            candidates.extend(base.glob('MODS*.zip'))
        return list(dict.fromkeys(candidates))
