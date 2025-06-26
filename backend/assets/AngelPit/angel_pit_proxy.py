########## IMPORTS ##########

import logging
import re
import os
import time
import importlib
import angel_filters
from mitmproxy import http, tcp
from cachetools import TTLCache

########## LOGGER ##########

SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)

logging.Logger.success = success

class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",
        "INFO": "\033[97m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[95m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

logger = logging.getLogger("mitm_logger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)

########## FILTER HOT-RELOAD ##########

FILTERS_PATH = os.path.abspath(angel_filters.__file__)
LAST_FILTERS_MTIME = os.path.getmtime(FILTERS_PATH)

def maybe_reload_filters():
    global LAST_FILTERS_MTIME
    current_mtime = os.path.getmtime(FILTERS_PATH)
    if current_mtime != LAST_FILTERS_MTIME:
        importlib.reload(angel_filters)
        LAST_FILTERS_MTIME = current_mtime
        logger.success("[♻️] Reloaded filters.py")

########## CONTEXT WRAPPER ##########

class FlowContext:
    def __init__(self, flow):
        self.flow = flow
        self.type = "http" if hasattr(flow, "request") else "tcp"
        self.raw_request = b""
        self.raw_response = b""
        self.session_id = None

        if self.type == "http":
            request_line = f"{flow.request.method} {flow.request.path} {flow.request.http_version}\r\n".encode()
            headers = b"".join(f"{k}: {v}\r\n".encode() for k, v in flow.request.headers.items())
            body = flow.request.raw_content or b""
            self.raw_request = request_line + headers + b"\r\n" + body

            status_line = f"{flow.response.http_version} {flow.response.status_code} {flow.response.reason}\r\n".encode()
            headers = b"".join(f"{k}: {v}\r\n".encode() for k, v in flow.response.headers.items())
            body = flow.response.raw_content or b""
            self.raw_response = status_line + headers + b"\r\n" + body

            self.session_id = angel_filters.find_session_id(flow)

        elif self.type == "tcp":
            self.raw_request = b"".join(m.content for m in flow.messages if m.from_client)
            self.raw_response = b"".join(m.content for m in flow.messages if not m.from_client)

########## MAIN ADDON ##########

class ProxyAddon:
    def __init__(self):
        logger.success("[🔧] ProxyAddon initialized")

    def response(self, flow: http.HTTPFlow):
        maybe_reload_filters()
        ctx = FlowContext(flow)

        if angel_filters.TRACK_HTTP_SESSION and ctx.session_id:
            logger.debug(f"[📦] Session ID: {ctx.session_id}")
            if angel_filters.ALL_SESSIONS.get(ctx.session_id):
                angel_filters.replace_flag(ctx.flow)
                return

        try:
            for f in angel_filters.FILTERS:
                f(ctx)
        except Exception as e:
            logger.error(f"[❌] Filter error: {e}")

    def tcp_message(self, flow: tcp.TCPFlow):
        maybe_reload_filters()
        ctx = FlowContext(flow)
        logger.info(f"[📥] TCP message ({len(flow.messages)} messages)")

        try:
            for f in angel_filters.FILTERS:
                f(ctx)
        except Exception as e:
            logger.error(f"[❌] TCP Filter error: {e}")

########## ADDON REGISTRATION ##########

addons = [ProxyAddon()]
