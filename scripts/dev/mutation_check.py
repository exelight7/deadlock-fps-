import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
pattern = sys.argv[2]
mutations = [
    ('deadlock_fps/installer/engine.py', r"if result\.sha256 != package\.sha256:", "if False:", 'published SHA-256 no longer compared'),
    ('deadlock_fps/installer/engine.py', r"if plan\.requires_ack and not acknowledged:", "if False:", 'acknowledgement not enforced'),
    ('deadlock_fps/installer/engine.py', r"if not target\.is_file\(\) or target\.stat\(\)\.st_size != planned\.size or sha256_file\(target\) != planned\.sha256:", "if False:", 'post-install verification skipped'),
    ('deadlock_fps/installer/engine.py', r"if dst\.exists\(\):\n                    raise InstallError\(STALE, 'refusing to overwrite %s' % dst\.name\)", "pass", 'moves may overwrite'),
    ('deadlock_fps/installer/engine.py', r"if sha256_file\(staged\) != planned\.sha256:|or sha256_file\(staged\) != planned\.sha256:", "or False:", 'staged files not rechecked'),
    ('deadlock_fps/installer/archive.py', r"if _unsafe_name\(entry\.filename\):", "if False:", 'unsafe archive names allowed'),
    ('deadlock_fps/installer/vpk.py', r"if archive != EXTERNAL:", "if False:", 'multi-file VPK allowed'),
    ('deadlock_fps/installer/vpk.py', r"if data_start \+ start \+ length > file_size:", "if False:", 'VPK data bounds unchecked'),
]
for path, old, new, label in mutations:
    file = root / path
    original = file.read_bytes().decode('utf-8')
    changed, count = re.subn(old, new, original, count=1)
    if count != 1:
        print('SKIP (pattern not found): ' + label)
        continue
    file.write_bytes(changed.encode('utf-8'))
    try:
        run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern], cwd=root, capture_output=True, text=True, encoding='utf-8')
        print(('CAUGHT ' if run.returncode else 'MISSED ') + label + ' -> ' + run.stderr.strip().splitlines()[-1])
    finally:
        file.write_bytes(original.encode('utf-8'))
