import re
import uuid
import types
import typing
import sys
import traceback


# Use a fake python module to hold state between file reloads
# When reloaded it will import the fake python module
# Instead of using global variables use state.VAR
state = sys.modules.setdefault("proxy_state", types.ModuleType("proxy_state"))


# Filters should return one the following values
# bytes          -> the chunk will be replaced
# None           -> same as returning the original chunk
# Ellipsis (...) -> kill the flow
FilterOutput = bytes | None | types.EllipsisType

# Filter will receive as arguments the values
# 1 parameter -> flow id (UUID4)
# 2 parameter -> current chunk (bytes)
# 3 parameter -> client history (bytes)
# 4 parameter -> server history (bytes)
FilterType = typing.Callable[[uuid.UUID, bytes, bytes, bytes], FilterOutput]


# ------------------------------------------------------------------------------------------------ #


# HTTP session tracking
HTTP_SESSION_TRACK = False
HTTP_SESSION_COOKIE = "session"
HTTP_SESSION_TTL = 30  # seconds
HTTP_SESSION_LIMIT = 4000


# Regexes
FLAG_REGEX = re.compile(rb"[A-Z0-9]{31}=")
FLAG_REPLACEMENT = b"GRAZIEDARIO"


# Used to detect evil connections (check_is_evil)
ALL_REGEXES = [rb"evil"]


# Blacklist and whitelist of user-agents (regexes!)
USERAGENTS_WHITELIST = [r"CHECKER"]
USERAGENTS_BLACKLIST = [r"requests"]


# ------------------------------------------------------------------------------------------------ #


COMPILED_REGEXES = [re.compile(pattern) for pattern in ALL_REGEXES]

COMPILED_WHITELIST = [
    re.compile(rf"(?i:User-Agent):\s*{pattern}\r\n".encode())
    for pattern in USERAGENTS_WHITELIST
]

COMPILED_BLACKLIST = [
    re.compile(rf"(?i:User-Agent):\s*{pattern}\r\n".encode())
    for pattern in USERAGENTS_BLACKLIST
]


# This filter always replaces the flag, combine it
def replace_flag(id, chunk, client_history, server_history):
    return re.sub(FLAG_REGEX, FLAG_REPLACEMENT, chunk)


# This filter always kills the connection, combine it
def kill(*_rest):
    return ...


# This filter always sends an error, combine it
def send_error(*_rest):
    return b"Internal Server Error\r\n"


# ------------------------------------------------------------------------------------------------ #


# Check if any of the patterns in ALL_REGEXES match the client_history
def check_is_evil(id, chunk, client_history, server_history):
    return any(re.search(pattern, client_history) for pattern in COMPILED_REGEXES)


# If the connection is recognized as evil, call DEFAULT_FILTER
def default_on_evil(id, chunk, client_history, server_history):
    if check_is_evil(id, chunk, client_history, server_history):
        return DEFAULT_FILTER(id, chunk, client_history, server_history)


def whitelist_useragent(id, chunk, client_history, server_history):
    if not any(re.search(ua, chunk) for ua in COMPILED_WHITELIST):
        print("Blocked or missing User-Agent")
        return DEFAULT_FILTER(id, chunk, client_history, server_history)


def blacklist_useragent(id, chunk, client_history, server_history):
    if any(re.search(ua, chunk) for ua in COMPILED_BLACKLIST):
        print("Blacklisted User-Agent")
        return DEFAULT_FILTER(id, chunk, client_history, server_history)


# Custom filters start


def myfilter(id, chunk, client_history, server_history):
    return None


# ...


DEFAULT_FILTER: FilterType = kill


# Filters for the messages sent from the client to the server (incoming)
CLIENT_FILTERS: list[FilterType] = []

# Filters for the messages sent from the server to the client (outgoing)
SERVER_FILTERS: list[FilterType] = [default_on_evil]


# ------------------------------------------------------------------------------------------------ #


# Exception handling
SKIP_ERROR = True  # skip filter if exception was raised
PRINT_ERROR = True  # print traceback of exceptions


if HTTP_SESSION_TRACK and not hasattr(state, "HTTP_SESSIONS"):
    state.HTTP_SESSIONS = __import__("cachetools").TTLCache(
        maxsize=HTTP_SESSION_LIMIT, ttl=HTTP_SESSION_TTL
    )


# Generic filter runner
def run_filters(
    id: uuid.UUID,
    chunk: bytes,
    client_history: bytes,
    server_history: bytes,
    filters: list[FilterType],
) -> FilterOutput:
    current = chunk
    for f in filters:
        try:
            outcome = f(id, current, client_history, server_history)
            if outcome is ...:
                return ...
            if outcome is not None:
                current = outcome
        except Exception as e:
            if PRINT_ERROR:
                traceback.print_exc()
            if not SKIP_ERROR:
                break
    return current


# Filter for the incoming messages
def client_filter_history(
    id: uuid.UUID, chunk: bytes, client_history: bytes, server_history: bytes
) -> FilterOutput:
    if HTTP_SESSION_TRACK:
        pass
    return run_filters(id, chunk, client_history, server_history, CLIENT_FILTERS)


# Filter for the outgoing messages
def server_filter_history(
    id: uuid.UUID, chunk: bytes, client_history: bytes, server_history: bytes
) -> FilterOutput:
    if HTTP_SESSION_TRACK:
        pass
    return run_filters(id, chunk, client_history, server_history, SERVER_FILTERS)