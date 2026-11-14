"""Loopback-only desktop web host with session authorization and origin checks."""
import hashlib
import errno
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
from io import BytesIO
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import threading
from urllib.parse import parse_qs, urlsplit
import webbrowser
import zipfile

from career_profile import unique_json
from runtime_paths import APP_VERSION, RESOURCE_ROOT, default_database_path, new_practice_path
from web_service import WebService, browser_profile, require, seed_web_demo

ASSETS = {"/app.js": ("app.js", "application/javascript"), "/styles.css": ("styles.css", "text/css"),
          "/icons.js": ("icons.js", "application/javascript"),
          "/document-preview.css": ("document-preview.css", "text/css")}


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, service):
        if address[0] != "127.0.0.1":
            raise ValueError("The desktop host must bind to IPv4 loopback")
        self.service = service
        self.token = secrets.token_urlsafe(32)
        super().__init__(address, RequestHandler)
        self.origin = "http://127.0.0.1:" + str(self.server_port)

    def handle_error(self, request, client_address):
        pass  # Do not log URLs, request bodies or session credentials.

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(10)
        return request, address


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "RoleWeaveLocal"
    sys_version = ""

    def log_message(self, *_args):
        pass

    def reply(self, status, payload, content_type="application/json; charset=utf-8", filename=None):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        if filename:
            self.send_header("Content-Disposition", 'attachment; filename="' + filename + '"')
        self.end_headers()
        self.wfile.write(payload)

    def valid_origin(self):
        expected = "127.0.0.1:" + str(self.server.server_port)
        if self.headers.get("Host") != expected:
            self.reply(403, {"error": "Unrecognized local host"})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            self.reply(403, {"error": "Cross-origin requests are refused"})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.reply(403, {"error": "Open RoleWeave from its local shortcut"})
            return False
        return True

    def authorized(self):
        if not self.valid_origin():
            return False
        provided = self.headers.get("X-RoleWeave-Token", "")
        if not hmac.compare_digest(provided, self.server.token):
            self.reply(401, {"error": "This local session expired. Reopen RoleWeave."})
            return False
        return True

    def query(self):
        parsed = urlsplit(self.path)
        values = parse_qs(parsed.query, keep_blank_values=True)
        if any(len(value) != 1 for value in values.values()):
            raise ValueError("Duplicate query parameters are unsupported")
        return parsed.path, {key: value[0] for key, value in values.items()}

    def body(self, limit=1024 * 1024):
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or self.headers.get("Transfer-Encoding") or not lengths[0].isdigit():
            raise ValueError("A bounded request length is required")
        size = int(lengths[0])
        if not 0 < size <= limit:
            raise ValueError("Request exceeds its supported size")
        payload = self.rfile.read(size)
        if len(payload) != size:
            raise ValueError("Incomplete request")
        return payload

    def do_OPTIONS(self):
        self.reply(403, {"error": "Cross-origin API access is disabled"})

    def do_GET(self):
        try:
            self.get()
        except (ValueError, OSError, sqlite3.Error, KeyError) as exc:
            self.reply(400, {"error": str(exc) if isinstance(exc, ValueError) else "That local record or file is unavailable. Refresh and try again."})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.reply(500, {"error": "RW-WEB-001: action interrupted. Refresh saved state before repeating it. No diagnostic contents were logged."})

    def get(self):
        path, params = self.query()
        if path == "/health":
            if self.valid_origin():
                self.reply(200, {"app": "roleweave-local-v1", "version": APP_VERSION,
                                 "workspace": hashlib.sha256(str(self.server.service.store.path.resolve()).encode()).hexdigest()})
            return
        if path in ("/", "/index.html"):
            if not self.valid_origin():
                return
            html = (RESOURCE_ROOT / "web" / "index.html").read_text(encoding="utf-8")
            html = html.replace("__ROLEWEAVE_SESSION__", self.server.token)
            self.reply(200, html.encode(), "text/html; charset=utf-8")
            return
        if path in ASSETS:
            if not self.valid_origin():
                return
            filename, content_type = ASSETS[path]
            self.reply(200, (RESOURCE_ROOT / "web" / filename).read_bytes(), content_type)
            return
        if path in ("/form-fixture.html", "/form-fixture.js") and self.server.service.demo:
            if not self.valid_origin():
                return
            filename = path[1:]
            self.reply(200, (RESOURCE_ROOT / "web" / filename).read_bytes(), "text/html" if path.endswith("html") else "application/javascript")
            return
        if not self.authorized():
            return
        service = self.server.service
        if path == "/api/bootstrap":
            self.reply(200, service.bootstrap())
        elif path == "/api/job":
            require(params, ("id",), ("id",))
            self.reply(200, service.job(params["id"]))
        elif path == "/api/profile":
            self.reply(200, service.profile())
        elif path == "/api/resume":
            require(params, ("id",), ("id",))
            self.reply(200, service.get_resume(params["id"]))
        elif path == "/api/letter":
            require(params, ("id",), ("id",))
            self.reply(200, service.get_letter(params["id"]))
        elif path == "/api/autofill-profile":
            profile = service.profile()
            if profile is None:
                raise ValueError("Save a reviewed profile first")
            self.reply(200, browser_profile(profile["profile"]))
        elif path == "/api/download":
            require(params, ("kind", "id", "format"), ("kind", "id"))
            payload, content_type, filename = service.download(params["kind"], params["id"], params.get("format", "pdf"))
            self.reply(200, payload, content_type, filename)
        elif path == "/api/backup":
            self.reply(200, service.backup(), "application/json", "RoleWeave-backup.json")
        elif path == "/api/workspace-bundle":
            self.reply(200, service.workspace_bundle(), "application/zip", "RoleWeave-workspace.zip")
        elif path == "/api/browser-helper":
            stream = BytesIO()
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                for filename in ("manifest.json", "popup.html", "popup.css", "popup.js", "page.js", "background.js", "README.md"):
                    archive.writestr("RoleWeave-helper/" + filename, (RESOURCE_ROOT / "browser-helper" / filename).read_bytes())
            self.reply(200, stream.getvalue(), "application/zip", "RoleWeave-browser-helper.zip")
        else:
            self.reply(404, {"error": "That application route does not exist"})

    def do_POST(self):
        if not self.authorized():
            return
        try:
            path, params = self.query()
            if params:
                raise ValueError("POST actions do not accept URL parameters")
            if path == "/api/restore":
                if self.headers.get("Content-Type", "").split(";")[0] != "application/octet-stream":
                    raise ValueError("Choose a backup file")
                self.reply(200, self.server.service.restore(self.body(64 * 1024 * 1024)))
                return
            if path == "/api/recovery/preview":
                if self.headers.get("Content-Type", "").split(";")[0] != "application/octet-stream":
                    raise ValueError("Choose a workspace ZIP")
                self.reply(200,self.server.service.preview_recovery(self.body(64*1024*1024)))
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError("JSON request required")
            data = json.loads(self.body(8*1024*1024 if path=='/api/resume-import/preview' else 1024*1024), object_pairs_hook=unique_json)
            if not isinstance(data, dict):
                raise ValueError("Request must be an object")
            service = self.server.service
            routes = {"/api/jobs": service.save_job, "/api/profile": service.save_profile,
                      "/api/resume-import/preview": service.preview_resume_import,
                      "/api/resume-import/commit": service.commit_resume_import,
                      "/api/recovery/restore": service.restore_recovery,
                      "/api/review": service.save_review, "/api/search": service.search,
                      "/api/review/from-profile": service.review_from_profile,
                      "/api/search/save": service.save_search_job,
                      "/api/resume/preview": service.resume,
                      "/api/resume": lambda value: service.resume(value, freeze=True),
                      "/api/letter": service.letter, "/api/packet": service.packet,
                      "/api/letter/preview": lambda value: service.letter(value, freeze=False),
                      "/api/track": service.track, "/api/submission": service.submit_observation}
            if path in routes:
                self.reply(200, routes[path](data))
            elif path == '/api/recovery/open':
                recovered=service.recovery_database(data)
                if getattr(sys,'frozen',False):command=[sys.executable,'--db',str(recovered)]
                else:
                    executable=Path(sys.executable).with_name('pythonw.exe')
                    command=[str(executable) if executable.exists() else sys.executable,str(RESOURCE_ROOT/'desktop.py'),'--db',str(recovered)]
                subprocess.Popen(command,cwd=RESOURCE_ROOT)
                self.reply(200,{'opened':True})
            elif path == "/api/quit":
                require(data, ("confirmed",), ("confirmed",))
                if data["confirmed"] is not True:
                    raise ValueError("Confirm closing the local app")
                self.reply(200, {"closed": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            elif path == "/api/legacy":
                require(data, ("confirmed",), ("confirmed",))
                if data["confirmed"] is not True:
                    raise ValueError("Confirm opening native tools")
                if getattr(sys, "frozen", False):
                    command = [sys.executable, "--legacy", "--db", str(service.store.path)]
                else:
                    executable = Path(sys.executable).with_name("pythonw.exe")
                    command = [str(executable) if executable.exists() else sys.executable, str(RESOURCE_ROOT / "desktop.py"), "--legacy", "--db", str(service.store.path)]
                subprocess.Popen(command, cwd=RESOURCE_ROOT)
                self.reply(200, {"opened": True})
            else:
                self.reply(404, {"error": "Unknown application action"})
        except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
            self.reply(400, {"error": str(exc)})
        except (OSError, sqlite3.Error, KeyError):
            self.reply(400, {"error": "The local operation could not complete. Refresh saved state before retrying."})
        except Exception:
            self.reply(500, {"error": "RW-WEB-001: action interrupted. Refresh saved state before repeating it. No diagnostic contents were logged."})


def find_workspace_host(path, preferred):
    """Reuse only the exact workspace/version; never stop another local server."""
    expected = hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()
    candidates = range(8765, 8773) if preferred == 8765 else [preferred] if preferred else []
    fallback_ports = []
    for candidate in candidates:
        connection = http.client.HTTPConnection("127.0.0.1", candidate, timeout=.25)
        try:
            connection.request("GET", "/health")
            response = connection.getresponse()
            answer = json.loads(response.read(4096))
            if (response.status == 200 and isinstance(answer, dict)
                    and answer.get("app") == "roleweave-local-v1"
                    and answer.get("workspace") == expected and answer.get("version") == APP_VERSION):
                return candidate, fallback_ports
        except (ConnectionRefusedError, TimeoutError):
            # Windows can time out before reporting a refused loopback connect.
            # Binding is authoritative; an occupied port still fails without replacement.
            fallback_ports.append(candidate)
        except (OSError, ValueError, http.client.HTTPException):
            pass  # Occupied, unresponsive or unrelated: leave it untouched.
        finally:
            connection.close()
    return None, fallback_ports


def run_application(path=None, demo=False, port=8765, open_browser=True):
    path = new_practice_path(default_database_path().parent) if demo else Path(path) if path else default_database_path()
    if demo:
        seed_web_demo(path)
        if port == 8765:
            port = 0
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Choose a valid local port")
    running, fallback_ports = find_workspace_host(path, port)
    if running is not None:
        origin = "http://127.0.0.1:" + str(running)
        if open_browser:
            webbrowser.open(origin)
        else:
            print(origin, flush=True)
        return 0
    service = WebService(path, demo=demo)
    for candidate in [*fallback_ports, 0]:
        try:
            server = LocalServer(("127.0.0.1", candidate), service)
            break
        except OSError as exc:
            if candidate and (exc.errno == errno.EADDRINUSE or getattr(exc, "winerror", None) == 10048):
                continue  # Another launch won the bind race; choose a free port.
            raise
    try:
        if open_browser:
            webbrowser.open(server.origin)
        else:
            print(server.origin, flush=True)
        server.serve_forever(poll_interval=.2)
    finally:
        server.server_close()
    return 0
