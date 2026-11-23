"""HTTP access shared by the research: generic user agent, per-host pacing, retries, file cache.

The services are queried without an account. Each host gets a minimum delay between two requests (AniList allows 30
requests per minute), and the answers to GET requests are cached on disk so that running the research again doesn't
query the services again.
"""
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Generic: no name, no address
USER_AGENT = "color-sheet-research/0.1"
# Minimum seconds between two requests to the same host
PACING = {
    "graphql.anilist.co": 2.1,
    "api.mangadex.org": 0.3,
    "uploads.mangadex.org": 0.3,
    "api.mangabaka.org": 0.5,
    "danbooru.donmai.us": 0.5,
    "onepiece.fandom.com": 0.5,
    "s4.anilist.co": 0.2,
    "huggingface.co": 1.0,
}
DEFAULT_PACING = 0.5


class Http:

    def __init__(self, cache_dir: Path, offline=False):
        self.cache_dir = cache_dir
        self.offline = offline
        self.last = {}
        self.requests = 0

    def _wait(self, host):
        delay = PACING.get(host, DEFAULT_PACING) - (time.monotonic() - self.last.get(host, -1e9))
        if delay > 0:
            time.sleep(delay)
        self.last[host] = time.monotonic()

    def _open(self, url, data=None, headers=None, timeout=60):
        host = urllib.parse.urlsplit(url).hostname
        request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
        for attempt in range(5):
            self._wait(host)
            self.requests += 1
            try:
                return urllib.request.urlopen(request, timeout=timeout)
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 4:
                    raise
                retry = e.headers.get("Retry-After")
                time.sleep(float(retry) if retry and retry.isdigit() else 5 * 2 ** attempt)
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == 4:
                    raise
                time.sleep(5 * 2 ** attempt)

    def _cache_path(self, key, suffix):
        return self.cache_dir / "http" / (hashlib.sha1(key.encode()).hexdigest() + suffix)

    def json(self, url, body=None):
        """GET (or POST of a JSON body) returning parsed JSON, cached on disk."""
        key = url if body is None else url + "\n" + json.dumps(body, sort_keys=True)
        path = self._cache_path(key, ".json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if self.offline:
            raise LookupError(f"not in the cache: {url}")
        data, headers = None, {"Accept": "application/json"}
        if body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        with self._open(url, data, headers) as response:
            result = json.load(response)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result), encoding="utf-8")
        return result

    def file(self, url, suffix=""):
        """Downloads a file into the cache and returns its path (images: kept out of the repository)."""
        path = self._cache_path(url, suffix or Path(urllib.parse.urlsplit(url).path).suffix)
        if path.exists():
            return path
        if self.offline:
            raise LookupError(f"not in the cache: {url}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with self._open(url, timeout=120) as response, open(tmp, "wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
        tmp.replace(path)
        return path


def download_model(cache: Path, name, url, sha256):
    """Downloads a model file once into the model cache, checked against its SHA-256 (like the server does)."""
    path = cache / name
    if path.exists():
        return path
    cache.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(name + ".tmp")
    digest = hashlib.sha256()
    print(f"Downloading {name}...", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response, open(tmp, "wb") as out:
                total = int(response.headers.get("Content-Length") or 0)
                done, shown = 0, 0
                while chunk := response.read(1 << 20):
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if total > 50e6 and done * 10 // total > shown:
                        shown = done * 10 // total
                        print(f"  {shown * 10}% of {total / 1e9:.2f} GB", flush=True)
            break
        except urllib.error.HTTPError as e:
            # Hugging Face limits anonymous downloads from shared addresses for a while
            if e.code != 429 or attempt == 3:
                raise
            digest = hashlib.sha256()
            time.sleep(60 * (attempt + 1))
    if digest.hexdigest() != sha256:
        tmp.unlink()
        raise SystemExit(f"{name} is corrupted, start again")
    tmp.replace(path)
    return path
