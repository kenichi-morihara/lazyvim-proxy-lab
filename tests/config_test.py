"""Exercise backups and standalone relocation with a temporary HOME."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

EDITOR = Path(__file__).resolve().parents[1] / 'editor'
class ConfigTests(unittest.TestCase):
    def test_standalone_link_copy_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'dotfiles/editor'
            shutil.copytree(EDITOR, source, ignore=shutil.ignore_patterns('__pycache__'))
            config = root / 'config'
            old = config / 'nvim'
            old.mkdir(parents=True)
            (old/'old.lua').write_text('-- keep me')
            env = dict(os.environ, XDG_CONFIG_HOME=str(config), NVIM_APPNAME='nvim')
            command = [str(source/'scripts/install-config')]
            subprocess.run(command, env=env, check=True)
            self.assertTrue(old.is_symlink())
            self.assertEqual((list(config.glob('nvim.backup-*'))[0]/'old.lua').read_text(), '-- keep me')
            subprocess.run(command, env=env, check=True)
            self.assertEqual(len(list(config.glob('nvim.backup-*'))),1)
            subprocess.run(command+['--copy'], env=env, check=True)
            self.assertFalse(old.is_symlink())
            backups = len(list(config.glob('nvim.backup-*')))
            subprocess.run(command+['--copy'], env=env, check=True)
            self.assertEqual(len(list(config.glob('nvim.backup-*'))), backups)
            self.assertEqual((old/'init.lua').read_text(), (source/'nvim/init.lua').read_text())
            shutil.rmtree(source)
            self.assertTrue((old/'lazy-lock.json').exists())
            for p in old.rglob('*.lua'):
                self.assertNotIn('/workspace',p.read_text())
                self.assertNotIn('172.30.',p.read_text())

if __name__ == '__main__': unittest.main()
