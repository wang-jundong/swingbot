"""HTTP server for the token dashboard."""

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.config.web import WEB_HOST, WEB_PORT
from src.utils.log_util import log_formatter
from src.web.api import ohlc_curve_payload, ohlc_tokens_payload
from src.web.page import page_html

_STATIC = Path(__file__).resolve().parent / "static"
_STATIC_FILES = {
    "/static/lightweight-charts.js": ("text/javascript; charset=utf-8", "lightweight-charts.js"),
}


def _logger() -> logging.Logger:
    logger = logging.getLogger("swingbot.web")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(log_formatter())
        logger.addHandler(handler)
    return logger


logger = _logger()


def _query_int(query: dict, key: str) -> int | None:
    raw = (query.get(key) or [""])[0]
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class TokenDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", page_html().encode("utf-8"))
            return
        static = _STATIC_FILES.get(path)
        if static:
            content_type, name = static
            file_path = _STATIC / name
            if file_path.is_file():
                self._send(200, content_type, file_path.read_bytes())
                return
        if path == "/api/ohlc/tokens":
            query = parse_qs(urlparse(self.path).query)
            raw_wallet = (query.get("wallet") or [None])[0]
            scoped = "wallet" not in query or (raw_wallet not in (None, "", "all"))
            wallet = None if raw_wallet in (None, "", "all") else raw_wallet
            try:
                body = json.dumps(ohlc_tokens_payload(wallet, scoped=scoped)).encode("utf-8")
            except Exception:
                logger.exception("failed to load ohlc tokens")
                self._send(500, "application/json", b'{"error":"failed to load ohlc tokens"}')
                return
            self._send(200, "application/json; charset=utf-8", body, cache=False)
            return
        if path == "/api/ohlc/curve":
            query = parse_qs(urlparse(self.path).query)
            address = (query.get("address") or [""])[0]
            wallet = (query.get("wallet") or [None])[0]
            interval = (query.get("interval") or ["1m"])[0]
            time_from = _query_int(query, "from")
            time_to = _query_int(query, "to")
            try:
                payload = ohlc_curve_payload(address, wallet, interval, time_from, time_to)
            except Exception:
                logger.exception("failed to load ohlc curve")
                self._send(500, "application/json", b'{"error":"failed to load ohlc curve"}')
                return
            if payload is None:
                self._send(404, "application/json; charset=utf-8", b'{"error":"ohlc not found"}')
                return
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(payload).encode("utf-8"),
                cache=False,
            )
            return
        self._send(404, "text/plain; charset=utf-8", b"not found")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self._send(404, "text/plain; charset=utf-8", b"not found")

    def log_message(self, format: str, *args) -> None:
        logger.info("%s %s", self.address_string(), format % args)

    def _send(
        self,
        status: int,
        content_type: str,
        body: bytes,
        cache: bool = True,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run_web_server(host: str = WEB_HOST, port: int = WEB_PORT) -> None:
    server = ThreadingHTTPServer((host, port), TokenDashboardHandler)
    logger.info("dashboard http://%s:%s", host, port)
    server.serve_forever()


if __name__ == "__main__":
    run_web_server()
