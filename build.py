"""Build on each target OS: python build.py"""
from pathlib import Path
import subprocess,sys,shutil
root=Path(__file__).parent.resolve()
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir',
 '--name','DeadlockToolbox','--icon',str(root/'assets/app.ico'),'--add-data',f'{root / "assets"}:assets',str(root/'main.py')],cwd=root,check=True)
folder=root/'dist/DeadlockToolbox'
shutil.copytree(root/'docs',folder/'docs',dirs_exist_ok=True)
for name in ['LICENSE','THIRD_PARTY.md','README.md']:shutil.copy2(root/name,folder/name)
# Include distribution license and notice files without flattening paths.
from importlib.metadata import distribution
for package in ['PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','psutil','pyinstaller']:
    dist=distribution(package)
    for item in dist.files or []:
        if any(word in str(item).lower() for word in ['license','copying','notice']):
            source=Path(dist.locate_file(item))
            if source.is_file():
                target=folder/'notices'/package/str(item).replace('../','')
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
target='windows' if sys.platform=='win32' else sys.platform
shutil.make_archive(str(root/'dist'/f'DeadlockToolbox-{target}-x64'),'zip',root/'dist','DeadlockToolbox')
