"""Shared, lab-independent paths and pinned Git checkout helper."""
import json
import os
from pathlib import Path
import subprocess
import time

TOOLS = Path(__file__).resolve().parent
EDITOR = TOOLS.parent
VERSIONS = json.loads((TOOLS / "versions.json").read_text())
CACHE = Path(os.environ.get("EDITOR_BUILD_CACHE", Path.home() / ".cache/editor-build"))
PREFIX = Path(os.environ.get("EDITOR_PREFIX", Path.home() / ".local"))
JOBS = os.environ.get("BUILD_JOBS", "2")
if not JOBS.isdigit() or int(JOBS) < 1:
    raise SystemExit("BUILD_JOBS must be a positive integer")

def run(*args, **kwargs):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)

def checkout(url, revision, dest):
    dest = Path(dest)
    if (dest / ".git").exists():
        result = subprocess.run(["git", "-C", str(dest), "rev-parse", "--verify", "HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        current = result.stdout.strip() if result.returncode == 0 else None
        if current == revision:
            return dest
    else:
        dest.mkdir(parents=True, exist_ok=True)
        run("git", "init", "--quiet", dest)
        run("git", "-C", dest, "remote", "add", "origin", url)
    for attempt in range(3):
        try:
            run("git", "-C", dest, "-c", "http.lowSpeedLimit=1024", "-c", "http.lowSpeedTime=60", "fetch", "--depth=1", "origin", revision)
            break
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    run("git", "-C", dest, "checkout", "--detach", "FETCH_HEAD")
    return dest
