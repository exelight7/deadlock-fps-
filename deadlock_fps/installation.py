"""Per-user installs. Never overwrite an executable that may still be running."""
from pathlib import Path, PurePosixPath
import hashlib
import hmac
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
from . import __version__
from .updates import Version

MAX_EXPANDED = 2 * 1024 * 1024 * 1024


def install_base():
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'DeadlockToolbox'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'DeadlockToolbox'


def executable(folder):
    return Path(folder) / ('DeadlockToolbox.exe' if os.name == 'nt' else 'DeadlockToolbox')


def desktop_entry(binary):
    # Desktop Entry Exec has its own escaping rules, independent of the shell.
    value = str(binary).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    icon = binary.parent / '_internal/assets/app.png'
    return f'[Desktop Entry]\nType=Application\nName=Deadlock Toolbox\nComment=Graphics, mods and crosshairs for Deadlock\nExec="{value}"\nIcon={icon}\nTerminal=false\nCategories=Game;Utility;\n'


def create_shortcut(binary):
    if os.name == 'nt':
        # Pass paths as environment data, never interpolated PowerShell code.
        script = "$w=New-Object -ComObject WScript.Shell; $p=Join-Path ([Environment]::GetFolderPath('Programs')) 'Deadlock Toolbox.lnk'; $s=$w.CreateShortcut($p); $s.TargetPath=$env:TOOLBOX_BINARY; $s.WorkingDirectory=$env:TOOLBOX_FOLDER; $s.Save()"
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                       env=dict(os.environ, TOOLBOX_BINARY=str(binary), TOOLBOX_FOLDER=str(binary.parent)), check=True, timeout=30,
                       capture_output=True)
    else:
        from .core import atomic
        applications = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'applications'
        atomic(applications / 'deadlock-toolbox.desktop', desktop_entry(binary).encode('utf-8'))


def install_folder(source, version=__version__, base=None, shortcut=True):
    """Stage a full portable folder, then atomically publish a new install directory."""
    Version.parse(version)
    source = Path(source).resolve()
    if not executable(source).is_file() or not (source / '_internal').is_dir():
        raise ValueError('حزمة التطبيق ناقصة. فك الحزمة كاملة ثم أعد المحاولة.')
    if any(p.is_symlink() and (p.is_dir() or not p.resolve().is_relative_to(source)) for p in source.rglob('*')):
        raise ValueError('الحزمة تحتوي روابط ملفات غير مدعومة.')
    base = Path(base or install_base()).resolve()
    if base.is_relative_to(source):
        raise ValueError('مجلد التثبيت يجب أن يكون خارج حزمة المصدر.')
    base.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.install-', dir=base))
    target = base / (version + '-' + stage.name.removeprefix('.install-'))
    try:
        shutil.copytree(source, stage, dirs_exist_ok=True)
        binary = executable(stage)
        if os.name != 'nt':
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
        stage.rename(target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    binary = executable(target)
    warning = ''
    if shortcut:
        try:
            create_shortcut(binary)
        except (OSError, subprocess.SubprocessError) as error:
            warning = 'تم التثبيت لكن تعذر إنشاء الاختصار. افتح التطبيق من: ' + str(binary)
    return binary, warning


def install_archive(archive, version, expected, base=None, shortcut=True):
    """Recheck the downloaded hash and reject escaping/oversized archive members."""
    archive = Path(archive)
    with archive.open('rb') as stream:
        if not expected or not hmac.compare_digest(hashlib.file_digest(stream, 'sha256').hexdigest(), expected):
            raise ValueError('تغير ملف التنزيل. نزّل التحديث من جديد.')
        stream.seek(0)
        with zipfile.ZipFile(stream) as bundle, tempfile.TemporaryDirectory(prefix='toolbox-update-') as temp:
            entries = bundle.infolist()
            if len(entries) > 20000 or sum(e.file_size for e in entries) > MAX_EXPANDED:
                raise ValueError('حجم الحزمة بعد الفك أكبر من المسموح.')
            seen = set()
            for entry in entries:
                path = PurePosixPath(entry.filename)
                key = path.as_posix().casefold()
                if (not path.parts or path.parts[0] != 'DeadlockToolbox' or '..' in path.parts
                        or '\\' in entry.filename or ':' in entry.filename or key in seen
                        or stat.S_ISLNK(entry.external_attr >> 16)
                        or any(p.endswith(('.', ' ')) for p in path.parts)
                        or any(ord(c) < 32 for c in entry.filename)):
                    raise ValueError('مسارات غير آمنة داخل الحزمة.')
                seen.add(key)
            bundle.extractall(temp)
            return install_folder(Path(temp) / 'DeadlockToolbox', version, base, shortcut)
