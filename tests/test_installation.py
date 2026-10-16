import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from deadlock_fps.installation import install_archive, install_folder, executable, desktop_entry


class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'portable'
        (self.source / '_internal').mkdir(parents=True)
        executable(self.source).write_bytes(b'program')
        (self.source / '_internal/resource').write_bytes(b'resource')

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, extra=None):
        archive = self.root / 'package.zip'
        with zipfile.ZipFile(archive, 'w') as bundle:
            for path in self.source.rglob('*'):
                bundle.write(path, 'DeadlockToolbox/' + path.relative_to(self.source).as_posix())
            if extra:
                bundle.writestr(*extra)
        return archive, hashlib.sha256(archive.read_bytes()).hexdigest()

    def test_full_install_retains_previous_and_does_not_change_source(self):
        base = self.root / 'installed'
        old, _ = install_folder(self.source, '2.4.0', base, False)
        executable(self.source).write_bytes(b'new program')
        new, _ = install_folder(self.source, '2.5.0', base, False)
        self.assertEqual(old.read_bytes(), b'program')
        self.assertEqual(new.read_bytes(), b'new program')
        self.assertEqual((new.parent / '_internal/resource').read_bytes(), b'resource')
        self.assertFalse(list(base.glob('.install-*')))
        if os.name != 'nt':self.assertTrue(new.stat().st_mode & stat.S_IXUSR)

    def test_zip_install_verifies_again_and_restores_executable_permission(self):
        archive, digest = self.archive()
        binary, _ = install_archive(archive, 'v2.5.0', digest, self.root / 'installed', False)
        self.assertEqual(binary.read_bytes(), b'program')
        archive.write_bytes(b'tampered')
        with self.assertRaises(ValueError):install_archive(archive, 'v2.5.0', digest, self.root / 'installed', False)
        self.assertEqual(binary.read_bytes(), b'program')

    def test_escaping_duplicate_and_symlink_zip_entries_rejected(self):
        for name in ['../outside', 'DeadlockToolbox/../../outside', 'DeadlockToolbox/..\\outside', '/outside',
                     'DeadlockToolbox/C:/outside', 'DeadlockToolbox/_internal/../outside',
                     'DeadlockToolbox/_internal/resource', 'DeadlockToolbox/unsafe. /file']:
            with self.subTest(name=name):
                archive, digest = self.archive((name, b'unsafe'))
                with self.assertRaises(ValueError):install_archive(archive, '2.5.0', digest, self.root / 'installed', False)
        info = zipfile.ZipInfo('DeadlockToolbox/link');info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive, digest = self.archive((info, b'../../outside'))
        with self.assertRaises(ValueError):install_archive(archive, '2.5.0', digest, self.root / 'installed', False)
        self.assertFalse((self.root / 'outside').exists())

    def test_failed_staging_keeps_old_install_and_cleans_partial(self):
        base = self.root / 'installed'
        old, _ = install_folder(self.source, '2.4.0', base, False)
        with patch('deadlock_fps.installation.shutil.copytree', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):install_folder(self.source, '2.5.0', base, False)
        self.assertEqual(old.read_bytes(), b'program')
        self.assertFalse(list(base.glob('.install-*')))

    def test_shortcut_failure_still_returns_valid_install(self):
        with patch('deadlock_fps.installation.create_shortcut', side_effect=OSError('denied')):
            binary, warning = install_folder(self.source, '2.5.0', self.root / 'installed')
        self.assertTrue(binary.is_file());self.assertTrue(warning)

    def test_linux_shortcut_uses_per_user_menu_and_quotes_paths(self):
        if os.name == 'nt':self.skipTest('Linux desktop file')
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root / 'user data')}):
            binary, warning = install_folder(self.source, '2.5.0', self.root / 'installed files')
            shortcut = self.root / 'user data/applications/deadlock-toolbox.desktop'
            self.assertEqual(shortcut.read_text(), desktop_entry(binary));self.assertFalse(warning)

    def test_incomplete_and_nested_source_are_rejected(self):
        with self.assertRaises(ValueError):install_folder(self.source, '2.5.0', self.source / 'nested', False)
        executable(self.source).unlink()
        with self.assertRaises(ValueError):install_folder(self.source, '2.5.0', self.root / 'installed', False)
