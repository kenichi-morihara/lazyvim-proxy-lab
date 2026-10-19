"""Exercise rootless daemon startup/dispatch with a local fake CLI and Unix socket."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "editor/scripts/tailscale-local"


class TailscaleTests(unittest.TestCase):
    def setUp(self):
        # macOS's default temp path can exceed the Unix socket path limit.
        self.temp = tempfile.TemporaryDirectory(prefix="editor tailscale ", dir="/tmp")
        self.root = Path(self.temp.name).resolve()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.state = self.root / "private state"
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("EDITOR_TAILSCALE_")}
        self.env.update(PATH=str(self.bin), EDITOR_TAILSCALE_STATE_DIR=str(self.state),
                        TEST_DAEMON_ARGS=str(self.root / "daemon.json"), TEST_CLI_ARGS=str(self.root / "cli.json"),
                        TEST_DAEMON_PID=str(self.root / "daemon.pid"))
        self.tool("tailscale", '''import json, os, sys
from pathlib import Path
socket = sys.argv[1].split('=', 1)[1]
if sys.argv[2:] == ['status', '--json']:
    if Path(socket).exists():
        print(json.dumps({'BackendState': 'NeedsLogin'}))
    raise SystemExit(1)
Path(os.environ['TEST_CLI_ARGS']).write_text(json.dumps(sys.argv[1:]))
print('CLI output')
''')
        self.tool("tailscaled", '''import json, os, signal, socket, sys, time
from pathlib import Path
Path(os.environ['TEST_DAEMON_ARGS']).write_text(json.dumps(sys.argv[1:]))
Path(os.environ['TEST_DAEMON_PID']).write_text(str(os.getpid()))
args = dict(arg.split('=', 1) for arg in sys.argv[1:] if '=' in arg)
Path(args['--state']).write_text('fixture state')
server = socket.socket(socket.AF_UNIX)
server.bind(args['--socket'])
server.listen()
signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
while True: time.sleep(1)
''')

    def tearDown(self):
        pid = self.root / "daemon.pid"
        if pid.exists():
            try:
                os.kill(int(pid.read_text()), signal.SIGTERM)
            except ProcessLookupError:
                pass
        self.temp.cleanup()

    def tool(self, name, source):
        path = self.bin / name
        path.write_text("#!" + sys.executable + "\n" + source)
        path.chmod(0o700)

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)

    def test_start_is_private_rootless_and_reusable_before_login(self):
        result = self.run_script("start")
        self.assertEqual(result.returncode, 0, result.stdout)
        args = json.loads((self.root / "daemon.json").read_text())
        self.assertIn("--tun=userspace-networking", args)
        self.assertIn("--port=0", args)
        self.assertIn("--socket=" + str(self.state / "tailscaled.sock"), args)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.state / "tailscaled.log").stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.state / "tailscaled.state").stat().st_mode & 0o777, 0o600)
        pid = (self.root / "daemon.pid").read_text()
        repeated = self.run_script("start")
        self.assertEqual(repeated.returncode, 0, repeated.stdout)
        self.assertIn("Reusing", repeated.stdout)
        self.assertEqual((self.root / "daemon.pid").read_text(), pid)

    def test_cli_arguments_and_socket_are_forwarded_without_shell(self):
        result = self.run_script("file", "cp", "/tmp/report with spaces.json", "my-mac:")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("CLI output", result.stdout)
        self.assertEqual(json.loads((self.root / "cli.json").read_text()),
                         ["--socket=" + str(self.state / "tailscaled.sock"), "file", "cp",
                          "/tmp/report with spaces.json", "my-mac:"])

    def test_missing_cli_does_not_create_state(self):
        (self.bin / "tailscale").unlink()
        result = self.run_script("start")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not on PATH", result.stdout)
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
