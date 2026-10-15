"""Native Steam relay selection; independent implementation using Valve's public data."""
from dataclasses import dataclass,asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import ipaddress,json,os,re,subprocess,urllib.request,math,shutil
from datetime import datetime,timezone
from .core import atomic,ASSETS
SDR_URL='https://api.steampowered.com/ISteamApps/GetSDRConfig/v1/?appid=1422450'
@dataclass(frozen=True,order=True)
class Relay:
    ip: str
    first: int
    last: int
@dataclass(frozen=True)
class Region:
    code: str
    name: str
    relays: tuple

def checked_relay(ip,first,last):
    address=ipaddress.ip_address(ip)
    if address.version!=4 or not address.is_global:raise ValueError('عنوان سيرفر غير عام أو غير صالح.')
    if type(first) is not int or type(last) is not int or not 1<=first<=last<=65535:raise ValueError('منافذ غير صالحة.')
    return Relay(str(address),first,last)

def parse_catalog(data):
    if not isinstance(data,dict) or not isinstance(data.get('pops'),dict):raise ValueError('بيانات Steam غير صالحة.')
    if len(data['pops'])>250:raise ValueError('قائمة السيرفرات أكبر من المتوقع.')
    regions=[]
    for code,pop in data['pops'].items():
        if not re.fullmatch(r'[a-z0-9_-]{1,32}',code) or not isinstance(pop,dict):continue
        relays=[]
        for relay in pop.get('relays',[]):
            ports=relay.get('port_range',[27015,27060])
            if len(ports)!=2:raise ValueError('مدى منافذ غير صالح.')
            relays.append(checked_relay(relay.get('ipv4',''),*ports))
        if len(relays)>256:raise ValueError('عدد خوادم المنطقة أكبر من المتوقع.')
        if relays:regions.append(Region(code,str(pop.get('desc',code))[:160],tuple(sorted(set(relays)))))
    if not regions:raise ValueError('لم أجد مناطق اتصال قابلة للاستخدام.')
    return sorted(regions,key=lambda r:r.name.casefold())

def exclude_shared(blocked,allowed):
    result=set()
    for relay in blocked:
        spans=[(relay.first,relay.last)]
        for keep in allowed:
            if keep.ip!=relay.ip:continue
            remaining=[]
            for first,last in spans:
                if keep.last<first or keep.first>last:remaining.append((first,last));continue
                if first<keep.first:remaining.append((first,keep.first-1))
                if last>keep.last:remaining.append((keep.last+1,last))
            spans=remaining
        result.update(Relay(relay.ip,first,last) for first,last in spans)
    return sorted(result)

class ServerStore:
    def __init__(self,folder):self.folder=Path(folder);self.cache=self.folder/'catalog.json';self.state_path=self.folder/'selection.json'
    def load_catalog(self):
        p=self.cache if self.cache.exists() else ASSETS/'servers/deadlock-sdr.json'
        data=json.loads(p.read_text(encoding='utf-8'));return parse_catalog(data),str(data.get('revision',''))
    def refresh(self):
        request=urllib.request.Request(SDR_URL,headers={'User-Agent':'DeadlockToolbox/2.0'})
        with urllib.request.urlopen(request,timeout=20) as r:
            if r.geturl().split('/')[2]!='api.steampowered.com':raise ValueError('وجهة غير متوقعة لبيانات Steam.')
            raw=r.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise ValueError('بيانات Steam أكبر من المتوقع.')
        data=json.loads(raw);regions=parse_catalog(data);atomic(self.cache,raw);return regions,str(data.get('revision',''))
    def state(self):
        return json.loads(self.state_path.read_text(encoding='utf-8')) if self.state_path.exists() else {'blocked':[],'rules':[],'presets':{}}
    def save(self,data):atomic(self.state_path,json.dumps(data,ensure_ascii=False,indent=2).encode())
    def save_preset(self,name,codes):
        name=name.strip()
        if not name or len(name)>60:raise ValueError('اختر اسمًا قصيرًا للحفظ.')
        state=self.state();state.setdefault('presets',{})[name]=sorted(set(codes));self.save(state)
    def delete_preset(self,name):
        state=self.state();state.setdefault('presets',{}).pop(name,None);self.save(state)
    def plan(self,regions,selected,action):
        known={r.code:r for r in regions};selected=set(selected)
        if not selected<=known.keys():raise ValueError('منطقة غير موجودة في البيانات الحالية.')
        state=self.state();blocked=set(state.get('blocked',[]))&known.keys()
        if action=='block':blocked|=selected
        elif action=='unblock':blocked-=selected
        elif action=='only':
            if not selected:raise ValueError('اختر منطقة واحدة على الأقل للسماح بها.')
            blocked=set(known)-selected
        elif action=='clear':blocked=set()
        else:raise ValueError('عملية غير صالحة.')
        # Never deny a shared relay needed by a region the user leaves available.
        allowed={relay for r in regions if r.code not in blocked for relay in r.relays}
        desired=exclude_shared({relay for r in regions if r.code in blocked for relay in r.relays},allowed)
        if len(desired)>2000:raise ValueError('عدد القواعد أكبر من المتوقع.')
        return {'schema':1,'old':state.get('rules',[]),'new':[asdict(r) for r in desired]},sorted(blocked)
    def record(self,blocked,rules):
        state=self.state();state.update(blocked=blocked,rules=rules,applied_at=datetime.now(timezone.utc).isoformat());self.save(state)

@dataclass(frozen=True)
class PingResult:
    latency: float | None
    loss: int | None
    status: str
    detail: str
    address: str = ''

def probe_address(ip):
    ip=checked_relay(ip,1,1).ip
    if os.name=='nt':
        script=f'@((Test-Connection -ComputerName {ip} -Count 3 -ErrorAction SilentlyContinue).ResponseTime) | ConvertTo-Json -Compress'
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            samples=json.loads(result.stdout or '[]');samples=samples if isinstance(samples,list) else [samples]
            samples=[float(s) for s in samples if s is not None]
        except (ValueError,TypeError):
            return PingResult(None,None,'error','تعذر قراءة نتيجة أداة قياس Windows.',ip)
        if result.returncode and not samples:
            return PingResult(None,None,'error','تعذر تشغيل قياس Windows: '+result.stderr.strip()[:240],ip)
    else:
        env=os.environ.copy();env['LC_ALL']='C'
        result=subprocess.run(['ping','-n','-c','3','-W','1',ip],capture_output=True,text=True,timeout=8,env=env)
        samples=[float(s.replace(',','.')) for s in re.findall(r'time\s*[=<]\s*([\d.,]+)\s*ms',result.stdout)]
        if result.returncode not in (0,1):
            return PingResult(None,None,'error','تعذر تشغيل أداة القياس: '+result.stderr.strip()[:240],ip)
    samples=[s for s in samples if math.isfinite(s) and s>=0][:3]
    if not samples:return PingResult(None,100,'no_reply','لم يصل رد ICMP. قد تكون الردود محجوبة؛ لا يعني هذا أن سيرفر اللعبة متوقف.',ip)
    return PingResult(round(sum(samples)/len(samples),1),round((3-len(samples))*100/3),'ok',f'متوسط {len(samples)} ردود من 3 محاولات ICMP. هذا قياس للاتصال الوسيط وليس بنق المباراة.',ip)

def probe_region(region):
    tried=[]
    # A region can have a non-responsive first relay. Try two more instead of declaring it dead.
    for relay in region.relays[:3]:
        try:result=probe_address(relay.ip)
        except FileNotFoundError:return PingResult(None,None,'error','أداة القياس غير مثبتة. ثبّت ping في Linux أو تأكد من توفر PowerShell في Windows.')
        except PermissionError:return PingResult(None,None,'error','النظام منع أداة القياس من العمل. لا تُعرض نتيجة فقد وهمية.')
        except subprocess.TimeoutExpired:result=PingResult(None,None,'timeout','انتهت مهلة قياس هذا العنوان.',relay.ip)
        except OSError as e:return PingResult(None,None,'error','خطأ في أداة القياس: '+str(e)[:200])
        tried.append(result)
        if result.status=='ok':return result
        if result.status=='error':return result
    if not tried:return PingResult(None,None,'error','لا يوجد عنوان صالح لهذه المنطقة.')
    last=tried[-1]
    return PingResult(None,last.loss,last.status,last.detail+f' جُرّبت {len(tried)} عناوين في المنطقة.',last.address)

def ping_region(region):
    result=probe_region(region)
    return result.latency,result.loss

def ping_regions(regions,on_result=None):
    results={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        pending={pool.submit(probe_region,r):r.code for r in regions}
        for future in as_completed(pending):
            code=pending[future]
            try:result=future.result()
            except Exception as e:result=PingResult(None,None,'error','تعذر إكمال القياس: '+str(e)[:200])
            results[code]=result
            if on_result:on_result(code,result)
    return results
