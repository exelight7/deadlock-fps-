"""Exercise the shipped --install UI, then launch the installed binary."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import time

root=Path(__file__).resolve().parents[1]
name='DeadlockToolbox.exe' if os.name=='nt' else 'DeadlockToolbox'
source=root/'dist/DeadlockToolbox'/name
with tempfile.TemporaryDirectory(prefix='toolbox-install-smoke-') as temp:
    folder=Path(temp).resolve()
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',XDG_DATA_HOME=str(folder/'data'),
             XDG_CONFIG_HOME=str(folder/'config'),XDG_CACHE_HOME=str(folder/'cache'),
             LOCALAPPDATA=str(folder/'local'))
    base=folder/('local' if os.name=='nt' else 'data')/'DeadlockToolbox'
    process=subprocess.Popen([str(source),'--install'],cwd=source.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+60
        installed=[]
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Installer exited: '+process.communicate()[1].decode(errors='replace'))
            installed=list(base.glob('*/'+name))
            if installed and (base/'last-install.json').is_file():break
            time.sleep(.1)
        else:raise RuntimeError('Per-user installation did not complete')
        diagnostics=json.loads((base/'last-install.json').read_text(encoding='utf-8'))
        if diagnostics['shortcut_error']:raise RuntimeError('Shortcut creation failed: '+diagnostics['shortcut_error'])
        if os.name!='nt':assert (folder/'data/applications/deadlock-toolbox.desktop').is_file()
        # Give the UI time to receive its worker result before closing the process.
        time.sleep(1)
        if os.name=='nt':
            # Confirm the actual Start Menu link, including its target, on Windows.
            script="$p=Join-Path ([Environment]::GetFolderPath('Programs')) 'Deadlock Toolbox.lnk'; $w=New-Object -ComObject WScript.Shell; for($i=0;$i -lt 100;$i++){if((Test-Path $p) -and $w.CreateShortcut($p).TargetPath -eq $env:TOOLBOX_EXPECTED_BINARY){exit 0}; Start-Sleep -Milliseconds 100}; throw 'Start Menu shortcut missing or incorrect'"
            try:
                subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                               env=dict(env,TOOLBOX_EXPECTED_BINARY=str(installed[0])),check=True,timeout=30)
            except subprocess.SubprocessError as error:
                status=base/'last-install.json'
                raise RuntimeError('Shortcut verification failed. Install diagnostics: '+(status.read_text(encoding='utf-8') if status.exists() else 'not written')) from error
    finally:
        if process.poll() is None:process.terminate()
        _,error=process.communicate(timeout=10)
        if error:raise RuntimeError(error.decode(errors='replace'))
    binary=installed[0]
    assert (binary.parent/'_internal/assets/app.png').is_file()
    process=subprocess.Popen([str(binary),'--updates'],cwd=binary.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        try:
            process.wait(timeout=2.5)
            raise RuntimeError('Installed GUI exited: '+process.communicate()[1].decode(errors='replace'))
        except subprocess.TimeoutExpired:pass
    finally:
        if process.poll() is None:process.terminate()
        _,error=process.communicate(timeout=10)
        if error:raise RuntimeError(error.decode(errors='replace'))
    print('Per-user GUI installation, bundled resources and installed startup verified.')
