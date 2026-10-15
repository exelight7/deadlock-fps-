"""Only Toolbox-owned rules, elevated by a short-lived helper on explicit apply."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,os,shutil,subprocess,sys,tempfile
from .servers import checked_relay
CHAIN='DLTB_OUT'
PREFIX='DeadlockToolbox_SDR_'

def validate_plan(plan):
    if not isinstance(plan,dict) or plan.get('schema')!=1:raise ValueError('خطة اتصال غير صالحة.')
    result={'schema':1,'reset':plan.get('reset',False)}
    if type(result['reset']) is not bool:raise ValueError('خطة غير صالحة.')
    for key in ['old','new']:
        rows=plan.get(key)
        if not isinstance(rows,list) or len(rows)>2000:raise ValueError('عدد قواعد غير صالح.')
        checked=[]
        for item in rows:
            if not isinstance(item,dict) or set(item)!={'ip','first','last'}:raise ValueError('قاعدة غير صالحة.')
            checked.append(checked_relay(item['ip'],item['first'],item['last']))
        result[key]=sorted(set(checked))
    if result['reset'] and result['new']:raise ValueError('خطة فك الحظر لا تقبل قواعد جديدة.')
    return result

def rule_name(relay):return PREFIX+hashlib.sha256(f'{relay.ip}:{relay.first}:{relay.last}'.encode()).hexdigest()[:24]

def _run(args,**kwargs):
    return subprocess.run(args,capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),**kwargs)

def linux_apply(plan,run=_run):
    iptables=shutil.which('iptables');restore=shutil.which('iptables-restore')
    if not iptables or not restore:raise RuntimeError('ثبّت iptables وiptables-restore لتفعيل اختيار السيرفرات.')
    def command(*args,required=True):
        result=run([iptables,'-w','5',*args])
        if required and result.returncode:raise RuntimeError(result.stderr.strip() or 'تعذر تعديل قواعد Toolbox.')
        return result
    existing=command('-S',CHAIN,required=False)
    if existing.returncode and ('Permission denied' in existing.stderr or 'Operation not permitted' in existing.stderr):raise PermissionError('تحتاج العملية صلاحية المدير.')
    if not plan['new']:
        # Remove only our jump and our dedicated chain. Never flush a built-in chain.
        if existing.returncode==0:
            for _ in range(16):
                if command('-C','OUTPUT','-j',CHAIN,required=False).returncode:break
                command('-D','OUTPUT','-j',CHAIN)
            command('-F',CHAIN);command('-X',CHAIN)
        return
    created=existing.returncode!=0
    if created:command('-N',CHAIN)
    old_rules=[line for line in existing.stdout.splitlines() if line.startswith('-A '+CHAIN+' ')] if not created else []
    def replace(lines):
        script='\n'.join(['*filter','-F '+CHAIN,*lines,'COMMIT',''])
        result=run([restore,'-w','5','--noflush'],input=script)
        if result.returncode:raise RuntimeError(result.stderr.strip() or 'تعذر تطبيق قواعد Toolbox.')
    rules=[f'-A {CHAIN} -d {r.ip} -p udp --dport {r.first}:{r.last} -j DROP' for r in plan['new']]
    try:
        replace(rules)
        if command('-C','OUTPUT','-j',CHAIN,required=False).returncode:command('-I','OUTPUT','1','-j',CHAIN)
    except Exception:
        replace(old_rules)
        if created:command('-X',CHAIN,required=False)
        raise

def windows_apply(plan,run=_run):
    netsh=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/netsh.exe')
    def command(args):
        result=run([netsh,'advfirewall','firewall',*args])
        if result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'تعذر تعديل قواعد Toolbox.')
    def add(relay):
        command(['add','rule','name='+rule_name(relay),'dir=out','action=block','enable=yes','profile=any',
                 'protocol=UDP','remoteip='+relay.ip,f'remoteport={relay.first}-{relay.last}'])
    def delete(relay):command(['delete','rule','name='+rule_name(relay)])
    if plan['reset']:
        # netsh's rule name is the user-facing DisplayName; Name may be a GUID.
        script="$ErrorActionPreference='Stop'; Get-NetFirewallRule -DisplayName 'DeadlockToolbox_SDR_*' -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match '^DeadlockToolbox_SDR_[a-f0-9]{24}$' } | Remove-NetFirewallRule"
        result=run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script])
        if result.returncode:raise RuntimeError(result.stderr.strip() or 'تعذر فك حظر Toolbox.')
        return
    old=set(plan['old']);new=set(plan['new']);created=[];removed=[]
    try:
        for relay in sorted(new):
            exists=run([netsh,'advfirewall','firewall','show','rule','name='+rule_name(relay)])
            if exists.returncode:add(relay);created.append(relay)
        for relay in sorted(old-new):delete(relay);removed.append(relay)
    except Exception:
        for relay in removed:add(relay)
        for relay in created:delete(relay)
        raise

def helper_main(path):
    p=Path(path)
    with p.open('rb') as source:raw=source.read(512*1024+1)
    if len(raw)>512*1024:raise ValueError('خطة قواعد أكبر من المسموح.')
    plan=validate_plan(json.loads(raw))
    if os.name=='nt':windows_apply(plan)
    elif sys.platform.startswith('linux'):linux_apply(plan)
    else:raise RuntimeError('اختيار السيرفرات مدعوم على Windows وLinux فقط.')

def apply_elevated(plan):
    checked=validate_plan(plan)
    # Validation happens both before and after elevation. No shell text from server data.
    fd,name=tempfile.mkstemp(prefix='deadlock-toolbox-',suffix='.json')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump({'schema':1,'reset':checked['reset'],'old':[asdict(r) for r in checked['old']],'new':[asdict(r) for r in checked['new']]},f)
        exe=str(Path(sys.executable).resolve())
        args=['--firewall-plan',name]
        if not getattr(sys,'frozen',False):args.insert(0,str(Path(__file__).resolve().parent.parent/'main.py'))
        if os.name=='nt':
            def quote(value):return "'"+value.replace("'","''")+"'"
            # ArgumentList is Windows command-line text, not PowerShell code.
            arguments=subprocess.list2cmdline(args)
            script=f"$ErrorActionPreference='Stop'; try {{ $p=Start-Process -FilePath {quote(exe)} -ArgumentList {quote(arguments)} -Verb RunAs -Wait -PassThru; exit $p.ExitCode }} catch {{ Write-Error $_; exit 1 }}"
            command=['powershell.exe','-NoProfile','-NonInteractive','-Command',script]
        elif sys.platform.startswith('linux'):
            pkexec=shutil.which('pkexec')
            if not pkexec:raise RuntimeError('ثبّت polkit لتظهر نافذة صلاحية المدير.')
            command=[pkexec,exe,*args]
        else:raise RuntimeError('النظام غير مدعوم.')
        result=subprocess.run(command,capture_output=True,text=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise RuntimeError(result.stderr.strip() or 'لم تُطبّق القواعد: أُلغيت صلاحية المدير أو فشلت العملية.')
    finally:Path(name).unlink(missing_ok=True)
