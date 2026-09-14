#!/usr/bin/env python3
"""Skills Hub UI server.

Stdlib only: http.server for static files + a two-endpoint JSON API,
webbrowser to open the tab. No dependencies, no build step.

By default the API serves a live scan of the real hub (scanner.py;
rescanned at most every scanner.SCAN_TTL seconds). --dummy serves the
prototype's dummy data instead.

Usage:
    python3 app/server.py [--port N] [--host H] [--no-browser] [--dummy]
"""

import argparse
import json
import socket
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
HUB_ROOT = BASE.parent

if BASE not in sys.path:  # allow running from anywhere
    sys.path.insert(0, str(BASE))

import data  # noqa: E402  (sibling module: dummy data)
import scanner  # noqa: E402  (sibling module: real scan)

DUMMY = False

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "SkillsHubUI/0.1"

    def _send_bytes(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send_bytes(
            HTTPStatus.OK,
            json.dumps(obj, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _static(self, rel):
        path = (STATIC / rel.lstrip("/")).resolve()
        if not path.is_file() or STATIC.resolve() not in path.parents:
            self._send_bytes(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
            return
        body = path.read_bytes()
        ctype = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        self._send_bytes(HTTPStatus.OK, body, ctype)

    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route == "/api/hub":
            payload = scanner.scan(HUB_ROOT)["hub"] if not DUMMY else data.hub()
            payload = dict(payload)
            payload.pop("_unresolved", None)
            self._json(payload)
        elif route == "/api/projects":
            payload = data.projects() if DUMMY else scanner.scan(HUB_ROOT)["projects"]
            self._json(payload)
        elif route in ("/", "/index.html"):
            self._static("index.html")
        elif route == "/favicon.svg":
            self._static("favicon.svg")
        else:
            self._static(route)

    def log_message(self, format, *args):  # quieter default logging
        sys.stderr.write("  %s\n" % (format % args))


def free_port(preferred, host="127.0.0.1"):
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
            except OSError:
                continue
            return port
    return preferred


def main():
    global DUMMY
    ap = argparse.ArgumentParser(description="Skills Hub UI")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--dummy", action="store_true",
                    help="serve the prototype's dummy data instead of the real hub")
    args = ap.parse_args()
    DUMMY = args.dummy

    port = free_port(args.port, args.host)
    url = f"http://{args.host}:{port}/"
    httpd = ThreadingHTTPServer((args.host, port), Handler)
    httpd.daemon_threads = True

    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    print(f"Skills Hub UI — {'DUMMY data' if DUMMY else 'live hub data (rescans every %ss)' % scanner.SCAN_TTL}")
    print(f"  hub root    {HUB_ROOT}")
    print(f"  serving at  {url}")
    print(f"  stop with   Ctrl-C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
