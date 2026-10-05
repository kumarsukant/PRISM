"""Which web pages and Host names may talk to the backend (CORS, Origin refusal, Host check).

Calls the ASGI app directly (no server, no extra packages). Run from the repo root with the dev venv:
    backend\\venv\\Scripts\\python.exe -m unittest discover -s backend\\tests -v
"""
import asyncio
import contextlib
import io
import os
import sys
import unittest

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP_DIR)

import main  # noqa: E402


def call(method: str, path: str, host: str = "127.0.0.1:8000", origin: str = None, preflight: bool = False):
    """(status, headers) for one request through the full middleware stack."""
    headers = [(b"host", host.encode())]
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    if preflight:
        headers += [(b"access-control-request-method", b"POST"), (b"access-control-request-headers", b"content-type")]
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "scheme": "http",
             "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "", "headers": headers,
             "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", 8000)}
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(main.app(scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    return start["status"], {k.decode().lower(): v.decode() for k, v in start["headers"]}


ALLOWED = ["http://tauri.localhost", "https://tauri.localhost", "tauri://localhost", "http://localhost:5173",
           "http://127.0.0.1:5173", "http://localhost", "https://localhost:1420", "http://127.0.0.1"]
REFUSED = ["https://example.com", "http://tauri.localhost.evil.com", "http://localhost.evil.com", "null",
           "http://127.0.0.1.nip.io", "http://evil.com:5173", "tauri://evil", "file://", "http://localhost:123456"]


class OriginTest(unittest.TestCase):
    def setUp(self):
        main._refused_origins.clear()

    def test_app_and_dev_origins_pass_preflight(self):
        for origin in ALLOWED:
            status, headers = call("OPTIONS", "/scan/start", origin=origin, preflight=True)
            self.assertEqual(status, 200, origin)
            self.assertEqual(headers.get("access-control-allow-origin"), origin)

    def test_other_origins_are_refused_and_logged_once(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            for origin in REFUSED:
                status, headers = call("OPTIONS", "/scan/start", origin=origin, preflight=True)
                self.assertEqual(status, 403, origin)
                self.assertNotIn("access-control-allow-origin", headers)
                status, _ = call("GET", "/health", origin=origin)  # simple requests too, not only preflights
                self.assertEqual(status, 403, origin)
        log = out.getvalue()
        for origin in REFUSED:
            self.assertEqual(log.count(f"Refused request from origin {origin!r}"), 1, log)

    def test_no_origin_is_allowed(self):
        # thumbnails in <img>, the app's Rust lookup and scripts send no Origin header
        self.assertEqual(call("GET", "/health")[0], 200)


class HostTest(unittest.TestCase):
    def test_only_loopback_names_are_accepted(self):
        for host in ("127.0.0.1:8000", "localhost:8000", "127.0.0.1", "localhost"):
            self.assertEqual(call("GET", "/health", host=host)[0], 200, host)
        for host in ("evil.example", "evil.example:8000", "127.0.0.1.evil.example", "192.168.1.5:8000"):
            self.assertEqual(call("GET", "/health", host=host)[0], 400, host)


if __name__ == "__main__":
    unittest.main()
