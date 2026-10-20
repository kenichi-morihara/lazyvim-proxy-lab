"""Private connection persistence and interactive setup without network calls."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_config', ROOT / 'editor/pi/local_config.py')
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class ConfigTests(unittest.TestCase):
    def test_private_atomic_save_environment_override_and_legacy_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {'HOME': directory}
            data = {'INTERNAL_AI_TRANSPORT': 'openai', 'INTERNAL_AI_API_KEY': 'test-private-token',
                    'INTERNAL_AI_MODEL': 'saved-model', 'HTTPS_PROXY': 'http://proxy.example:8080'}
            path = config.save_config(env, data)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            loaded = config.load_config(dict(env, INTERNAL_AI_MODEL='override'))
            self.assertEqual(loaded['INTERNAL_AI_API_KEY'], 'test-private-token')
            self.assertEqual(loaded['INTERNAL_AI_MODEL'], 'override')
            legacy = config.load_config(dict(env, INTERNAL_AI_TRANSPORT='company-chat'))
            self.assertNotIn('INTERNAL_AI_API_KEY', legacy)
            self.assertEqual(legacy['HTTPS_PROXY'], data['HTTPS_PROXY'])
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                config.read_config(env)

    def test_rejects_symlinks_and_git_repository_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {'HOME': directory}
            target = root / 'secret'
            target.write_text('unchanged')
            target.chmod(0o600)
            path = config.config_path(env)
            path.parent.mkdir(parents=True)
            path.symlink_to(target)
            with self.assertRaises(ValueError):
                config.save_config(env, {})
            self.assertEqual(target.read_text(), 'unchanged')
            (root / '.git').mkdir()
            with self.assertRaises(ValueError):
                config.save_config({'HOME': str(root), 'XDG_CONFIG_HOME': str(root / 'another')}, {})

    def test_config_home_in_dotfiles_uses_private_state_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / 'dotfiles'
            (checkout / '.git').mkdir(parents=True)
            env = {'HOME': str(root / 'home'), 'XDG_CONFIG_HOME': str(checkout / '.config')}
            path = config.save_config(env, {'INTERNAL_AI_MODEL': 'saved-model'})
            self.assertEqual(path, root / 'home/.local/state/editor-pi/connection.json')
            self.assertEqual(config.load_config(dict(env))['INTERNAL_AI_MODEL'], 'saved-model')
            self.assertFalse((checkout / '.config/editor-pi').exists())

    def test_refresh_updates_old_managed_launcher_without_reinstall(self):
        import runpy
        wizard = runpy.run_path(str(ROOT / 'editor/scripts/configure-pi'))
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            command = prefix / 'bin/pi'
            command.parent.mkdir()
            command.write_text('#!/usr/bin/python3\n# proxy-lab managed internal Pi launcher\n# old version\n')
            cli = prefix / 'share/editor-pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'
            cli.parent.mkdir(parents=True)
            cli.write_text('// fixture')
            self.assertTrue(wizard['refresh_runtime'](prefix))
            self.assertIn('load_config', command.read_text())
            self.assertTrue((prefix / 'share/editor-pi/company/local_config.py').is_file())

    def test_wizard_saves_explicit_internal_http_permission(self):
        import runpy
        wizard = runpy.run_path(str(ROOT / 'editor/scripts/configure-pi'))
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'HOME': directory}, clear=True), patch('sys.stdin.isatty', return_value=True), \
                 patch('builtins.input', side_effect=['http://10.0.0.2/v1', 'y', '', 'X-User', '', '']), \
                 patch('getpass.getpass', side_effect=['private-user', 'private-token', '', '']), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wizard['main'](), 0)
            data = config.read_config({'HOME': directory})
            self.assertEqual(data['INTERNAL_AI_ALLOW_HTTP'], '1')
            self.assertEqual(data['INTERNAL_AI_BASE_URL'], 'http://10.0.0.2/v1')
            with patch.dict(os.environ, {'HOME': directory}, clear=True), patch('sys.stdin.isatty', return_value=True), \
                 patch('builtins.input', side_effect=['', '', '', '', '', '']) as prompts, \
                 patch('getpass.getpass', side_effect=['new-user', 'new-token', '', '']), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wizard['main'](), 0)
            data = config.read_config({'HOME': directory})
            self.assertEqual(data['INTERNAL_AI_ALLOW_HTTP'], '1')
            self.assertEqual(data['INTERNAL_AI_USER'], 'new-user')
            self.assertIn('[Y/n]', prompts.call_args_list[1].args[0])


    def test_wizard_saves_user_and_bearer_without_printing_them(self):
        spec = importlib.util.spec_from_loader('configure_pi', __import__('importlib').machinery.SourceFileLoader(
            'configure_pi', str(ROOT / 'editor/scripts/configure-pi')))
        wizard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wizard)
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch.dict(os.environ, {'HOME': directory}, clear=True), patch('sys.stdin.isatty', return_value=True), \
                 patch('builtins.input', side_effect=['https://ai.example/v1', '', 'X-User', '', '']), \
                 patch.object(wizard.getpass, 'getpass', side_effect=['private-user', 'Bearer private-token', '', '']), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(wizard.main(), 0)
            data = config.read_config({'HOME': directory})
            self.assertEqual(data['INTERNAL_AI_API'], 'openai-responses')
            self.assertEqual(data['INTERNAL_AI_USER'], 'private-user')
            self.assertEqual(data['INTERNAL_AI_API_KEY'], 'private-token')
            self.assertNotIn('private-user', output.getvalue())
            self.assertNotIn('private-token', output.getvalue())


if __name__ == '__main__':
    unittest.main()
