#!/usr/bin/env python3
"""Availability checker for a static status page.

Probes each target over HTTPS, records the result, and writes a rolling
window of history to status.json for the front end to render.

Standard library only -- no pip install, nothing to break on a rebuild.

Run from cron:
    */5 * * * * /opt/statuspage/check.py
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path(os.environ.get("STATUS_CONFIG", "/opt/statuspage/targets.json"))
HISTORY = Path(os.environ.get("STATUS_HISTORY", "/var/lib/statuspage/history.json"))
OUTPUT = Path(os.environ.get("STATUS_OUTPUT", "/var/www/html/status.json"))

HISTORY_SLOTS = 90          # 90 checks x 5 min = 7.5 hours of window
TIMEOUT = 10                # seconds
USER_AGENT = "statuspage-monitor/1.0 (+availability check)"


def probe(url: str, expect: int | None = None) -> dict:
    """Fetch a URL and report outcome, HTTP code, and round-trip time."""
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": USER_AGENT},
    )

    context = ssl.create_default_context()
    started = time.monotonic()

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT, context=context) as response:
            response.read(2048)          # touch the body; some servers stall on headers alone
            elapsed = int((time.monotonic() - started) * 1000)
            code = response.status
            ok = (code == expect) if expect else (200 <= code < 400)
            return {
                "status": "up" if ok else "down",
                "code": code,
                "ms": elapsed,
                "detail": None if ok else f"unexpected status {code}",
            }

    except urllib.error.HTTPError as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        ok = (exc.code == expect) if expect else False
        return {
            "status": "up" if ok else "down",
            "code": exc.code,
            "ms": elapsed,
            "detail": None if ok else f"HTTP {exc.code}",
        }

    except ssl.SSLCertVerificationError as exc:
        return {"status": "down", "code": None, "ms": None,
                "detail": f"TLS certificate problem: {exc.reason}"}

    except urllib.error.URLError as exc:
        return {"status": "down", "code": None, "ms": None,
                "detail": f"unreachable: {exc.reason}"}

    except TimeoutError:
        return {"status": "down", "code": None, "ms": None,
                "detail": f"no response within {TIMEOUT}s"}

    except Exception as exc:                                  # noqa: BLE001
        return {"status": "down", "code": None, "ms": None,
                "detail": f"{type(exc).__name__}: {exc}"}


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def main() -> int:
    targets = load_json(CONFIG, None)
    if not targets:
        print(f"No targets found at {CONFIG}", file=sys.stderr)
        return 1

    history = load_json(HISTORY, {})
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    services = []
    for target in targets:
        name = target["name"]
        url = target["url"]
        result = probe(url, target.get("expect_status"))

        entry = {"at": now, "status": result["status"], "ms": result["ms"]}
        past = history.get(url, [])
        past.append(entry)
        history[url] = past[-HISTORY_SLOTS:]

        services.append({
            "name": name,
            "url": url,
            "status": result["status"],
            "code": result["code"],
            "ms": result["ms"],
            "detail": result["detail"],
            "history": history[url],
        })

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(history))

    payload = {"generated": now, "services": services}

    # Write to a temp file then rename, so the front end never reads a
    # half-written document mid-check.
    temp = OUTPUT.with_suffix(".json.tmp")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp.write_text(json.dumps(payload, indent=2))
    temp.replace(OUTPUT)
    OUTPUT.chmod(0o644)

    down = [s["name"] for s in services if s["status"] == "down"]
    print(f"{now}  checked {len(services)}  down: {down or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())