"""Mutation spot-check of the mod-store engine. Usage: mutation_store.py <repo root>

Disables safety and logic checks of the mod store (`deadlock_fps/store/`, and the installer, graph and page code the store
install path relies on) one at a time, runs `tests/test_store_*.py`, and reports
whether the tests noticed. The file is restored in a `finally`. A SURVIVED line means a check the tests cannot see:
either the check is redundant, or another one masks it; add a test that isolates it. Result on 2026-11-14: engine 15 of 15
caught; install path 14 of 14 caught (see the vault note "Task - Mod Store install").
"""
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
py = root / '.venv' / 'Scripts' / 'python.exe'
if not py.exists():
    py = Path(sys.executable)
store = root / 'deadlock_fps' / 'store'
gb, cat, syn = store / 'gamebanana.py', store / 'catalog.py', store / 'sync.py'
adapter = store / 'install.py'
app = root / 'deadlock_fps'
engine, archive_py, updates_py = app / 'installer' / 'engine.py', app / 'installer' / 'archive.py', app / 'installer' / 'updates.py'
graph_build, page = app / 'graph' / 'build.py', app / 'pages' / 'browse.py'

MUTATIONS = [
    ('host allow-list removed', gb, "return url if host == 'gamebanana.com' or host.endswith('.gamebanana.com') else ''", 'return url'),
    ('bidi overrides no longer stripped', gb, r"\x7f‪-‮⁦-⁩]')", r"\x7f]')"),
    ('md5 not validated', gb, "md5.lower() if isinstance(md5, str) and _MD5.fullmatch(md5) else ''", "md5 if isinstance(md5, str) else ''"),
    ('profile identity check removed', gb, 'if profile.submission.id != ident:', 'if False:'),
    ('nsfw flag ignored', gb, "nsfw=record.get('_sInitialVisibility') in _HIDDEN_VISIBILITY", 'nsfw=False'),
    ('image extension allow-list widened', gb, '(?:jpe?g|png|webp|gif)', '(?:jpe?g|png|webp|gif|exe)'),
    ('file name path separators kept', gb, ".replace('/', '_').replace('\\\\', '_')", ''),
    ('raw user text sent to FTS', cat, "params.append(' '.join('\"%s\"*' % token for token in tokens))", 'params.append(text)'),
    ('counts overwritten by the index', cat, 'tags=excluded.tags, seen=excluded.seen\'', 'tags=excluded.tags, seen=excluded.seen, likes=excluded.likes\''),
    ('nsfw filter dropped', cat, 'if not include_nsfw:', 'if False:'),
    ('unknown sort reaches SQL', cat, "order = SORTS.get(sort, SORTS['updated'])", 'order = SORTS.get(sort, sort)'),
    ('cursor does not advance', syn, 'crawl_next=page + 1', 'crawl_next=page'),
    ('page-size end test replaced', syn, 'last = result.raw_count < PAGE_SIZE\n            catalog.save_page', 'last = result.raw_count == 0\n            catalog.save_page'),
    ('ordering guard removed', syn, 'ordered = all(a >= b for a, b in zip(stamps, stamps[1:]))', 'ordered = True'),
    ('crawl not paced', syn, '            page += 1\n            self.sleep(self.pause)', '            page += 1'),
]

INSTALL_MUTATIONS = [
    ('md5 check removed', engine, 'if md5_file(part) != package.md5.lower():', 'if False:'),
    ('final-host check removed', engine, 'if package.hosts and not self._on_hosts(result.url, package.hosts):', 'if False:'),
    ('host suffix match loosened', engine, "host.endswith('.' + h)", 'host.endswith(h)'),
    ('no-.vpk check removed', archive_py, "if not wanted:\n                raise InstallError(BAD_PACKAGE, 'the archive contains no .vpk file')", "if False:\n                raise InstallError(BAD_PACKAGE, 'the archive contains no .vpk file')"),
    ('discovery cap removed', archive_py, 'if len(wanted) > MAX_DISCOVERED:', 'if False:'),
    ('adapter drops the host list', adapter, "None, (), file.md5, HOSTS)", "None, (), file.md5, ())"),
    ('adapter drops the md5', adapter, 'None, (), file.md5, HOSTS)', "None, (), '', HOSTS)"),
    ('unsupported files look installable', adapter, "reason = _REASONS[code] if code else ''", "reason = ''"),
    ('zip packages not discovered', adapter, "discover=(kind == 'zip')", 'discover=False'),
    ('store labelled COMMUNITY', adapter, 'Trust.UNVERIFIED, NOTE', 'Trust.COMMUNITY, NOTE'),
    ('store update note removed', updates_py, 'if mod.repository_id.startswith(STORE_PREFIX):', 'if False:'),
    ('graph store branch removed', graph_build, 'if mid not in graph.nodes and key[0].startswith(STORE_PREFIX):', 'if False:'),
    ('page: install offered for any file', page, 'can = bool(kind) and not self.mods.busy', 'can = not self.mods.busy'),
    ('page: game-linked guard removed', page, "        if not self.mods.ready():\n            self.set_result('warning', tr('Link your Deadlock folder on the Home page first.'))\n            return\n", ''),
]
MUTATIONS += INSTALL_MUTATIONS

env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONIOENCODING='utf-8')
command = [str(py), '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_store_*.py']
survivors = []
for label, path, old, new in MUTATIONS:
    original = path.read_bytes()          # bytes in, bytes out: the repository is LF and must stay LF
    text = original.decode('utf-8')
    if old not in text:
        print('PATTERN MISSING  %s (the code changed; update this list)' % label)
        survivors.append(label)
        continue
    try:
        path.write_bytes(text.replace(old, new, 1).encode('utf-8'))
        result = subprocess.run(command, cwd=str(root), env=env, capture_output=True, text=True, timeout=300)
    finally:
        path.write_bytes(original)
    caught = result.returncode != 0
    print('%-9s %s' % ('CAUGHT' if caught else 'SURVIVED', label))
    if not caught:
        survivors.append(label)
print('\nsurvivors:', survivors or 'none')
