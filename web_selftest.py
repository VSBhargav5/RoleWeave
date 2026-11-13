"""Exercise bundled browser assets and local API using a fresh synthetic shelf."""
import http.client
import json
from pathlib import Path
import sys
import threading
from runtime_paths import APP_VERSION
from web_server import LocalServer
from web_service import WebService, seed_web_demo


def run_web_self_test(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    report = {"version": APP_VERSION, "frozen": bool(getattr(sys, "frozen", False)), "ok": False}
    server = None
    try:
        path = destination / "synthetic.db"
        seed_web_demo(path)
        server = LocalServer(("127.0.0.1", 0), WebService(path, demo=True))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def get(path, authorized=True):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
            try:
                connection.request("GET", path, headers={"X-RoleWeave-Token": server.token} if authorized else {})
                response = connection.getresponse()
                payload = response.read()
                if response.status != (401 if not authorized and path.startswith('/api/') else 200):
                    raise ValueError("Bundled route failed")
                return payload
            finally:
                connection.close()
        get('/api/bootstrap', False)
        for asset in ('/', '/app.js', '/styles.css', '/icons.js', '/api/browser-helper'):
            if not get(asset): raise ValueError('Bundled asset missing')
        data = json.loads(get('/api/bootstrap'))
        resume = data['resumes'][0]
        # Demo freezes HTML; the core test suite separately covers PDF creation.
        if not get('/api/download?kind=resume&id='+resume['id']+'&format=html'):
            raise ValueError('Frozen resume unavailable')
        get('/api/backup')
        report['ok'] = True
    except Exception:
        report['error'] = 'Synthetic web runtime check failed; no private diagnostics logged.'
    finally:
        if server:
            server.shutdown()
            server.server_close()
        (destination / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report['ok']
