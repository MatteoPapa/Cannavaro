import re
from cachetools import TTLCache
import logging

logger = logging.getLogger("mitm_logger")

# HTTP session tracking
TRACK_HTTP_SESSION = False
SESSION_COOKIE_NAME = "session"
SESSION_TTL = 30
SESSION_LIMIT = 4000
ALL_SESSIONS = TTLCache(maxsize=SESSION_LIMIT, ttl=SESSION_TTL)

# How to block the attack
FLAG_REGEX = rb'[A-Z0-9]{31}='
FLAG_REPLACEMENT = "GRAZIEDARIO"
BLOCK_ALL_EVIL = False
BLOCKING_ERROR = b"Internal Server Error\n"

# Regexes and User-Agent filters
ALL_REGEXES = [
    rb'evil'
]

USERAGENTS_WHITELIST = [r"CHECKER"]
USERAGENTS_BLACKLIST = [r"python-requests"]

############ FILTERS #################


def regex_filter(ctx):
    if any(re.search(reg, ctx.raw_request) for reg in ALL_REGEXES):
        if ctx.session_id:
            logger.debug(f"[🔍] Regex match found in session {ctx.session_id}")
            ALL_SESSIONS[ctx.session_id] = True
        replace_flag(ctx.flow)

def example_response_replace(ctx):
    flow = ctx.flow
    if flow.type == "http" and flow.response:
        flow.response.content = flow.response.content.replace(b"TO_REPLACE", b"PALLE")

def whitelist_useragent(ctx):
    agent = ctx.flow.request.headers.get("User-Agent", "")
    if not any(re.search(ua, agent) for ua in USERAGENTS_WHITELIST):
        logger.debug(f"Blocked or missing User-Agent: {agent}")
        replace_flag(ctx.flow)

def blacklist_useragent(ctx):
    agent = ctx.flow.request.headers.get("User-Agent", "")
    if any(re.search(ua, agent) for ua in USERAGENTS_BLACKLIST):
        logger.debug(f"Blacklisted User-Agent: {agent}")
        replace_flag(ctx.flow)


FILTERS = [
    regex_filter
]

# ------------------- CONTEXT AND FLOW REFERENCE -------------------
# ctx: FlowContext
#   - ctx.flow        → The mitmproxy flow object (http.HTTPFlow or tcp.TCPFlow)
#   - ctx.type        → "http" or "tcp"
#   - ctx.session_id  → Extracted session ID if available (e.g., from cookies)
#   - ctx.raw_request → Raw byte-string of request (headers + body)
#   - ctx.raw_response→ Raw byte-string of response (headers + body, if present)

# ctx.flow (when HTTP):
#   - flow.request.method / path / headers / raw_content
#   - flow.response.status_code / headers / raw_content

# ctx.flow (when TCP):
#   - flow.messages[] → list of TCPMessage objects
#       - .content (bytes), .from_client (bool)

# Used heavily by filters to inspect, match, and mutate traffic.
# -----------------------------------------------------------------


########### UTILITY FUNCTIONS ###########

def replace_flag(flow):
    if flow.type == "http" and flow.response:
        flow.response.status_code = 500 if BLOCK_ALL_EVIL else flow.response.status_code
        flow.response.raw_content = BLOCKING_ERROR if BLOCK_ALL_EVIL else re.sub(FLAG_REGEX, FLAG_REPLACEMENT.encode(), flow.response.content)
    elif flow.type == "tcp":
        for msg in reversed(flow.messages):
            if not msg.from_client:
                msg.content = BLOCKING_ERROR if BLOCK_ALL_EVIL else re.sub(FLAG_REGEX, FLAG_REPLACEMENT.encode(), msg.content)
                break

def find_session_id(flow):
    session_id = None

    # Try to extract from Set-Cookie in response
    for h in flow.response.headers.get_all("Set-Cookie"):
        m = re.search(rf'{SESSION_COOKIE_NAME}=([^;]+)', h)
        if m:
            session_id = m.group(1)
            ALL_SESSIONS[session_id] = False
            logger.debug(f"Tracking new session id from response: {session_id}")
            return session_id

    # Try to extract from request cookies
    cookies = flow.request.cookies.get_all(SESSION_COOKIE_NAME)
    if cookies:
        session_id = cookies[0]
        if session_id not in ALL_SESSIONS:
            ALL_SESSIONS[session_id] = False
        logger.debug(f"Found session id in request: {session_id}")
    else:
        logger.debug(f"No {SESSION_COOKIE_NAME} cookie found in request.")
        
    return session_id

##########################################