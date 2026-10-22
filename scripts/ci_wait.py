"""Wait for local test services, using only the Python standard library."""

import time
import urllib.error
import urllib.request

deadline = time.monotonic() + 90
for url in ["http://127.0.0.1:8000/api/health", "http://127.0.0.1:3000"]:
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2):  # noqa: S310 - fixed loopback HTTP URLs only
                break
        except (urllib.error.URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise SystemExit(f"Test service did not become ready: {url}") from None
            time.sleep(0.5)
