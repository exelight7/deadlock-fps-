"""Versioned GitHub releases and transactional, checksum-verified downloads."""
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from urllib.parse import urlsplit,unquote
import hashlib,hmac,json,os,platform,re,tempfile,time
from .core import atomic

REPOSITORY='exelight7/deadlock-fps-'
REPO_URL='https://github.com/'+REPOSITORY
RELEASES_URL=REPO_URL+'/releases'
LATEST_URL='https://api.github.com/repos/'+REPOSITORY+'/releases/latest'
MAX_METADATA=2*1024*1024
MAX_CHECKSUMS=64*1024
MAX_PACKAGE=512*1024*1024
PACKAGE_NAMES={'linux':'DeadlockToolbox-linux-x64.zip','windows':'DeadlockToolbox-windows-x64.zip'}

@total_ordering
@dataclass(frozen=True,eq=False)
class Version:
    major:int
    minor:int
    patch:int
    pre:tuple=()
    @classmethod
    def parse(cls,value):
        if not isinstance(value,str) or len(value)>150:raise ValueError('رقم إصدار غير صالح.')
        m=re.fullmatch(r'v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?',value)
        if not m:raise ValueError('رقم إصدار غير مدعوم: '+value)
        pre=tuple(m[4].split('.')) if m[4] else ()
        if any(x.isdigit() and len(x)>1 and x[0]=='0' for x in pre):raise ValueError('رقم إصدار تجريبي غير صالح.')
        return cls(*map(int,m.group(1,2,3)),pre)
    def key(self):return self.major,self.minor,self.patch
    def __eq__(self,other):return isinstance(other,Version) and self.key()==other.key() and self.pre==other.pre
    def __hash__(self):return hash((self.key(),self.pre))
    def __lt__(self,other):
        if not isinstance(other,Version):return NotImplemented
        if self.key()!=other.key():return self.key()<other.key()
        if not self.pre or not other.pre:return bool(self.pre) and not other.pre
        for a,b in zip(self.pre,other.pre):
            if a==b:continue
            if a.isdigit() and b.isdigit():return int(a)<int(b)
            if a.isdigit()!=b.isdigit():return a.isdigit()
            return a<b
        return len(self.pre)<len(other.pre)

def platform_key(system=None,machine=None):
    system=(system or platform.system()).lower();machine=(machine or platform.machine()).lower()
    return system if system in PACKAGE_NAMES and machine in {'x86_64','amd64','x64'} else None

def checked_url(value,path):
    if not isinstance(value,str):raise ValueError('رابط الإصدار غير صالح.')
    u=urlsplit(value)
    if u.scheme!='https' or u.netloc!='github.com' or u.query or u.fragment or unquote(u.path)!=path:raise ValueError('رابط إصدار خارج مستودع Toolbox المعتمد.')
    return value

@dataclass(frozen=True)
class Asset:
    name:str
    url:str
    size:int
    digest:str=''

@dataclass(frozen=True)
class Release:
    tag:str
    version:Version
    url:str
    title:str
    notes:str
    published_at:str
    assets:tuple
    def asset(self,name):return next((a for a in self.assets if a.name==name),None)
    def package(self,system=None,machine=None):
        key=platform_key(system,machine)
        return self.asset(PACKAGE_NAMES[key]) if key else None

def parse_release(data):
    if not isinstance(data,dict) or data.get('draft') is not False or data.get('prerelease') is not False:raise ValueError('لا يوجد إصدار عام مستقر قابل للفحص.')
    tag=data.get('tag_name');version=Version.parse(tag)
    if version.pre:raise ValueError('الفحص مخصص للإصدارات المستقرة.')
    url=checked_url(data.get('html_url'),'/'+REPOSITORY+'/releases/tag/'+tag)
    values=data.get('assets')
    if not isinstance(values,list) or len(values)>64:raise ValueError('قائمة حزم الإصدار غير صالحة.')
    assets=[];seen=set()
    for item in values:
        if not isinstance(item,dict):raise ValueError('بيانات حزمة غير صالحة.')
        name=item.get('name')
        if name not in {*PACKAGE_NAMES.values(),'SHA256SUMS.txt'}:continue
        if name in seen:raise ValueError('اسم حزمة مكرر في الإصدار.')
        seen.add(name);limit=MAX_CHECKSUMS if name=='SHA256SUMS.txt' else MAX_PACKAGE;size=item.get('size')
        if item.get('state')!='uploaded' or type(size) is not int or not 0<size<=limit:raise ValueError('الحزمة غير مكتملة أو أكبر من المسموح.')
        link=checked_url(item.get('browser_download_url'),'/'+REPOSITORY+'/releases/download/'+tag+'/'+name)
        digest=item.get('digest') or ''
        if digest and (not isinstance(digest,str) or not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest)):raise ValueError('بصمة حزمة غير صالحة.')
        assets.append(Asset(name,link,size,digest[7:].lower() if digest else ''))
    notes=data.get('body') or '';title=data.get('name') or tag;published=data.get('published_at') or ''
    if not all(isinstance(v,str) for v in (notes,title,published)) or len(notes)>128*1024 or len(title)>256 or len(published)>64:raise ValueError('وصف الإصدار غير صالح.')
    return Release(tag,version,url,title,notes,published,tuple(assets))

def checksum_for(raw,asset,manifest):
    if len(raw)>MAX_CHECKSUMS or len(raw)!=manifest.size:raise ValueError('ملف بصمات التنزيل غير مكتمل.')
    if manifest.digest and not hmac.compare_digest(hashlib.sha256(raw).hexdigest(),manifest.digest):raise ValueError('بصمة ملف التحقق غير مطابقة.')
    values={}
    for line in raw.decode('utf-8-sig').splitlines():
        if not line.strip() or line.startswith('#'):continue
        m=re.fullmatch(r'([a-fA-F0-9]{64})[ \t]+\*?([A-Za-z0-9_.-]+)',line.strip())
        if not m or m[2] in values:raise ValueError('ملف بصمات التنزيل غير صالح أو مكرر.')
        values[m[2]]=m[1].lower()
    value=values.get(asset.name)
    if not value:raise ValueError('بصمة حزمة نظامك غير موجودة.')
    if asset.digest and not hmac.compare_digest(value,asset.digest):raise ValueError('بيانات بصمة الإصدار متعارضة؛ أعد الفحص.')
    return value

class Download:
    """Keep any existing ZIP until the complete new payload matches its hash."""
    def __init__(self,folder,release,asset,expected):
        if not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('بصمة تنزيل غير صالحة.')
        self.folder=Path(folder)/release.tag;self.folder.mkdir(parents=True,exist_ok=True)
        self.target=self.folder/asset.name;fd,name=tempfile.mkstemp(dir=self.folder,prefix='.toolbox-',suffix='.part')
        self.part=Path(name);self.file=os.fdopen(fd,'wb');self.asset=asset;self.expected=expected;self.received=0;self.hash=hashlib.sha256()
    def write(self,chunk):
        if self.file is None:raise ValueError('التنزيل متوقف.')
        if self.received+len(chunk)>self.asset.size:raise ValueError('حجم التنزيل تجاوز حجم الحزمة المنشور.')
        self.file.write(chunk);self.hash.update(chunk);self.received+=len(chunk)
    def commit(self):
        try:
            if self.received!=self.asset.size:raise ValueError('التنزيل غير مكتمل؛ أعد المحاولة.')
            if not hmac.compare_digest(self.hash.hexdigest(),self.expected):raise ValueError('بصمة التنزيل غير مطابقة؛ حُذفت النسخة غير المكتملة.')
            self.file.flush();os.fsync(self.file.fileno());self.file.close();self.file=None;os.replace(self.part,self.target);return self.target
        except Exception:self.abort();raise
    def abort(self):
        if self.file is not None:self.file.close();self.file=None
        self.part.unlink(missing_ok=True)

class UpdateStore:
    def __init__(self,folder):
        self.folder=Path(folder);self.preferences=self.folder/'preferences.json';self.cache=self.folder/'latest.json'
        self.auto_check=True;self.checked_at=0.;self.attempted_at=0.;self.etag='';self.data=None;self.release=None;self.warning=''
        try:
            if self.preferences.exists():
                if self.preferences.stat().st_size>8192:raise ValueError('ملف تفضيلات كبير.')
                d=json.loads(self.preferences.read_text(encoding='utf-8'))
                if not isinstance(d,dict) or type(d.get('auto_check',True)) is not bool:raise ValueError('تفضيلات غير صالحة.')
                self.auto_check=d.get('auto_check',True)
                for field in ['checked_at','attempted_at']:
                    value=d.get(field,0)
                    if type(value) not in (int,float) or not 0<=value<1e12:raise ValueError('وقت فحص غير صالح.')
                    setattr(self,field,float(value))
        except (ValueError,OSError,TypeError):self.warning='تعذر قراءة تفضيلات التحديث؛ يمكنك الفحص يدويًا.'
        try:
            if self.cache.exists():
                if self.cache.stat().st_size>MAX_METADATA+4096:raise ValueError('ملف مخزن كبير.')
                d=json.loads(self.cache.read_text(encoding='utf-8'));self.release=parse_release(d['release']);self.data=d['release']
                etag=d.get('etag','')
                if not isinstance(etag,str) or len(etag)>256 or any(c in etag for c in '\r\n'):raise ValueError('وسم مخزن غير صالح.')
                self.etag=etag
        except (ValueError,OSError,TypeError,KeyError):self.release=None;self.data=None;self.etag='';self.warning='تعذر قراءة نتيجة الفحص المحفوظة؛ اضغط التحقق من التحديثات.'
    def save_preferences(self):
        atomic(self.preferences,json.dumps({'auto_check':self.auto_check,'checked_at':self.checked_at,'attempted_at':self.attempted_at}).encode())
    def due(self,now=None):
        now=time.time() if now is None else now
        if not self.auto_check:return False
        # Clock changes cannot suppress checking indefinitely.
        return (not self.release or not 0<=now-self.checked_at<86400) and (not self.attempted_at or not 0<=now-self.attempted_at<3600)
    def mark_attempt(self):self.attempted_at=time.time();self.save_preferences()
    def record(self,data,etag=''):
        release=parse_release(data)
        if not isinstance(etag,str) or len(etag)>256 or any(c in etag for c in '\r\n'):etag=''
        atomic(self.cache,json.dumps({'release':data,'etag':etag},ensure_ascii=False).encode('utf-8'))
        self.data=data;self.release=release;self.etag=etag;self.checked_at=time.time();self.warning='';self.save_preferences();return release
    def unchanged(self):
        if not self.release:raise ValueError('لا توجد نتيجة محفوظة لتأكيد الفحص.')
        self.checked_at=time.time();self.save_preferences();return self.release
