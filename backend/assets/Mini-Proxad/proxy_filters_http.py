import re
import string
import logging
from http.cookies import SimpleCookie
from cachetools import TTLCache
from proxad import HttpFlow, HttpResp, HttpReq


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


logger = logging.getLogger("mini-proxad")
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
if not logger.hasHandlers():
    logger.addHandler(handler)


# HTTP session tracking
TRACK_HTTP_SESSION = False
SESSION_COOKIE_NAME = "session"
SESSION_TTL = 30  # seconds
SESSION_LIMIT = 4000
ALL_SESSIONS = TTLCache(maxsize=SESSION_LIMIT, ttl=SESSION_TTL)

# How to block the attack
FLAG_REGEX = re.compile(rb"[A-Z0-9]{31}=")
FLAG_REPLACEMENT = "GRAZIEDARIO"
BLOCK_ALL_EVIL = False
BLOCKING_ERROR = """<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>"""
ERROR_RESPONSE = HttpResp(
    headers={"Content-Type": "text/html"},
    body=BLOCKING_ERROR.encode(),
    status=500,
)
INFINITE_LOADING_RESPONSE = HttpResp(
    headers={"Location": "https://stream.wikimedia.org/v2/stream/recentchange"},
    body=b"",
    status=302,
)

# Regexes
ALL_REGEXES = [rb"eviluser"]
ALL_REGEXES = list(re.compile(pattern) for pattern in ALL_REGEXES)

############ CONFIG #################

ALLOWED_HTTP_METHODS = ["GET", "POST", "PATCH", "DELETE"]
MAX_PARAMETER_AMOUNT = 10
MAX_PARAMETER_LENGTH = 10
USERAGENTS_WHITELIST = [
    r"checker",
]
USERAGENTS_WHITELIST = [re.compile(pattern) for pattern in USERAGENTS_WHITELIST]
USERAGENTS_BLACKLIST = [
    r"requests",
    r"urllib",
    r"curl",
]
USERAGENTS_BLACKLIST = [re.compile(pattern) for pattern in USERAGENTS_BLACKLIST]
ACCEPT_ENCODING_WHITELIST = [
    "gzip, deflate, zstd",
]

############ FILTERS #################


def method_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    method = req.method

    if method not in ALLOWED_HTTP_METHODS:
        logger.debug(f"Invalid method")
        return replace_flag(resp)


def params_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    params = req.uri.params

    amount = sum(max(1, len(x)) for x in params.values())

    if amount > MAX_PARAMETER_AMOUNT:
        logger.debug(f"Too many parameters: {len(params)}")
        return replace_flag(resp)

    for x in params.values():
        for param in x:
            if len(param) > MAX_PARAMETER_LENGTH:
                logger.debug(f"Parameter too long: {len(x)}")
                return replace_flag(resp)


def nonprintable_params_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    params = req.uri.params

    for x in params.values():
        for param in x:
            for c in param:
                if c not in string.printable:
                    logger.debug("Non-printable character found in parameter")
                    return replace_flag(resp)


def useragent_whitelist_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    user_agent = req.headers.get("user-agent", "")

    if not any(re.search(pattern, user_agent) for pattern in USERAGENTS_WHITELIST):
        logger.debug("Invalid User-Agent detected")
        return replace_flag(resp)


def useragent_blacklist_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    user_agent = req.headers.get("user-agent", "")

    if any(re.search(pattern, user_agent) for pattern in USERAGENTS_BLACKLIST):
        logger.debug("Invalid User-Agent detected")
        return replace_flag(resp)


def accept_encoding_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    accept_encoding = req.headers.get("accept-encoding", "")
    if accept_encoding not in ACCEPT_ENCODING_WHITELIST:
        logger.debug(f"Invalid Accept-Encoding header")
        return replace_flag(resp)


def multiple_flags_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    content = resp.body
    flags = re.findall(FLAG_REGEX, content)
    counter = len(flags)

    if counter > 1:
        logger.debug(f"Multiple flags found: {counter}")
        return replace_flag(resp)


def regex_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    if any(re.search(pattern, req.raw) for pattern in ALL_REGEXES):
        if flow.session_id:
            logger.info(f"[🔍] Regex match found in session {flow.session_id}")
            ALL_SESSIONS[flow.session_id] = True
        return replace_flag(resp)


########### UTILITY FUNCTIONS ###########


def block_response(resp):
    return ...
    # return INFINITE_LOADING_RESPONSE
    # return ERROR_RESPONSE


def replace_flag(resp):
    if BLOCK_ALL_EVIL:
        return block_response(resp)

    resp.body = re.sub(FLAG_REGEX, FLAG_REPLACEMENT.encode(), resp.body or b"")
    return resp


def find_session_id(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    h = resp.headers.get("set-cookie") or req.headers.get("cookie")
    if h:
        cookie = SimpleCookie()
        cookie.load(h)
        session_cookie = cookie.get(SESSION_COOKIE_NAME)
        if session_cookie:
            session_id = session_cookie.value
            if session_id not in ALL_SESSIONS:
                ALL_SESSIONS[session_id] = False
            logger.debug(f"Found session id: {session_id}")
            return session_id


def myfilter(flow, req, resp):
    resp.headers["ciao"] = "1"
    return resp


FILTERS = [
    # myfilter,
    regex_filter,
    # method_filter,
    # params_filter,
    # nonprintable_params_filter,
    # useragent_whitelist_filter,
    # useragent_blacklist_filter,
    # accept_encoding_filter,
    # multiple_flags_filter,
]


####################################


# Gets executed on every request / response pair
def http_filter(flow: HttpFlow, req: HttpReq, resp: HttpResp):
    if TRACK_HTTP_SESSION:
        flow.session_id = find_session_id(flow, req, resp)

    for f in FILTERS:
        result = f(flow, req, resp)
        if result is ...:
            return result
        if result:
            resp = result
    return resp


# Gets executed everytime a flow is opened
# def http_open(flow: HttpFlow):
#    pass