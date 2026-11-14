"""VPK validation, hostile ZIP archives, and the streaming download."""
import hashlib
import io
import stat
import struct
import tempfile
import threading
import unittest
import urllib.error
import zipfile
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from deadlock_fps.installer import archive
from deadlock_fps.installer.errors import InstallError
from deadlock_fps.installer.vpk import inspect_vpk, MAGIC
from deadlock_fps.repos.errors import RepoError
from deadlock_fps.repos.transport import UrllibTransport
from installer_fixtures import make_vpk, make_zip
from test_repos_providers import Reply, ScriptedOpener, redirect


class Folder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path


class Vpk(Folder):
    def test_a_valid_vpk_reports_its_files(self):
        info = inspect_vpk(self.write('a.vpk', make_vpk(['materials/shared/skin.vmat', 'models/hero.vmdl_c', 'root.txt'])))
        self.assertEqual(info.paths, frozenset({'materials/shared/skin.vmat', 'models/hero.vmdl_c', 'root.txt'}))
        self.assertEqual((info.version, info.entries), (1, 3))

    def test_a_version_2_header_is_read(self):
        v1 = make_vpk()
        tree_size = struct.unpack_from('<I', v1, 8)[0]
        body = v1[12:]
        v2 = struct.pack('<IIIIIII', MAGIC, 2, tree_size, 0, 0, 0, 0) + body
        self.assertEqual(inspect_vpk(self.write('b.vpk', v2)).entries, 1)

    def test_damaged_or_foreign_files_are_refused(self):
        good = make_vpk()
        tree_size = struct.unpack_from('<I', good, 8)[0]
        cases = {
            'empty': b'', 'short': b'\x34\x12\xaa', 'magic': b'\x00' * 4 + good[4:], 'version': good[:4] + struct.pack('<I', 9) + good[8:],
            'huge tree': good[:8] + struct.pack('<I', 2 ** 30) + good[12:], 'truncated': good[:12 + tree_size - 3],
            'text': b'this is not a package at all, just text', 'cut data': good[:-2],
            'no entries': struct.pack('<III', MAGIC, 1, 3) + b'\0\0\0',
        }
        for label, data in cases.items():
            with self.assertRaises(InstallError, msg=label) as caught:
                inspect_vpk(self.write('x.vpk', data))
            self.assertEqual(caught.exception.code, 'bad-package', label)

    def test_multi_file_vpks_are_refused_with_an_explicit_reason(self):
        tree = b'vmat\0materials\0shared\0' + struct.pack('<IHHIIH', 0, 0, 3, 0, 4, 0xFFFF) + b'\0\0\0'
        data = struct.pack('<III', MAGIC, 1, len(tree)) + tree
        with self.assertRaises(InstallError) as caught:
            inspect_vpk(self.write('pak01_dir.vpk', data))
        self.assertIn('multi-file', caught.exception.message)

    def test_a_bad_entry_terminator_and_invalid_utf8_are_refused(self):
        good = make_vpk()
        bad_terminator = good.replace(struct.pack('<H', 0xFFFF), struct.pack('<H', 0x1234), 1)
        with self.assertRaises(InstallError):
            inspect_vpk(self.write('t.vpk', bad_terminator))
        tree = b'vm\xffat\0materials\0shared\0' + struct.pack('<IHHIIH', 0, 0, 0x7FFF, 0, 4, 0xFFFF) + b'\0\0\0'
        with self.assertRaises(InstallError):
            inspect_vpk(self.write('u.vpk', struct.pack('<III', MAGIC, 1, len(tree)) + tree + b'DATA'))

    def test_missing_files_are_refused_not_crashed(self):
        with self.assertRaises(InstallError):
            inspect_vpk(self.dir / 'nope.vpk')


class Zips(Folder):
    def archive(self, members, extra=None):
        return self.write('p.zip', make_zip(members, extra))

    def test_wanted_members_are_found_and_the_rest_is_ignored_and_flagged(self):
        path = self.archive({'pak/a.vpk': make_vpk(), 'readme.txt': b'hi'}, {'setup.exe': b'MZ', 'tools/run.ps1': b'x'})
        report = archive.inspect_zip(path, ['pak/a.vpk'])
        self.assertEqual(report.members, ('pak/a.vpk',))
        self.assertEqual(sorted(report.ignored), ['readme.txt', 'setup.exe', 'tools/run.ps1'])
        self.assertEqual(sorted(report.risky), ['setup.exe', 'tools/run.ps1'])

    def test_unsafe_names_anywhere_in_the_archive_refuse_the_whole_archive(self):
        for bad in ['../evil.vpk', '/abs.vpk', 'a/../../b.vpk', 'C:/x.vpk', 'dir/./x.vpk', 'trail.', 'sp ace /x.vpk', 'ctl\x01.vpk', 'ads.vpk:stream']:
            path = self.archive({'good.vpk': make_vpk()}, {bad: b'x'})
            with self.assertRaises(InstallError, msg=repr(bad)) as caught:
                archive.inspect_zip(path, ['good.vpk'])
            self.assertEqual(caught.exception.code, 'bad-package')

    def test_symlinks_encrypted_entries_and_case_collisions_are_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('good.vpk', make_vpk())
            link = zipfile.ZipInfo('link.vpk')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(link, 'good.vpk')
        with self.assertRaises(InstallError) as caught:
            archive.inspect_zip(self.write('l.zip', buffer.getvalue()), ['good.vpk'])
        self.assertIn('symbolic link', caught.exception.message)
        flagged = bytearray(make_zip({'good.vpk': make_vpk(), 'secret.vpk': b'x'}))
        at = flagged.index(b'PK\x01\x02')                                           # walk the central directory to secret.vpk
        while bytes(flagged[at + 46:at + 56]) != b'secret.vpk':
            at = flagged.index(b'PK\x01\x02', at + 4)
        flagged[at + 8] |= 0x1                                                      # general-purpose flag: encrypted
        with self.assertRaises(InstallError) as caught:
            archive.inspect_zip(self.write('e.zip', bytes(flagged)), ['good.vpk'])
        self.assertIn('encrypted', caught.exception.message)
        path = self.archive({'Skin.vpk': make_vpk()}, {'skin.VPK': make_vpk()})
        with self.assertRaises(InstallError) as caught:
            archive.inspect_zip(path, ['Skin.vpk'])
        self.assertIn('case', caught.exception.message)

    def test_backslashes_and_other_hostile_spellings_are_unsafe(self):
        # zipfile itself rewrites backslashes on Windows, so these are checked on the predicate directly.
        for bad in ['a\\b.vpk', '..\\x.vpk', 'C:\\x', 'a/b:stream', '/x', '', 'a//b', './x', 'x/..', 'x ', 'x.']:
            self.assertTrue(archive._unsafe_name(bad), repr(bad))
        for good in ['a.vpk', 'pak/a b (1).vpk', 'dir/', 'a-b_c.vpk']:
            self.assertFalse(archive._unsafe_name(good), repr(good))

    def test_missing_directory_and_non_vpk_install_targets_are_refused(self):
        path = self.archive({'a.vpk': make_vpk(), 'dir/x.txt': b'x'})
        for wanted in (['absent.vpk'], ['dir'], ['dir/x.txt']):
            with self.assertRaises(InstallError, msg=str(wanted)):
                archive.inspect_zip(path, wanted)

    def test_limits_on_entries_declared_size_and_ratio(self):
        path = self.archive({'a.vpk': make_vpk(), 'b.txt': b'x', 'c.txt': b'y'})
        with patch.object(archive, 'MAX_ENTRIES', 2), self.assertRaises(InstallError):
            archive.inspect_zip(path, ['a.vpk'])
        with patch.object(archive, 'MAX_DECLARED_TOTAL', 10), self.assertRaises(InstallError):
            archive.inspect_zip(path, ['a.vpk'])
        bomb = self.write('bomb.zip', make_zip({'a.vpk': b'\0' * (3 * 1024 * 1024)}))
        with patch.object(archive, 'RATIO_MIN_SIZE', 1024), patch.object(archive, 'RATIO_LIMIT', 100), self.assertRaises(InstallError) as caught:
            archive.inspect_zip(bomb, ['a.vpk'])
        self.assertIn('zip bomb', caught.exception.message)

    def test_not_a_zip_is_refused(self):
        with self.assertRaises(InstallError):
            archive.inspect_zip(self.write('x.zip', b'PK nonsense'), ['a.vpk'])

    def test_extraction_counts_real_bytes_and_leaves_no_partial_file(self):
        path = self.archive({'a.vpk': b'x' * 5000})
        target = self.dir / 'out.vpk'
        with self.assertRaises(InstallError):
            archive.extract_member(path, 'a.vpk', target, limit=1000)
        self.assertFalse(target.exists())
        self.assertEqual(archive.extract_member(path, 'a.vpk', target), 5000)
        event = threading.Event()
        event.set()
        other = self.dir / 'other.vpk'
        with self.assertRaises(InstallError) as caught:
            archive.extract_member(path, 'a.vpk', other, cancel=event)
        self.assertEqual(caught.exception.code, 'cancelled')
        self.assertFalse(other.exists())


class Streaming(Folder):
    def transport(self, *steps):
        t = UrllibTransport()
        t._opener = ScriptedOpener(*steps)
        return t

    def test_download_streams_hashes_and_reports_progress(self):
        data = b'abcdefgh' * 100000
        seen = []
        result = self.transport(Reply(data, {'Content-Length': str(len(data))})).download('https://f.example.org/a', self.dir / 'a', max_bytes=10 ** 7, expected_size=len(data), progress=lambda a, b: seen.append((a, b)))
        self.assertEqual((result.size, result.sha256), (len(data), hashlib.sha256(data).hexdigest()))
        self.assertEqual((self.dir / 'a').read_bytes(), data)
        self.assertEqual(seen[-1], (len(data), len(data)))

    def test_every_failure_removes_the_partial_file(self):
        def fails(reply, expected=None, max_bytes=10 ** 6, code=None, cancel=None):
            target = self.dir / 'x'
            with self.assertRaises(RepoError) as caught:
                self.transport(reply).download('https://f.example.org/a', target, max_bytes=max_bytes, expected_size=expected, cancel=cancel)
            self.assertFalse(target.exists())
            if code:
                self.assertEqual(caught.exception.code, code)
        fails(Reply(b'x' * 500, {'Content-Length': '500'}), expected=100, code='too-large')          # declared too big
        fails(Reply(b'x' * 500), expected=100, code='too-large')                                     # streamed too big
        fails(Reply(b'x' * 50), expected=100, code='download-failed')                                 # ended short
        fails(Reply(b'x' * 500), max_bytes=100, code='too-large')
        fails(Reply(b''), code='download-failed')
        event = threading.Event()
        event.set()
        fails(Reply(b'x' * 50), cancel=event, code='cancelled')
        not_found = urllib.error.HTTPError('https://f.example.org/a', 404, 'Not Found', Message(), io.BytesIO(b''))
        fails(not_found, code='download-failed')

    def test_redirects_are_validated_for_downloads_too(self):
        t = self.transport(redirect('https://a.example.org/x', 'https://127.0.0.1/secret'))
        with self.assertRaises(RepoError) as caught:
            t.download('https://a.example.org/x', self.dir / 'x', max_bytes=100)
        self.assertEqual(caught.exception.code, 'bad-url')
        self.assertFalse((self.dir / 'x').exists())
        t = self.transport(redirect('https://a.example.org/x', 'https://cdn.example.net/y'), Reply(b'ok!'))
        self.assertEqual(t.download('https://a.example.org/x', self.dir / 'y', max_bytes=100).url, 'https://cdn.example.net/y')

    def test_an_existing_destination_is_never_overwritten(self):
        (self.dir / 'keep').write_bytes(b'precious')
        with self.assertRaises(RepoError):
            self.transport(Reply(b'new')).download('https://f.example.org/a', self.dir / 'keep', max_bytes=100)
        self.assertEqual((self.dir / 'keep').read_bytes(), b'precious')


if __name__ == '__main__':
    unittest.main()
