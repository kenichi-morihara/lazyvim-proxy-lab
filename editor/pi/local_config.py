"""Private, data-only Pi connection settings shared by setup and the launcher."""
import json
import os
from pathlib import Path
import stat
import tempfile

FIELDS = {
    'INTERNAL_AI_TRANSPORT', 'INTERNAL_AI_API', 'INTERNAL_AI_BASE_URL', 'INTERNAL_AI_MODEL',
    'INTERNAL_AI_USER_HEADER', 'INTERNAL_AI_USER', 'INTERNAL_AI_API_KEY', 'INTERNAL_AI_AUTH_HEADER',
    'HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY', 'NODE_EXTRA_CA_CERTS',
}


def config_path(env):
    return Path(env.get('XDG_CONFIG_HOME') or Path(env.get('HOME', str(Path.home()))) / '.config') / 'editor-pi' / 'connection.json'


def private_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('Pi connection file must be owned by you, regular, and mode 600.')


def read_config(env):
    path = config_path(env)
    if not path.exists() and not path.is_symlink():
        return {}
    private_file(path)
    try:
        data = json.loads(path.read_text())
    except (ValueError, UnicodeError):
        raise ValueError('Invalid Pi connection file; run make configure-pi.') from None
    if not isinstance(data, dict) or any(k not in FIELDS or not isinstance(v, str) or '\0' in v for k, v in data.items()):
        raise ValueError('Invalid Pi connection settings; run make configure-pi.')
    return data


def load_config(env):
    data = read_config(env)
    # An explicitly selected legacy transport must not acquire saved Responses credentials.
    if env.get('INTERNAL_AI_TRANSPORT') == 'company-chat':
        data = {k: v for k, v in data.items() if not k.startswith('INTERNAL_AI_')}
    for key, value in data.items():
        env.setdefault(key, value)
    return env


def save_config(env, data):
    path = config_path(env)
    for parent in (path.parent.resolve(), *path.parent.resolve().parents):
        if (parent / '.git').exists():
            raise ValueError('Choose XDG_CONFIG_HOME outside a Git repository.')
    if path.parent.is_symlink():
        raise ValueError('Pi settings directory must not be a symlink.')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.parent.stat()
    if info.st_uid != os.getuid():
        raise ValueError('Pi settings directory must be owned by you.')
    path.parent.chmod(0o700)
    if path.exists() or path.is_symlink():
        private_file(path)
    fd, name = tempfile.mkstemp(prefix='.connection-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.write('\n')
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    return path
