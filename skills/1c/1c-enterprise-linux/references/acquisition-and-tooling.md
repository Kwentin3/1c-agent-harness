# Acquisition & no-sudo tooling (verified 2026-08)

## No-sudo static aria2c (torrent client) — verified

No root/sudo available (uid 1024). Install a static aria2c without it:

```bash
cd <project>/.local/tools
curl -sSL -o aria2.zip \
  "https://github.com/abcfy2/aria2-static-build/releases/download/1.37.0/aria2-x86_64-linux-musl_static.zip"
python3 -c "import zipfile; zipfile.ZipFile('aria2.zip').extractall('aria2-extract')"
BIN=$(find aria2-extract -type f -name aria2c | head -1); chmod +x "$BIN"; "$BIN" --version
```

- Version 1.37.0; zip sha256 `e0a09b12ef67f35f8a8e4fdddbec851d235b7c31da549d0578bff459032b499a`.
- Latest release + asset list: `curl https://api.github.com/repos/abcfy2/aria2-static-build/releases/latest`.
- aria2c handles `.torrent` and `magnet:` directly (no daemon, no root). For a torrent download you
  only need the `.torrent` file or magnet link; credentials go in env vars, never on disk or in logs.

### Inspect a magnet BEFORE downloading (metadata only)

```bash
aria2c --bt-metadata-only=true --bt-save-metadata=true --enable-dht=true --follow-torrent=mem \
  --bt-tracker="udp://tracker.opentrackr.org:1337/announce,udp://open.stealth.si:80/announce,udp://tracker.torrent.eu.org:451/announce" \
  "$MAGNET"
aria2c --show-files <saved>.torrent   # names + sizes + infohash
```

- Metadata exchange works over DHT + the magnet's own tracker — no rutracker passkey needed.
- Download whole or selective: `aria2c --select-file=1,3 --seed-time=0 --enable-dht=true --enable-peer-exchange=true <file>.torrent`.
- Record provenance: infohash, tracker, filename, size, sha256 of the result; label "no vendor signature — third-party redistribution".

### The unified `.run` (8.3.20+/8.5) payload structure — for reference

The `.run` is an InstallBuilder (20.9.0) ELF, NOT `.deb`. Stream-scan for magics to map it
(`PK\x03\x04` zip, `PK\x05\x06` EOCD, `\x1f\x8b\x08` gzip, `BZh9` bzip2, `!<arch>` ar/.deb,
`1c-enterprise`, `1cv8`, `ragent`). Findings for 8.5.1.1150:
- `all-clients-distr` payload = thin client only: nested `setup-thin-8.5.1.1150-{i386,x86_64}.zip`,
  `1cv8-thin-client-…dmg`, Windows `.mst`/`.ini`. No thick client/Designer.
- `setup-full` manifest lists components CONFIG (Designer), ENTERPRISE (thick client),
  WEB_ENTERPRISE, MOB_ENTERPRISE, FILEVIEWER, MNG_ENTERPRISE.
- `--help` shows InstallBuilder opts (`--mode unattended`, `--unattendedmodeui none`,
  `--installer-language en`); `--enable-components` accepted an empty list; no `--prefix`;
  the root check happens before any extraction.

## No-sudo headless Chromium via lib-bundling — renders pages

Reusable runtime at `/data/hermes-home/runtimes/chromium-debian13` (built for the DNS-browser
project): extracted `.deb` libraries under `root/usr/lib/...` plus an `LD_LIBRARY_PATH` file.
Chromium binary comes from Playwright:

```bash
uv venv venv-playwright && uv pip install --python venv-playwright/bin/python "playwright==1.62.0"
venv-playwright/bin/python -m playwright install chromium   # -> ~/.cache/ms-playwright/chromium-1234/
export LD_LIBRARY_PATH="$(cat /data/hermes-home/runtimes/chromium-debian13/LD_LIBRARY_PATH)"
```

Launch for CDP (drive via `playwright connect_over_cdp("http://127.0.0.1:9222")`):

```bash
chrome .../chrome-linux64/chrome --headless=new --remote-debugging-port=9222 \
  --user-data-dir=<dir> --no-sandbox --disable-dev-shm-usage --disable-gpu \
  --disable-blink-features=AutomationControlled \
  --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36" about:blank
```

This renders ordinary pages with only harmless dbus/font warnings. The `--user-agent` override
matters: the default headless UA embeds `HeadlessChrome/...`, an instant automation marker.

## Cloudflare-protected login -> hand off the small step to the user

For a gated login behind Cloudflare "managed + Turnstile" from a datacenter IP, programmatic
clients (`curl`, `curl_cffi`, `cloudscraper`) returned 403, and the bundled Chromium crashed on
the challenge page. Rather than fight Turnstile from a server, **hand off only the human-browser
step** — the user downloads the `.torrent` / copies the magnet / supplies a cookie in their own
browser — and do everything downstream automatically (aria2c download, install, verify).
