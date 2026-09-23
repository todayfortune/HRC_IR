from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.services.market import MarketService
from app.services.report import ReportService
from app.services.telegram import TelegramService


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
reports = ReportService()


class Handler(BaseHTTPRequestHandler):
    server_version = "StockView/1.0"

    def _json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/report":
            day = parse_qs(parsed.query).get("date", [None])[0]
            try:
                self._json({"ok": True, "report": reports.load(day)})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        requested = "index.html" if parsed.path in ("", "/") else parsed.path.lstrip("/")
        target = (WEB_DIR / requested).resolve()
        if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            payload = self._body()
            if self.path == "/api/report/save":
                report = reports.save(payload)
            elif self.path == "/api/market/update":
                report = MarketService().update(reports.load(payload.get("date")))
                report = reports.save(report)
                reports.save_market_snapshot(report)
            elif self.path == "/api/telegram/update":
                report = TelegramService().update(reports.load(payload.get("date")))
                report = reports.save(report)
            else:
                self._json({"ok": False, "error": "Not found"}, HTTPStatus.NOT_FOUND)
                return
            self._json({"ok": True, "report": report})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main():
    parser = argparse.ArgumentParser(description="증권시장 동향 V1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"증권시장 동향: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
