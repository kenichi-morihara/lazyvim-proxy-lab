"""Exercise the public make interface in an isolated home with fake external tools."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAKE = shutil.which('make')


@unittest.skipUnless(MAKE, 'make is required')
class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='editor install ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo with spaces'
        self.editor = self.repo / 'editor'
        shutil.copytree(ROOT / 'editor', self.editor, ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
        shutil.copy2(ROOT / 'Makefile', self.repo / 'Makefile')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.home = self.root / 'home'
        self.home.mkdir()
        self.log = self.root / 'stages'
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('EDITOR_', 'XDG_', 'NVIM_')) and k not in ('BUILD_JOBS', 'CC', 'CXX', 'COPY', 'MAKEFLAGS', 'MFLAGS')}
        self.env.update(HOME=str(self.home), PATH=str(self.bin), PYTHON=sys.executable,
                        TEST_LOG=str(self.log), EDITOR_PREFIX=str(self.home / '.local'),
                        XDG_CONFIG_HOME=str(self.home / '.config'))
        for name in ('git', 'node', 'npm', 'cc', 'c++', 'make', 'rg', 'fd', 'tar', 'gzip', 'unzip', 'cmake', 'ninja', 'msgfmt'):
            output = 'git version 2.50.0' if name == 'git' else 'v22.0.0' if name == 'node' else ''
            self.tool(name, "printf '%s\\n' '" + output + "'\n")
        for name in ('bash', 'dirname'):
            (self.bin / name).symlink_to(shutil.which(name))
        # Each stub represents a stage, not the internals of package installation.
        # Real config placement is kept so a failed preflight cannot silently overwrite it.
        for stage in ('build-neovim', 'install-language-tools', 'install-plugins', 'install-parsers', 'install-pi'):
            code = '''import os
from pathlib import Path
stage = Path(__file__).name
with open(os.environ['TEST_LOG'], 'a') as log: log.write(stage + '\\n')
if os.environ.get('TEST_FAIL') == stage: raise SystemExit(9)
prefix = Path(os.environ['EDITOR_PREFIX']) / 'bin'
prefix.mkdir(parents=True, exist_ok=True)
'''
            if stage == 'build-neovim':
                code += "p=prefix/'nvim';p.write_text(" + repr(self.nvim_script('0.11.5', True)) + ");p.chmod(0o755)\n"
            if stage == 'install-language-tools':
                code += "\nfor name in ('basedpyright-langserver','vtsls','ruff','prettier'):\n p=prefix/name;p.write_text('#!/bin/sh\\nexit 0\\n');p.chmod(0o755)\n"
            (self.editor / 'tools' / stage).write_text(code)

    def tool(self, name, body):
        p = self.bin / name
        p.write_text('#!/bin/sh\n' + body)
        p.chmod(0o755)

    @staticmethod
    def nvim_script(version, luajit):
        return ("#!/bin/sh\nif [ \"$1\" = --version ]; then\n"
                + f"printf 'NVIM v{version}\\nBuild type: Release\\n{'LuaJIT 2.1' if luajit else 'Lua 5.1'}\\n'\n"
                + "else\nprintf 'verify\\n' >> \"$TEST_LOG\"\nfi\n")

    def test_auto_selects_versioned_python_when_python3_is_too_old(self):
        self.env.pop('PYTHON')
        self.tool('python3', 'exit 1\n')
        (self.bin / 'python3.11').symlink_to(sys.executable)
        result = self.run_make('doctor')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.stages(), [])

    def test_missing_python_reports_requirement_without_writes(self):
        self.env.pop('PYTHON')
        result = self.run_make()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Python 3.11+', result.stdout)
        self.assertEqual(self.stages(), [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_verification_failure_is_not_reported_as_success(self):
        self.nvim()
        path = self.bin / 'nvim'
        path.write_text(path.read_text().replace("else\nprintf", "else\nexit 7\nprintf"))
        result = self.run_make()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ERROR:', result.stdout)
        self.assertNotIn('PASS installation verified', result.stdout)

    def nvim(self, version='0.11.5', luajit=True):
        self.tool('nvim', self.nvim_script(version, luajit).split('\n', 1)[1])

    def run_make(self, *args, standalone=False):
        return subprocess.run([MAKE, *args], cwd=self.editor if standalone else self.repo,
                              env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def stages(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_setup_pi_is_independent_of_editor_preflight(self):
        for name in ('cc', 'c++', 'cmake', 'ninja', 'msgfmt'):
            (self.bin / name).unlink()
        result = self.run_make('setup-pi', standalone=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.stages(), ['install-pi'])
        self.assertFalse((self.home / '.config/nvim').exists())

    def test_setup_pi_failure_reports_the_optional_retry_target(self):
        self.env['TEST_FAIL'] = 'install-pi'
        result = self.run_make('setup-pi')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rerun make setup-pi', result.stdout)
        self.assertEqual(self.stages(), ['install-pi'])

    def test_doctor_rejects_git_too_old_for_diffview(self):
        self.tool('git', "printf 'git version 2.30.9\\n'\n")
        result = self.run_make('doctor')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Git >= 2.31 (Diffview)', result.stdout)
        self.assertEqual(self.stages(), [])

    def test_doctor_allows_missing_neovim_and_language_tools_without_writes(self):
        before = set(self.home.rglob('*'))
        result = self.run_make('doctor')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('PLAN build Neovim 0.11.5', result.stdout)
        self.assertNotIn('MISSING nvim', result.stdout)
        self.assertEqual(self.stages(), [])
        self.assertEqual(before, set(self.home.rglob('*')))

    def test_optional_tailscale_setup_does_not_require_or_install_editor_tools(self):
        for name in ('git', 'node', 'npm', 'cc', 'c++', 'rg', 'fd', 'cmake', 'ninja', 'msgfmt'):
            (self.bin / name).unlink()
        self.tool('tailscale', 'exit 0\n')
        self.tool('tailscaled', 'exit 0\n')
        (self.editor / 'scripts/tailscale-local').write_text('''import os, sys
with open(os.environ['TEST_LOG'], 'a') as log: log.write(' '.join(sys.argv[1:]) + '\\n')
''')
        for standalone in (False, True):
            with self.subTest(standalone=standalone):
                if self.log.exists(): self.log.unlink()
                result = self.run_make('setup-tailscale', standalone=standalone)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(self.stages(), ['start', 'up --accept-dns=false'])
                self.assertEqual(list(self.home.iterdir()), [])

    def test_optional_tailscale_setup_reports_missing_package_without_editor_changes(self):
        result = self.run_make('setup-tailscale')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('tailscale, tailscaled', result.stdout)
        self.assertIn('rerun make setup-tailscale', result.stdout)
        self.assertEqual(self.stages(), [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_missing_prerequisite_stops_before_config_or_helpers(self):
        (self.bin / 'npm').unlink()
        config = self.home / '.config/nvim'
        config.mkdir(parents=True)
        (config / 'keep.lua').write_text('unchanged')
        result = self.run_make()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('MISSING npm', result.stdout)
        self.assertEqual(self.stages(), [])
        self.assertEqual((config / 'keep.lua').read_text(), 'unchanged')
        self.assertEqual(len(list(config.parent.iterdir())), 1)

    def test_default_make_reuses_compatible_neovim_and_verifies(self):
        self.nvim()
        for name in ('cmake','ninja','msgfmt'):
            (self.bin / name).unlink()
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('PLAN reuse Neovim', result.stdout)
        self.assertEqual(self.stages(), ['install-language-tools','install-plugins','install-parsers','verify'])
        self.assertTrue((self.home / '.config/nvim').is_symlink())

    def test_default_make_builds_without_neovim(self):
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.stages(), ['build-neovim','install-language-tools','install-plugins','install-parsers','verify'])

    def test_other_version_or_without_luajit_is_not_reused(self):
        for version, luajit in [('0.11.6', True), ('0.11.5', False)]:
            with self.subTest(version=version, luajit=luajit):
                installed = self.home / '.local/bin/nvim'
                if installed.exists(): installed.unlink()
                if self.log.exists(): self.log.unlink()
                self.nvim(version, luajit)
                result = self.run_make()
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(self.stages()[0], 'build-neovim')

    def test_old_node_is_reported_before_any_install(self):
        self.tool('node', "printf 'v18.0.0\\n'\n")
        result = self.run_make()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Node.js >= 22', result.stdout)
        self.assertEqual(self.stages(), [])

    def test_invalid_jobs_fails_without_writes(self):
        result = self.run_make('BUILD_JOBS=0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BUILD_JOBS must be a positive integer', result.stdout)
        self.assertEqual(self.stages(), [])

    def test_failed_stage_can_be_retried_without_duplicate_config_backups(self):
        self.nvim()
        self.env['TEST_FAIL'] = 'install-plugins'
        first = self.run_make()
        self.assertNotEqual(first.returncode, 0)
        self.assertNotIn('install-parsers', self.stages())
        self.assertNotIn('verify', self.stages())
        self.env.pop('TEST_FAIL')
        second = self.run_make()
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(self.stages()[-1], 'verify')
        self.assertEqual(list((self.home / '.config').glob('nvim.backup-*')), [])

    def test_standalone_editor_and_copy_option(self):
        self.nvim()
        result = self.run_make('COPY=1', standalone=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        config = self.home / '.config/nvim'
        self.assertFalse(config.is_symlink())
        self.assertTrue((config / 'init.lua').exists())
        second = self.run_make('COPY=1', standalone=True)
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(list(config.parent.glob('nvim.backup-*')), [])


if __name__ == '__main__': unittest.main()
