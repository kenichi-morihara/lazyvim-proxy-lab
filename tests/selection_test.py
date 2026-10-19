"""Drive real Insert/Select mode and mouse input using Neovim's local RPC client."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

NVIM = shutil.which('nvim')
EDITOR = Path(__file__).resolve().parents[1] / 'editor/nvim'


@unittest.skipUnless(NVIM, 'Neovim is required for selection integration tests')
class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='editor-select-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.socket = str(Path(self.temp.name) / 'nvim.sock')
        init = Path(self.temp.name) / 'init.lua'
        init.write_text('''vim.g.mapleader = " "
dofile(vim.env.EDITOR_SELECTION_CONFIG .. "/lua/config/options.lua")
dofile(vim.env.EDITOR_SELECTION_CONFIG .. "/lua/config/keymaps.lua")
-- Capture the actual clipboard escape instead of writing to a host clipboard.
vim.api.nvim_chan_send = function(_, data)
  local encoded = data:match("^\\027%]52;c;([%w+/=]*)\\027\\\\$")
  if encoded then vim.g.selection_copied = vim.base64.decode(encoded) end
end
vim.g.selection_ready = true
''')
        self.process = subprocess.Popen(
            [NVIM, '--headless', '--noplugin', '-u', str(init), '--listen', self.socket],
            env=dict(os.environ, XDG_CONFIG_HOME=self.temp.name + '/config', EDITOR_SELECTION_CONFIG=str(EDITOR)),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.close_editor)
        deadline = time.monotonic() + 3
        while not Path(self.socket).exists() and time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.fail(self.process.stderr.read().decode())
            time.sleep(0.01)
        self.assertEqual(self.query("get(g:, 'selection_ready', v:false)"), 'true')

    def close_editor(self):
        if self.process.poll() is None:
            try:
                self.send('<Esc>:qa!<CR>')
                self.process.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                self.process.terminate()
                self.process.wait(timeout=2)
        self.process.stdout.close()
        self.process.stderr.close()

    def query(self, expression):
        result = subprocess.run([NVIM, '--server', self.socket, '--remote-expr', expression],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def send(self, keys):
        subprocess.run([NVIM, '--server', self.socket, '--remote-send', keys],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=3)

    def test_shift_selection_copy_and_type_to_replace_from_insert_mode(self):
        self.query("nvim_buf_set_lines(0,0,-1,v:false,['hello'])")
        self.send('A<S-Left><S-Left>')
        self.assertEqual(self.query('mode(1)'), 's')
        self.send('<C-c>')
        self.assertEqual(self.query("get(g:, 'selection_copied', '')"), 'lo')
        self.assertEqual(self.query('mode(1)'), 's')
        self.send('X<Esc>')
        self.assertEqual(self.query('getline(1)'), 'helX')

    def test_mouse_selection_copy_and_type_to_replace_from_insert_mode(self):
        self.query("nvim_buf_set_lines(0,0,-1,v:false,['hello world'])")
        self.query("execute('set nonumber norelativenumber signcolumn=no foldcolumn=0')")
        self.send('A')
        self.assertEqual(self.query('mode(1)'), 'i')
        self.query("execute('redraw')")
        for action, column in [('press', 0), ('drag', 4), ('release', 4)]:
            code = f"vim.api.nvim_input_mouse('left', '{action}', '', 0, 0, {column})"
            # Vim strings escape quotes by doubling them; no shell is involved.
            self.query("luaeval('" + code.replace("'", "''") + "')")
        self.assertEqual(self.query('mode(1)'), 's')
        self.send('<C-c>')
        self.assertEqual(self.query("get(g:, 'selection_copied', '')"), 'hello')
        self.send('Z<Esc>')
        self.assertEqual(self.query('getline(1)'), 'Z world')


if __name__ == '__main__':
    unittest.main()
