"""Start the actual portable executable on its build OS, without game changes."""
import os, subprocess, sys, zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
folder=root/'dist/DeadlockToolbox'
binary=folder/('DeadlockToolbox.exe' if os.name=='nt' else 'DeadlockToolbox')
assert binary.is_file(), binary
internal=folder/'_internal'
for path in ['assets/artwork/rem.jpg','assets/artwork/deadlock.jpg','assets/artwork/duo.jpg','assets/artwork/logo.jpg','assets/fonts/NotoSansArabic.ttf','assets/flags/ae.svg','assets/check.svg']:
    assert (internal/path).is_file(),path
assert list(internal.rglob('*qsvgicon*')), 'SVG icon plugin missing'
target='windows' if sys.platform=='win32' else sys.platform
archive=root/'dist'/f'DeadlockToolbox-{target}-x64.zip'
with zipfile.ZipFile(archive) as z:
    assert 'DeadlockToolbox/THIRD_PARTY.md' in z.namelist()
process=subprocess.Popen([str(binary)],cwd=folder,env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    try:
        process.wait(timeout=2.5)
        raise RuntimeError('Portable GUI exited at startup: '+process.communicate()[1].decode(errors='replace'))
    except subprocess.TimeoutExpired:
        print(f'Portable {target} GUI startup and resources verified.')
finally:
    if process.poll() is None:process.terminate()
    _,error=process.communicate(timeout=10)
    if error:raise RuntimeError(error.decode(errors='replace'))
