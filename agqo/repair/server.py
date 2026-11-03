"""Loopback-only decision UI, JSON API and bounded request handling."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import threading
from urllib.parse import urlparse

from .data import synthetic_data, parse_or_prices
from .llm import QwenClient
from .mandates import normalize_rules
from .workflow import decide

WEB = Path(__file__).parent / "web"


def create_server(port=8765, llm_mode="disabled", results_dir="results/repair", or_path="data/repair/indtrack1.txt"):
    client = QwenClient(llm_mode, audit_path=Path(results_dir) / "ui_qwen.jsonl")
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, mime="application/json; charset=utf-8"):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status); self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body)

        def data(self, source):
            if source == "synthetic":
                return synthetic_data()
            if source == "or-library":
                return parse_or_prices(Path(or_path).read_text(), expected_n=31)
            raise ValueError("Unsupported data source.")

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/context":
                d = self.data("synthetic")
                return self.reply(200, {"tickers": d.tickers, "sectors": d.sectors,
                                         "llm_mode": llm_mode, "or_library_available": Path(or_path).exists()})
            if path == "/api/benchmark":
                p = Path(results_dir) / "summary.json"
                return self.reply(200, json.loads(p.read_text()) if p.exists() else {"status": "not_run"})
            if path in {"/", "/app.js", "/style.css"}:
                p = WEB / ("index.html" if path == "/" else path[1:])
            elif path.startswith("/research/"):
                root = Path(results_dir).resolve()
                p = (root / path[len("/research/"):]).resolve()
                if root not in p.parents or p.suffix not in {".html", ".json", ".csv", ".png", ".md"}:
                    return self.reply(404, {"error": "not_found"})
            else:
                return self.reply(404, {"error": "not_found"})
            if not p.is_file():
                return self.reply(404, {"error": "not_found"})
            self.reply(200, p.read_bytes(), (mimetypes.guess_type(p.name)[0] or "application/octet-stream") + ("; charset=utf-8" if p.suffix in {".html", ".css", ".js"} else ""))

        def do_POST(self):
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"} or (origin and origin not in {f"http://{host}"}):
                return self.reply(403, {"error": "local_origin_required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    return self.reply(413, {"error": "request_too_large"})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict) or not isinstance(body.get("text"), str) or not body["text"].strip():
                    raise ValueError("A text investment mandate is required.")
                d = self.data(body.get("source", "synthetic"))
                normalizer = body.get("normalizer", "rules")
                if normalizer not in {"rules", "qwen"}:
                    raise ValueError("Invalid normalizer.")
                if not lock.acquire(blocking=False):
                    return self.reply(409, {"error": "A decision is being processed; try again later."})
                try:
                    if self.path == "/api/normalize":
                        if normalizer == "qwen":
                            m, trace = client.normalize(body["text"], d.tickers[:8], tuple(sorted(set(d.sectors[:8]))))
                        else:
                            m, trace = normalize_rules(body["text"], d.tickers[:8], tuple(sorted(set(d.sectors[:8])))), {"status": "baseline_rules_not_llm"}
                        return self.reply(200, {"mandate": None if m is None else m.to_dict(), "trace": trace})
                    if self.path == "/api/solve":
                        result = decide(d, body["text"], client, normalizer, export_circuit=False)
                        return self.reply(200, result)
                    return self.reply(404, {"error": "not_found"})
                finally:
                    lock.release()
            except (ValueError, TypeError, FileNotFoundError, KeyError) as exc:
                return self.reply(400, {"error": str(exc)})
            except Exception as exc:
                return self.reply(500, {"error": type(exc).__name__ + ": " + str(exc)})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
