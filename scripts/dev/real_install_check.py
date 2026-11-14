"""Install ONE real GameBanana mod through the real install path, inside a THROWAWAY game folder.
Usage: real_install_check.py <repo root> <new empty work folder>

This downloads a file (the default is mod 711387, file 1801337, `pak52_dir_3154a.zip`, 7 493 240 bytes), so ask the user
first and name the file. The work folder must not exist yet; the game folder is created inside it from the reference
`gameinfo.gi`. A real Deadlock folder is never involved. It prints what the engine found (archive members, hashes, plan,
warnings), installs, runs the analysis, uninstalls, and shows what is left. Run it with `python -I`. Delete the work
folder afterwards.

Result on 2026-11-14 (with the user's approval): downloaded in 19 s, MD5 matched, the zip held one VPK (`pak52_dir.vpk`,
28 612 194 bytes, 150 entries), the game folder stayed untouched until commit, the analysis found no problems, and the
uninstall moved the file to the recovery folder. The first attempt failed before any download: the version built from the
upload date (2026-08-29) had a leading zero, which the version rules refuse; fixed and covered by a test.
"""
import hashlib
import sys
import time
from pathlib import Path
from unittest.mock import patch

root, workdir = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(root))

from deadlock_fps.core import ASSETS
from deadlock_fps.installer import Installer
from deadlock_fps.installer import archive
from deadlock_fps.repos import UrllibTransport
from deadlock_fps.store import GameBananaClient
from deadlock_fps.store.install import build, STORE_ID

MOD_ID, FILE_ID = 711387, 1801337
workdir.mkdir(parents=True, exist_ok=False)          # a new, empty folder: nothing of the user's is involved
game = workdir / 'Deadlock'
gameinfo = game / 'game/citadel/gameinfo.gi'
gameinfo.parent.mkdir(parents=True)
reference = (ASSETS / 'reference/gameinfo.gi').read_text(encoding='utf-8').replace('            Game          "citadel/addons"\n', '')
gameinfo.write_text(reference, encoding='utf-8')
original = gameinfo.read_bytes()

transport = UrllibTransport(user_agent='DeadlockToolbox-ModStore')
profile = GameBananaClient(transport).profile(MOD_ID)
file = next(f for f in profile.files if f.id == FILE_ID)
print('PROFILE  %r by %s | file %s | %d bytes | MD5 %s | scan clean: %s' % (profile.submission.name, profile.submission.author, file.name, file.size, file.md5, file.av_clean))

real_inspect = archive.inspect_zip


def spy(path, wanted, discover=False):
    report = real_inspect(path, wanted, discover=discover)
    print('ZIP      installable .vpk members: %s' % (list(report.members),))
    print('ZIP      other files ignored (%d): %s' % (len(report.ignored), list(report.ignored)[:12]))
    print('ZIP      risky (never installed): %s' % (list(report.risky),))
    return report


last = [0.0]


def progress(done, total):
    if time.time() - last[0] > 1 or done == total:
        last[0] = time.time()
        print('DOWNLOAD %d of %d bytes' % (done, total), flush=True)


with patch('deadlock_fps.core.ensure_closed'), patch.object(archive, 'inspect_zip', spy):
    installer = Installer(game, transport)
    repository, mod, version = build(profile, file)
    started = time.time()
    plan = installer.prepare(repository, mod, version, progress=progress)
    print('PREPARED in %.1fs | size %d | sha256 %s' % (time.time() - started, plan.package_size, plan.actual_sha256))
    print('PLAN     md5_verified=%s sha256_verified=%s requires_ack=%s trust=%s blockers=%s' % (plan.md5_verified, plan.verified, plan.requires_ack, plan.trust, list(plan.blockers)))
    for f in plan.files:
        print('PLAN     file %s <- %r | %d bytes | %d entries inside' % (f.name, f.source, f.size, f.entries))
    for w in plan.warnings:
        print('WARNING  %s' % w)
    print('GAME     untouched after prepare: %s' % (gameinfo.read_bytes() == original and not (game / 'game/citadel/addons').exists()))
    installed = installer.commit(plan, acknowledged=True)
    addons = sorted(p.name for p in (game / 'game/citadel/addons').glob('*'))
    print('INSTALLED %s v%s -> %s | trust %s | package_url %s' % (installed.name, installed.version, addons, installed.trust, installed.package_url))
    for name in addons:
        path = game / 'game/citadel/addons' / name
        print('INSTALLED %s %d bytes sha256 %s' % (name, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()))
    print('GAMEINFO addons path added: %s' % ('citadel/addons' in gameinfo.read_text(encoding='utf-8')))
    problems = [(i.severity, i.code, i.subject) for i in installer.analyze() if i.severity in ('error', 'warning')]
    print('ANALYZE  problems after install: %s' % (problems or 'none'))
    installer.uninstall(STORE_ID, mod.id)
    after = sorted(p.name for p in (game / 'game/citadel/addons').glob('*'))
    trash = sorted(p.name for p in (installer.store_dir / 'trash').rglob('*.vpk'))
    print('UNINSTALL addons now %s | recovery folder holds %s | installed records: %d' % (after, trash, len(installer.installed())))
print('DONE')
