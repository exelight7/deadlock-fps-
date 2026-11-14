"""Mutation spot-check of the performance feature. Usage: mutation_perf.py <repo root>

Disables checks of the "What does this level change?" feature one at a time (the skip mechanism in settings.py, the
explanations and facts in perf/, the window, and its place in the main window), runs `tests/test_perf.py`, and reports
whether the tests noticed. Each file is restored in a `finally`; do not run other work in the tree while it runs.
A SURVIVED line is a check the tests cannot see. Result on 2026-11-14: see the vault note "Task - Performance Details".
"""
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
py = root / '.venv' / 'Scripts' / 'python.exe'
if not py.exists():
    py = Path(sys.executable)
app = root / 'deadlock_fps'
settings_py, facts_py, knowledge_py, explain_py = app / 'settings.py', app / 'perf' / 'facts.py', app / 'perf' / 'knowledge.py', app / 'perf' / 'explain.py'
window_py = ui_py = app / 'pages' / 'performance.py'

MUTATIONS = [
    ('skip is never applied by values()', settings_py, '    if s.skip:   # settings the user chose', '    if False:   # settings the user chose'),
    ('the video.txt twin is not removed', settings_py, "video={k:v for k,v in video.items() if k.removeprefix('setting.') not in left_out}", "video={k:v for k,v in video.items() if k not in left_out}"),
    ('scene keys are not removed', settings_py, "scene={k:v for k,v in scene.items() if k not in left_out}", "scene=scene"),
    ('protected settings can be skipped', settings_py, 'or n in PROTECTED_SKIP for n in self.skip', 'for n in self.skip'),
    ('skip names are not checked for characters', settings_py, "or not n.replace('_','').isalnum()", ''),
    ('skip list is not capped', settings_py, 'len(self.skip)>200 or ', ''),
    ('a saved skip list comes back as a list', settings_py, "tuple(data['skip']) if isinstance(data['skip'],(list,tuple)) else data['skip']", "data['skip']"),
    ('cheat-only counts as ignored', knowledge_py, "IGNORED = (REMOVED, BLOCKED)", "IGNORED = (REMOVED, BLOCKED, CHEAT)"),
    ('protected settings list shrinks', knowledge_py, "PROTECTED = frozenset({'fps_max', 'fps_max_ui', 'r_aspectratio'})", "PROTECTED = frozenset({'fps_max'})"),
    ('a fact is wrong (r_shadows)', facts_py, "'r_shadows': ('blocked',", "'r_shadows': ('active',"),
    ('a fact is wrong (fog_enableskybox since)', facts_py, "'fog_enableskybox': ('removed', 6728,", "'fog_enableskybox': ('removed', 6000,"),
    ('the report forgets what was left out', explain_py, "left_out=len(items) - len(live))", "left_out=0)"),
    ('left-out items drop out of the list', explain_py, "items = [Item(name, value, where, _entry(name), name in left_out) for name, (value, where) in found.items()]",
     "items = [Item(name, value, where, _entry(name), name in left_out) for name, (value, where) in found.items() if name not in left_out]"),
    ('page lets protected rows be unticked', window_py, '                box.setChecked(True)\n                box.setEnabled(False)', '                box.setChecked(True)\n                box.setEnabled(True)'),
    ('page returns protected names as left out', window_py, 'if not item.entry.protected and not box.isChecked()', 'if not box.isChecked()'),
    ('page button does not reset to everything', window_py, 'self.set_all(set())', 'pass'),
    ('main window forgets the choice when building settings', ui_py, 'mods=tuple(k for k,b in self.mod_checks.items() if b.isChecked()),skip=tuple(self.skip))', 'mods=tuple(k for k,b in self.mod_checks.items() if b.isChecked()))'),
    ('main window ignores the choice when loading settings', ui_py, 'self.skip=tuple(s.skip);self.refresh_perf_button()', 'pass'),
    ('main window keeps the choice after cancel -> accepts always', ui_py, 'if dialog.exec()==QDialog.Accepted:self.skip=dialog.skip()', 'if True:self.skip=dialog.skip()'),
]

env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONIOENCODING='utf-8')
command = [str(py), '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_perf.py']
survivors = []
for label, path, old, new in MUTATIONS:
    original = path.read_bytes()          # bytes in, bytes out: the repository is LF and must stay LF
    text = original.decode('utf-8')
    if text.count(old) != 1:
        print('PATTERN PROBLEM (%d matches)  %s' % (text.count(old), label))
        survivors.append(label)
        continue
    try:
        path.write_bytes(text.replace(old, new, 1).encode('utf-8'))
        result = subprocess.run(command, cwd=str(root), env=env, capture_output=True, text=True, timeout=300)
    finally:
        path.write_bytes(original)
    caught = result.returncode != 0
    print('%-9s %s' % ('CAUGHT' if caught else 'SURVIVED', label), flush=True)
    if not caught:
        survivors.append(label)
print('\nsurvivors:', survivors or 'none')
