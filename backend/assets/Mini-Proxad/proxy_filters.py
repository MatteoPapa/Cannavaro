import re, uuid
import types, typing
import sys


# Use a fake python module to hold state between file reloads
def make_state() -> types.ModuleType:
    state = types.ModuleType("proxy_state")
    return state


# Import the fake python module
# Instead of using global variables use state.VAR
state = sys.modules.setdefault("proxy_state", make_state())


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


# HTTP session tracking
# from cachetools import TTLCache
# TRACK_HTTP_SESSION = False
# SESSION_COOKIE_NAME = "session"
# SESSION_TTL = 30  # seconds
# SESSION_LIMIT = 4000
# ALL_SESSIONS = TTLCache(maxsize=SESSION_LIMIT, ttl=SESSION_TTL)


# Utilities functions start


# Compile a regex
def regex(pattern: bytes):
    return re.compile(pattern)


# Utilities functions end

FLAG_REGEX = regex(rb"[A-Z0-9]{31}=")
FLAG_REPLACEMENT = "GRAZIEDARIO"


ALL_REGEXES = [rb"evil"]
COMPILED_REGEXES = [regex(pattern) for pattern in ALL_REGEXES]


def check_is_evil(id, chunk, client_history, server_history):
    return any(re.search(pattern, client_history) for pattern in COMPILED_REGEXES)


def replace_flag(id, chunk, client_history, server_history):
    return re.sub(FLAG_REGEX, FLAG_REPLACEMENT.encode(), chunk)


def replace_when_evil(id, chunk, client_history, server_history):
    if check_is_evil(id, chunk, client_history, server_history):
        return replace_flag(id, chunk, client_history, server_history)


def kill_when_evil(id, chunk, client_history, server_history):
    if check_is_evil(id, chunk, client_history, server_history):
        return ...


# Custom filters start


CLIENT_FILTERS: list[FilterType] = []

SERVER_FILTERS: list[FilterType] = [kill_when_evil]

# Custom filters end


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
        outcome = f(id, current, client_history, server_history)
        if outcome is ...:
            return ...
        if outcome is not None:
            current = outcome
    return current


def server_filter_history(
    id: uuid.UUID, chunk: bytes, client_history: bytes, server_history: bytes
) -> FilterOutput:
    return run_filters(id, chunk, client_history, server_history, SERVER_FILTERS)


def client_filter_history(
    id: uuid.UUID, chunk: bytes, client_history: bytes, server_history: bytes
) -> FilterOutput:
    return run_filters(id, chunk, client_history, server_history, CLIENT_FILTERS)