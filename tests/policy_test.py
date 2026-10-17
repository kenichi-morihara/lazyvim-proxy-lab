"""Unit tests for the proxy decision function, without installing mitmproxy."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest

sys.modules['mitmproxy'] = types.SimpleNamespace(http=types.SimpleNamespace(HTTPFlow=object), ctx=None)
spec = importlib.util.spec_from_file_location('policy', Path(__file__).resolve().parents[1] / 'lab/proxy/policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

class PolicyTests(unittest.TestCase):
    def test_git(self):
        self.assertTrue(policy.permitted('GET', 'github.com', '/neovim/neovim.git/info/refs?service=git-upload-pack'))
        self.assertTrue(policy.permitted('POST', 'github.com', '/LazyVim/LazyVim/git-upload-pack'))
        self.assertFalse(policy.permitted('POST', 'github.com', '/owner/repo.git/git-receive-pack'))
    def test_downloads_and_unknown_hosts(self):
        for host,path in [('github.com','/neovim/neovim/archive/refs/tags/v0.11.5.tar.gz'),('github.com','/neovim/neovim/releases/download/v0.11.5/nvim-linux-arm64.tar.gz'),('codeload.github.com','/owner/repo/tar.gz/main'),('raw.githubusercontent.com','/owner/repo/main/init.lua'),('api.github.com','/repos/owner/repo/tarball'),('registry.npmjs.org.evil.example','/')]:
            self.assertFalse(policy.permitted('GET',host,path), (host,path))
    def test_registries(self):
        for host in ['registry.npmjs.org','files.pythonhosted.org','pypi.org','dl.rockylinux.org','dl.fedoraproject.org','auth.docker.io']:
            self.assertTrue(policy.permitted('GET',host,'/'))

if __name__ == '__main__': unittest.main()
