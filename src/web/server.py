"""HTTP server for the token dashboard."""

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from src.config.web import WEB_HOST, WEB_PORT
from src.utils.log_util import log_formatter
from src.web.api import (
    backtest_ohlcv_payload,
    candle_refresh_status,
    refresh_mint_ohlcv,
    start_candle_refresh,
    tokens_payload,
)
from src.web.page import PAGE_HTML


def _logger() -> logging.Logger:
    logger = logging.getLogger("swingbot.web")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(log_formatter())
        logger.addHandler(handler)
    return logger


logger = _logger()


class TokenDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE_HTML.encode("utf-8"))
            return
        if path == "/api/tokens":
            live = parse_qs(urlparse(self.path).query).get("live", ["0"])[0] == "1"
            try:
                body = json.dumps(tokens_payload(live=live)).encode("utf-8")
            except Exception:
                logger.exception("failed to load tokens")
                self._send(500, "application/json", b'{"error":"failed to load tokens"}')
                return
            self._send(200, "application/json; charset=utf-8", body, cache=False)
            return
        if path == "/api/backtest/ohlcv":
            address = (parse_qs(urlparse(self.path).query).get("address") or [""])[0]
            try:
                payload = backtest_ohlcv_payload(address)
            except Exception:
                logger.exception("failed to load ohlcv")
                self._send(500, "application/json", b'{"error":"failed to load ohlcv"}')
                return
            if payload is None:
                self._send(404, "application/json", b'{"error":"ohlcv not found"}')
                return
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(payload).encode("utf-8"),
                cache=False,
            )
            return
        if path == "/api/backtest/refresh":
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(candle_refresh_status()).encode("utf-8"),
                cache=False,
            )
            return
        self._send(404, "text/plain; charset=utf-8", b"not found")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        path = urlparse(self.path).path
        if path == "/api/backtest/ohlcv":
            address = (parse_qs(urlparse(self.path).query).get("address") or [""])[0]
            try:
                payload = refresh_mint_ohlcv(address)
            except Exception:
                logger.exception("failed to refresh ohlcv")
                self._send(500, "application/json", b'{"error":"failed to refresh ohlcv"}')
                return
            if payload is None:
                self._send(404, "application/json", b'{"error":"ohlcv not found"}')
                return
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(payload).encode("utf-8"),
                cache=False,
            )
            return
        if path == "/api/backtest/refresh":
            try:
                payload = start_candle_refresh()
            except Exception:
                logger.exception("failed to start candle refresh")
                self._send(500, "application/json", b'{"error":"failed to start refresh"}')
                return
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(payload).encode("utf-8"),
                cache=False,
            )
            return
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
