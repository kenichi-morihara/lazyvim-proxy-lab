"""Lab policy: deny GitHub downloads; allow Git smart HTTP and package registries."""
import re
from urllib.parse import parse_qs
from mitmproxy import http, ctx

GITHUB_DOWNLOAD_HOSTS = {
    "codeload.github.com", "raw.githubusercontent.com", "objects.githubusercontent.com",
    "release-assets.githubusercontent.com", "github-releases.githubusercontent.com",
}
PACKAGE_SUFFIXES = (
    "rockylinux.org", "fedoraproject.org", "cloud.fedoraproject.org", "download.docker.com",
    "registry.npmjs.org", "pypi.org", "pythonhosted.org",
    "registry-1.docker.io", "auth.docker.io", "production.cloudflare.docker.com",
    "docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com",
)

def permitted(method, host, path):
    host = host.lower().rstrip(".")
    if host == "github.com":
        # Accept only HTTPS Git smart protocol endpoints, including repos without .git suffix.
        endpoint, _, query = path.partition("?")
        return (
            method == "GET" and re.fullmatch(r"/[^/]+/[^/]+/info/refs", endpoint) is not None
            and parse_qs(query).get("service") == ["git-upload-pack"]
        ) or (
            method == "POST" and re.fullmatch(r"/[^/]+/[^/]+/git-upload-pack", endpoint) is not None
        )
    if host in GITHUB_DOWNLOAD_HOSTS or host.endswith(".githubusercontent.com") or host.endswith(".github.com"):
        return False
    return any(host == domain or host.endswith("." + domain) for domain in PACKAGE_SUFFIXES)

def request(flow: http.HTTPFlow):
    if not permitted(flow.request.method, flow.request.pretty_host, flow.request.path):
        flow.response = http.Response.make(403, b"Blocked by lazyvim-proxy-lab policy\n", {"Content-Type": "text/plain", "X-Lab-Policy": "deny"})
        # Never log query strings, headers, bodies or proxy credentials.
        ctx.log.info("DENY " + flow.request.pretty_host)
