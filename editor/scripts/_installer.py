"""One entry point for read-only preflight and resumable user-local installation."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

EDITOR = Path(__file__).resolve().parent.parent


class Installer:
    def __init__(self):
        self.versions = json.loads((EDITOR / "tools/versions.json").read_text())
        self.version = self.versions["neovim"]["version"]
        self.env = dict(os.environ)
        self.prefix = Path(self.env.get("EDITOR_PREFIX") or Path.home() / ".local").expanduser().resolve()
        self.env["EDITOR_PREFIX"] = str(self.prefix)
        self.env["PYTHON"] = sys.executable
        self.env["PATH"] = str(self.prefix / "bin") + os.pathsep + self.env.get("PATH", "")
        self.build_neovim = True

    def executable(self, name):
        return shutil.which(name, path=self.env["PATH"])

    def output(self, *command):
        try:
            result = subprocess.run(command, env=self.env, check=False, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            return result.stdout if result.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""

    def compatible_neovim(self):
        nvim = self.executable("nvim")
        if not nvim:
            return False
        output = self.output(nvim, "--version")
        version = re.search(r"^NVIM v(\d+\.\d+\.\d+)$", output, re.MULTILINE)
        return bool(version and version[1] == self.version and "LuaJIT" in output)

    def preflight(self):
        print("Checking prerequisites (no installation or network requests)", flush=True)
        missing = []
        jobs = self.env.get("BUILD_JOBS", "2")
        if not jobs.isdigit() or int(jobs) < 1:
            missing.append("BUILD_JOBS must be a positive integer")
        for module in ("venv", "ensurepip"):
            if importlib.util.find_spec(module) is None:
                missing.append("Python " + module)
        print("OK Python " + sys.version.split()[0])
        self.build_neovim = not self.compatible_neovim()
        if self.build_neovim:
            print(f"PLAN build Neovim {self.version} (LuaJIT) into {self.prefix}")
        else:
            print(f"PLAN reuse Neovim {self.version} (LuaJIT): {self.executable('nvim')}")
        required = ["git", "node", "npm", self.env.get("CC", "cc"), self.env.get("CXX", "c++"),
                    "make", "rg", "fd", "tar", "gzip", "unzip"]
        if self.build_neovim:
            required += ["cmake", "ninja", "msgfmt"]
        for name in dict.fromkeys(required):
            path = self.executable(name)
            if path:
                print(f"OK {name}: {path}")
            else:
                missing.append(name)
        if self.executable("git"):
            version = re.search(r"git version (\d+)\.(\d+)", self.output("git", "--version"))
            if not version or tuple(map(int, version.groups())) < (2, 19):
                missing.append("Git >= 2.19")
        if self.executable("node"):
            version = re.match(r"v(\d+)", self.output("node", "--version").strip())
            if not version or int(version[1]) < 22:
                missing.append("Node.js >= 22 (22 is the tested version)")
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
                    "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS", "PIP_CERT"):
            print(f"{key}={'set' if self.env.get(key) else 'unset'}")
        if missing:
            for item in missing:
                print("MISSING " + item, file=sys.stderr)
            print("Provide the missing prerequisites using this environment's package configuration, then rerun make.\n"
                  "No configuration or development tools were installed.", file=sys.stderr)
            return False
        print("PASS prerequisites; Neovim and language tools need not be installed yet.", flush=True)
        return True

    def run_helper(self, relative, *args):
        print("\n== " + relative + " ==", flush=True)
        subprocess.run([sys.executable, str(EDITOR / relative), *args], env=self.env, check=True)

    def verify(self):
        if not self.compatible_neovim():
            raise RuntimeError(f"Neovim {self.version} with LuaJIT is not available")
        required = ("pyright-langserver", "vtsls", "ruff", "prettier")
        missing = [name for name in required if not self.executable(name)]
        if missing:
            raise RuntimeError("Installed tools are missing: " + ", ".join(missing))
        env = dict(self.env, EDITOR_VERIFY_SCRIPT=str(EDITOR / "scripts/_verify.lua"))
        script = ("lua local ok,err=pcall(dofile,vim.env.EDITOR_VERIFY_SCRIPT); "
                  "if not ok then io.stderr:write(tostring(err)..'\\n'); vim.cmd('cquit 1') end")
        subprocess.run([self.executable("nvim"), "--headless", "+" + script],
                       env=env, check=True, timeout=60)
        print("PASS installation verified", flush=True)
        print(f"Use nvim from a project directory. For new shells, add {self.prefix / 'bin'} to PATH.")

    def install(self, copy=False):
        if not self.preflight():
            return 1
        if self.build_neovim:
            self.run_helper("tools/build-neovim")
        self.run_helper("scripts/install-config", *(["--copy"] if copy else []))
        self.run_helper("tools/install-language-tools")
        self.run_helper("tools/install-plugins")
        self.run_helper("tools/install-parsers")
        self.verify()
        return 0


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    install = subparsers.add_parser("install")
    install.add_argument("--copy", action="store_true")
    args = parser.parse_args()
    installer = Installer()
    try:
        if args.command == "doctor":
            return 0 if installer.preflight() else 1
        return installer.install(args.copy)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}\nFix the reported issue and rerun make; completed stages and caches can be reused.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
