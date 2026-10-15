"""CI-only real netsh/PowerShell check on a disposable Windows runner.

Creates two outbound UDP test rules on unused destination ports. Removes both
in finally. Does not request UAC or touch live users' machines.
"""
import json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deadlock_fps.firewall import windows_apply,validate_plan,rule_name
assert os.name=='nt' and os.environ.get('GITHUB_ACTIONS')=='true', 'Only run on disposable Windows CI'
netsh=str(Path(os.environ['SystemRoot'])/'System32/netsh.exe')
row={'ip':'8.8.8.8','first':65530,'last':65530}
plan=validate_plan({'schema':1,'old':[],'new':[row]})
name=rule_name(plan['new'][0]);sentinel='DeadlockToolbox_SDR_not_owned'
def command(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=60)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout

def exists(display):
    script=f"@(Get-NetFirewallRule -DisplayName '{display}' -ErrorAction SilentlyContinue).Count | ConvertTo-Json -Compress"
    return json.loads(command(['powershell.exe','-NoProfile','-NonInteractive','-Command',script]))>0
try:
    windows_apply(plan);assert exists(name),'Block rule was not created'
    windows_apply(validate_plan({'schema':1,'old':[row],'new':[]}));assert not exists(name),'Unblock did not remove netsh rule'
    windows_apply(plan)
    command([netsh,'advfirewall','firewall','add','rule','name='+sentinel,'dir=out','action=block','protocol=UDP','remoteip=8.8.8.8','remoteport=65531'])
    windows_apply(validate_plan({'schema':1,'reset':True,'old':[row],'new':[]}))
    assert not exists(name),'Clear failed to remove netsh-created rule by DisplayName'
    assert exists(sentinel),'Clear removed a rule outside the owned hash namespace'
    print('Real Windows block, unblock and scoped clear verified.')
finally:
    for display in [name,sentinel]:
        subprocess.run([netsh,'advfirewall','firewall','delete','rule','name='+display],capture_output=True,text=True,timeout=60)
