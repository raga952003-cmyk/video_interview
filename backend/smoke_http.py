"""HTTP smoke test against a running Flask server. Usage: python smoke_http.py [base_url]"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def check(base: str) -> int:
    base = base.rstrip("/")
    failures = 0
    tests = [
        ("GET", "/", None, (200,)),
        ("GET", "/favicon.ico", None, (204,)),
        ("GET", "/api/health", None, (200,)),
        ("GET", "/api/roles", None, (200,)),
        (
            "GET",
            "/api/get-question?role=Python%20Developer",
            None,
            (200,),
        ),
    ]
    for method, path, body, ok_codes in tests:
        url = base + path
        try:
            req = urllib.request.Request(url, method=method, data=body)
            with urllib.request.urlopen(req, timeout=10) as r:
                code = r.status
                raw = r.read()
        except urllib.error.HTTPError as e:
            code = e.code
            raw = e.read()
        except Exception as e:
            print(f"FAIL {method} {path}: {e}")
            failures += 1
            continue
        if code not in ok_codes:
            print(f"FAIL {method} {path}: status {code} (want {ok_codes})")
            failures += 1
            continue
        if path == "/api/health":
            try:
                data = json.loads(raw.decode())
                if "database" not in data or "openai_configured" not in data:
                    print(f"FAIL {path}: wrong JSON (not interview-coach API?): {data}")
                    failures += 1
                    continue
            except json.JSONDecodeError:
                print(f"FAIL {path}: not JSON")
                failures += 1
                continue
        print(f"OK   {method} {path} -> {code}")

    return failures


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5050"
    n = check(base_url)
    sys.exit(1 if n else 0)
