from importlib import import_module
import socket, select, threading
import os, shutil, resource, sys, re, json
import logging
import random, string
import requests, datetime, time
import base64
import importlib
import ssl
from collections import UserDict
from scapy.all import PcapNgWriter, PcapWriter, Ether, IP, IPv6, TCP, Raw

#PLACEHOLDER_FOR_CANNAVARO_DONT_TOUCH_THIS_LINE
##############################   SETTINGS   ##############################


LOG_LEVEL = 'info'
DEV = False

IPV6 = False
if IPV6:
	INADDR_ANY = '::'
	LOCALHOST = '::1'
else:
	INADDR_ANY = '0.0.0.0'
	LOCALHOST = '127.0.0.1'


FROM_ADDR = INADDR_ANY
TO_ADDR = "{{TARGET_IP}}" # type: ignore

FROM_PORT = {{FROM_PORT}} # type: ignore
TO_PORT = {{TO_PORT}} # type: ignore

# SSL Configuration (Pay attention to the paths)
SSL = {{SSL_ENABLED}} # type: ignore
SSL_KEYFILE = "./certs/server-key.pem"
SSL_CERTFILE = "./certs/server-cert.pem"
SSL_CA_CERT = "./certs/ca-cert.pem"
ALLOWED_PROTOCOLS = ['http/1.1'] # type: ignore

DUMP = SSL
DUMP_MODE = 'pcap'
PCAPS_DIR = '/root/pcaps/service/'
if DUMP and not os.path.exists(PCAPS_DIR):
	os.makedirs(PCAPS_DIR)
	
DUMP_FORMAT = f"{PCAPS_DIR}service_{TO_PORT}_%Y-%m-%d_%H.%M.%S.pcap"
DUMP_ROUND = 60

ULIMIT = 16384

HISTORY_MAX_SIZE = 1024 * 1024

FLAG_LEN = 32
FLAG_REGEX = rb'[A-Z0-9]{31}='
FLAG_REPLACEMENT = 'GRAZIEDARIO'
BLOCK_ALL_EVIL_REQUESTS = False #Not only flag replacements, but also other requests that match the regexes

REGEX_MASKS = [
]
REGEX_MASKS_2 = [
]

#PLACEHOLDER_FOR_CANNAVARO_DONT_TOUCH_THIS_LINE
##############################   SETUP   ##############################


if DUMP_MODE == 'auto':
	DUMP_MODE = DUMP_FORMAT.split('.')[-1]


##############################   COLORS   ##############################



END				= "\033[0m"

BLACK			= "\033[30m"
RED				= "\033[31m"
GREEN			= "\033[32m"
YELLOW			= "\033[33m"
BLUE			= "\033[34m"
PURPLE			= "\033[35m"
CYAN			= "\033[36m"
GREY			= "\033[90m"

HIGH_RED		= "\033[91m"
HIGH_GREEN		= "\033[92m"
HIGH_YELLOW		= "\033[93m"
HIGH_BLUE		= "\033[94m"
HIGH_PURPLE		= "\033[95m"
HIGH_CYAN		= "\033[96m"


##############################   MAIN   ##############################


if __name__ == '__main__':
	module = __file__.split('/')[-1][:-3]
	dh = import_module(module)

	proxy = dh.TCPProxy(dh.logger, dh.FROM_ADDR, dh.TO_ADDR, dh.FROM_PORT, dh.TO_PORT)
	proxy.start()

	proxy.lock.acquire()
	if not proxy.sock:
		os._exit(0)
	proxy.lock.release()

	if dh.DUMP:
		dh.DUMPER.start()

	while True:
		try:
			cmd = input()
			ret = dh.execute_command(dh, proxy, cmd)
			if type(ret) is dh.TCPProxy:
				proxy = ret

		except KeyboardInterrupt:
			proxy.exit()
		except Exception as e:
			dh.logger.error(str(e))


##############################   LOG   ##############################


class CustomFormatter(logging.Formatter):
	fmt = "[%(asctime)s] %(levelname)s: %(message)s"
	FORMATS = {
		logging.DEBUG: GREY + fmt + END,
		logging.INFO: GREY + "[%(asctime)s] " + END + "%(levelname)s: %(message)s",
		logging.WARNING: YELLOW + "[%(asctime)s] %(levelname)s: " + HIGH_YELLOW + "%(message)s" + END,
		logging.ERROR: RED + fmt + END,
		logging.CRITICAL: HIGH_RED + fmt + END,
	}

	def format(self, record):
		log_fmt = self.FORMATS.get(record.levelno, self.fmt)
		formatter = logging.Formatter(log_fmt)
		return formatter.format(record)


def to_rainbow(s: str) -> str:
	rainbow = [HIGH_PURPLE, HIGH_BLUE, HIGH_CYAN, HIGH_GREEN, HIGH_YELLOW, YELLOW, RED]
	colors = len(rainbow)
	i = 0
	res = ''
	for char in s:
		res += rainbow[i] + char
		i = (i + 1) % colors
	res += END
	return res


levels = {
	'debug': logging.DEBUG,
	'info': logging.INFO,
	'warning': logging.WARNING,
	'error': logging.ERROR,
	'critical': logging.CRITICAL,
}
log_level = levels.get(LOG_LEVEL.lower(), logging.INFO)


logger = logging.getLogger('demologger')
logger.handlers.clear()
custom_handler = logging.StreamHandler()
custom_handler.setLevel(log_level)
custom_handler.setFormatter(CustomFormatter())
logger.addHandler(custom_handler)
logger.setLevel(log_level)


def change_loglevel(direction):
	global levels, log_level, logger
	levels_values = list(levels.values())
	levels_labels = list(levels.keys())
	current_level_index = levels_values.index(log_level)
	current_level = levels_labels[current_level_index]
	if direction > 0:
		if current_level_index < len(levels_values) - 1:
			current_level_index += direction
	else:
		if current_level_index > 0:
			current_level_index += direction
	new_level = levels_values[current_level_index]
	new_level_label = levels_labels[current_level_index]
	logger.critical(f"{HIGH_CYAN}{current_level}{END} -> {GREEN}{new_level_label}{END}")
	log_level = new_level
	logger.setLevel(log_level)


def loglevel_up():
	change_loglevel(-1)


def loglevel_down():
	change_loglevel(+1)


##############################   UTILS   ##############################


def replace_flag(logger: logging.Logger, data: bytes, id: str) -> bytes:
	def callback(match_obj):
		new_flag = FLAG_REPLACEMENT
		logger.warning(f"{match_obj.group().decode()} -> {new_flag}")
		return new_flag.encode()

	logger.warning(f"Reciving Attack from {id}")
	search = re.search(FLAG_REGEX, data)
	if search:
		data = re.sub(FLAG_REGEX, callback, data)
	elif BLOCK_ALL_EVIL_REQUESTS:
		data = b"HTTP/1.1 500 Internal Server Error\r\n\r\n"
	return data


##############################   HISTORY   ##############################


class History():
	def __init__(self):
		self.data = b""
		self.lengths = [0]
		self.len = 0


	def add(self, data: bytes):
		length = len(data)
		if self.len + length > HISTORY_MAX_SIZE:
			return
		self.len += length
		self.lengths.append(self.len)
		self.data += data


##############################   HTTP   ##############################


HEADER = re.compile(r'([^:]+):\s+(.+)')
REQUEST = re.compile(r"(\w+)\s+(.+)\s+HTTP\/(\d\.\d|\d)")
RESPONSE = re.compile(r"HTTP\/(\d\.\d|\d)\s+(\d+)\s+(.+)")



class MalformedHeaderException(Exception):
	def __init__(self, message):
		custom_msg = f'MalformedHeaderException: {message}'
		super().__init__(custom_msg)


class MalformedRequestLineException(Exception):
	def __init__(self, message):
		custom_msg = f'MalformedRequestLineException: {message}'
		super().__init__(custom_msg)


class MalformedResponseLineException(Exception):
	def __init__(self, message):
		custom_msg = f'MalformedResponseLineException: {message}'
		super().__init__(custom_msg)


class HTTPHeaders(UserDict):
	def __init__(self, data: bytes) -> None:
		self.data: dict = {}
		for line in data.split(b'\n'):
			line = line.strip().decode()
			if not line:
				break
			match = HEADER.match(line)
			if not match:
				raise MalformedHeaderException(line)
			key: str = match.group(1)
			value: str = match.group(2)
			self[key] = value

	def __getitem__(self, item: str) -> str:
		return self.data[item.lower()]

	def __setitem__(self, item: str, value: str) -> None:
		self.data[item.lower()] = value



class HTTPPayload:
	def __init__(self, data: bytes) -> None:
		self.headers: HTTPHeaders = HTTPHeaders(data)
		self.body: bytes = b''
		if "content-length" in self.headers:
			self.body = data.split(b'\r\n\r\n', 1)[1]

	def __bytes__(self) -> bytes:
		result = bytearray()
		for key, value in self.headers.items():
			result.extend(f"{key}: {value}\r\n".encode())
		result.extend(b"\r\n")
		if self.body:
			result.extend(self.body)
		return bytes(result)


class HTTPRequest:
	def __init__(self, data: bytes) -> None:
		if b'\n' not in data:
			raise MalformedRequestLineException(data)
		request, data = data.split(b'\n', 1)
		request = request.strip().decode()
		if not request:
			return None
		match = REQUEST.match(request)
		if match is None:
			raise MalformedRequestLineException(request)

		self.method: str = match.group(1)
		self.path: str = match.group(2)
		self.version: str = match.group(3)
		self.payload: HTTPPayload = HTTPPayload(data)

	def __bytes__(self) -> bytes:
		return (
			f"{self.method} {self.path} HTTP/{self.version}\r\n".encode()
			+ bytes(self.payload)
		)


class HTTPResponse:
	def __init__(self, data: bytes) -> None:
		if b'\n' not in data:
			raise MalformedResponseLineException(data)
		request, data = data.split(b'\n', 1)
		request = request.strip().decode()
		if not request:
			return None
		match = RESPONSE.match(request)
		if not match:
			raise MalformedResponseLineException(request)

		self.version: str = match.group(1)
		self.code: str = match.group(2)
		self.message: str = match.group(3)
		self.payload: HTTPPayload = HTTPPayload(data)

	def __bytes__(self) -> bytes:
		return (
			f"HTTP/{self.version} {self.code} {self.message}\r\n".encode()
			+ bytes(self.payload)
		)

#PLACEHOLDER_FOR_CANNAVARO_DONT_TOUCH_THIS_LINE
##############################   FILTERS   ##############################


def http_response(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:int) -> bytes:
	try:
		req = HTTPResponse(data)
		req.payload.body = replace_flag(logger, req.payload.body, id)
		return bytes(req)
	except Exception as e:
		logger.error(f'{e}')
	return data


def http_request(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:int) -> bytes:
	try:
		req = HTTPRequest(data)
		return bytes(req)
	except Exception as e:
		logger.error(f'{e}')
	return data


def client_info_filter(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:str) -> bytes:
	logger.info(f"client -> {data}")
	return data


def server_info_filter(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:str) -> bytes:
	logger.info(f"server -> {data}")
	return data


def close_filter(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:str) -> bytes:
	for exclusion in REGEX_MASKS:
		if re.search(exclusion, data):
			return False
	return data


def replace_filter(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:str) -> bytes:
	data = replace_flag(logger, data, id)
	return data


def regex_filter(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:str) -> bytes:
	for exclusion in REGEX_MASKS:
		if re.search(exclusion, client_history.data):
			data = replace_flag(logger, data, id)
			break
	return data


def empty_filter(logger:logging.Logger, data:bytes, server_history:History, client_history:History, id:str) -> bytes:

	# write here

	return data



SERVER_FILTERS = [
]

CLIENT_FILTERS = [
]

#PLACEHOLDER_FOR_CANNAVARO_DONT_TOUCH_THIS_LINE
##############################   DUMPER   ##############################


class Dumper(threading.Thread):
	def __init__(self, file_format, logger):
		super().__init__()
		self.file_format = file_format
		self.logger = logger
		self.lock = threading.Lock()
		self.lock.acquire()

	def open(self, file):
		self.file = file
		if DUMP_MODE == 'pcapng':
			self.pcap_writer = PcapNgWriter(self.file)
		else:
			self.pcap_writer = PcapWriter(self.file, append=True)

	def write(self, pkt):
		self.lock.acquire()
		self.pcap_writer.write(pkt)
		self.lock.release()

	def close(self):
		self.pcap_writer.close()

	def run(self):
		while True:
			file = datetime.datetime.now().strftime(self.file_format)
			tmp_file = f"/tmp/temp_{TO_PORT}.pcap"
			self.open(tmp_file)
			self.lock.release()
			time.sleep(DUMP_ROUND)
			self.lock.acquire()
			self.close()
			shutil.move(tmp_file, file)
			self.logger.info(f"Dumped to {file}")


class TCPDump:
	default_ack = 1_000_000
	default_seq = 1_000

	def __init__(self, dumper, src, dst, sport, dport):
		self.dumper = dumper
		self.src = src
		self.dst = dst
		self.sport = sport
		self.dport = dport
		self.seq = self.default_seq
		self.ack = 0
		self.client = False
		self.do_handshake()

	def write_packet(self, seq, ack, client=True, data=None, mode='A'):
		if client:
			s, d, sp, dp = self.src, self.dst, self.sport, self.dport
		else:
			s, d, sp, dp = self.dst, self.src, self.dport, self.sport
		if IPV6:
			pkt = Ether(src="11:11:11:11:11:11", dst="22:22:22:22:22:22") / IPv6(src=s, dst=d) / TCP(sport=sp, dport=dp, flags=mode, seq=seq, ack=ack)
		else:
			pkt = Ether(src="11:11:11:11:11:11", dst="22:22:22:22:22:22") / IP(src=s, dst=d) / TCP(sport=sp, dport=dp, flags=mode, seq=seq, ack=ack)
		if data:
			pkt /= Raw(load=data)
		self.dumper.write(pkt)

	def do_handshake(self):
		self.write_packet(self.seq, self.ack, mode='S')
		self.seq, self.ack = self.default_ack, self.seq + 1
		self.write_packet(self.seq, self.ack, client=False, mode='SA')
		self.seq, self.ack = self.ack, self.seq + 1
		self.write_packet(self.seq, self.ack)

	def close(self):
		self.write_packet(self.seq, self.ack, client=(not self.client), mode='FA')

	def add_packet(self, data, client=True):
		self.write_packet(self.seq, self.ack, client=client, data=data, mode='PA')
		self.seq, self.ack = self.ack, self.seq + len(data)
		self.client = client


DUMPER = Dumper(DUMP_FORMAT, logger)


##############################   CLIENT2SERVER   ##############################


class Client2Server(threading.Thread):
	def __init__(self, logger:logging.Logger, to_host:str, to_port:int, client_sock:socket.socket, client_id:str):
		super().__init__()
		self.logger = logger
		self.client = client_sock
		self.id = client_id
		self.client_history = History()
		self.server_history = History()
		self.error = None
		try:
			if IPV6:
				self.server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			else:
				self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			if SSL:
				context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
				context.set_alpn_protocols(['h2', 'http/1.1'])
				context.load_verify_locations(SSL_CA_CERT)
				self.server = context.wrap_socket(
					self.server,
					do_handshake_on_connect=True,
					server_hostname=to_host,
				)
			self.server.connect((to_host, to_port))

			if DUMP:
				src, sport = self.client.getpeername()[:2]
				dst, dport = self.client.getsockname()[0], self.server.getpeername()[1]
				self.dump = TCPDump(DUMPER, src, dst, sport, dport)
			else:
				self.dump = None

			self.client.setblocking(False)
			self.server.setblocking(False)
		except ConnectionRefusedError as e:
			self.error = f'{e}'
			self.logger.warning(self.error)
		except Exception as e:
			self.error = f'{e}'
			self.logger.critical(self.error)


	def exit(self, msg):
		if self.dump:
			self.dump.close()
		msg = f'{CYAN}{self.id}{END} ' + msg
		if self.client.fileno() != -1:
			self.client.close()
			msg = f'client ' + msg
			if self.server.fileno() != -1:
				msg = 'and ' + msg
		if self.server.fileno() != -1:
			self.server.close()
			msg = f'server ' + msg
		self.logger.info(f"{msg}")
		sys.exit()


	def reply(self, read:socket.socket, write:socket.socket, is_client:bool):
		try:
			if SSL:
				data = read.recv()
			else:
				data = read.recv(1024)

		except ssl.SSLError as e:
			if e.errno == ssl.SSL_ERROR_WANT_READ:
				pass
			return
		except Exception as e:
			self.exit(f'{e}')

		if not data:
			self.exit("closed")
		self.send(data, write, is_client)


	def send(self, data: bytes, write: socket.socket, is_client: bool):
		if is_client:
			self.client_history.add(data)
			filters = CLIENT_FILTERS
		else:
			self.server_history.add(data)
			filters = SERVER_FILTERS

		if self.dump:
			self.dump.add_packet(data, is_client)

		try:
			for f in filters:
				data = f(self.logger, data, self.server_history, self.client_history, self.id)
			if data is False:
				self.exit(f"{YELLOW}Force Close{END}")
			write.sendall(data)

		except Exception as e:
			self.exit(f"{e}")


	def run(self):
		socket_list = [self.client, self.server]
		while True:
			read_sockets, write_sockets, error_sockets = select.select(socket_list, [], [])
			if DEV:
				self.logger.debug(f'{read_sockets} {write_sockets} {error_sockets}')

			if self.client.fileno() == -1 or self.server.fileno() == -1:
				self.exit(f'closed during select')

			for sock in read_sockets:
				if sock == self.client:
					self.reply(self.client, self.server, True)
				elif sock == self.server:
					self.reply(self.server, self.client, False)


##############################   TCP_PROXY   ##############################


class TCPProxy(threading.Thread):
	def __init__(self, logger:logging.Logger, from_host:str, to_host:str, from_port:int, to_port:int, sock:socket.socket=None):
		super().__init__()
		self.logger = logger
		self.from_host = from_host
		self.to_host = to_host
		self.from_port = from_port
		self.to_port = to_port
		self.sock = sock
		self.is_running = True
		self.lock = threading.Lock()
		self.lock.acquire()


	def setup_socket(self):
		if IPV6:
			self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
		else:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		if SSL:
			context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
			context.set_alpn_protocols(ALLOWED_PROTOCOLS)
			context.load_cert_chain(SSL_CERTFILE, SSL_KEYFILE)
			self.sock = context.wrap_socket(
				self.sock,
				server_side=True,
				do_handshake_on_connect=True,
			)
		self.sock.bind((self.from_host, self.from_port))
		self.sock.listen(1)


	def setup(self) -> bool:
		try:
			if not self.sock:
				self.setup_socket()
				info = f"Serving {BLUE}{self.from_host}{END}:{GREEN}{self.from_port}{END}" +\
					f" -> {BLUE}{self.to_host}{END}:{GREEN}{self.to_port}{END}"
				self.logger.info(info)
			else:
				info = f"{BLUE}{self.from_host}{END}:{GREEN}{self.from_port}{END}" +\
					f" -> {BLUE}{self.to_host}{END}:{GREEN}{self.to_port}{END}"
				self.logger.info(info)
				self.logger.info(f"{to_rainbow('Proxy Successfully Reloaded')}")
			self.lock.release()
		except Exception as e:
			self.logger.critical('Error while opening Main Socket')
			self.logger.critical(f'{e}')
			self.sock.close()
			self.sock = None
			self.lock.release()
			return True
		return False


	def run(self):
		if self.setup():
			return

		while True:
			socket_list = [self.sock]
			read_sockets, write_sockets, error_sockets = select.select(socket_list, [], [])
			if DEV:
				self.logger.debug(f'{read_sockets} {write_sockets} {error_sockets}')

			if not self.is_running:
				break

			if self.sock.fileno() == -1:
				self.logger.info(f"Shutting {HIGH_RED}{self.from_port}{END} -> {HIGH_RED}{self.to_port}{END}")
				break

			if not read_sockets:
				continue

			for sock in read_sockets:
				if sock == self.sock:
					try:
						client_sock, addr = sock.accept()
						client_ip, client_port = addr[0], addr[1]
						if IPV6:
							client_id = f"[{client_ip}]:{client_port}"
						else:
							client_id = f"{client_ip}:{client_port}"
						self.logger.info(f"client {CYAN}{client_id}{END} connected")
					except ssl.SSLError as e:
						if e.errno == ssl.SSL_ERROR_EOF:
							pass
						continue
					except OSError as e:
						self.logger.error(f'{e}')
					break
			else:
				continue

			middleware = Client2Server(
				self.logger,
				self.to_host,
				self.to_port,
				client_sock,
				client_id
			)
			if not middleware.error:
				middleware.start()
		
		self.logger.info(f"{to_rainbow('Proxy Closed')}")
		#try:
		self.lock.release()
		#except RuntimeError as e: # RuntimeError: release unlocked lock
		#	logger.error(f'{e}')


	def sample_connection(self):
		try:
			if IPV6:
				server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			else:
				server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			server.connect((LOCALHOST, self.from_port))
			server.close()
		except ConnectionRefusedError as e:
			self.logger.warning(f'{e}')
		except Exception as e:
			self.logger.critical(f'{e}')


	def close(self):
		if self.sock:
			self.sock.close()
			self.sample_connection()
	

	def exit(self):
		self.lock.acquire()
		self.close()
		self.lock.acquire()
		os._exit(0)


##############################   COMMANDS   ##############################


def	quit(mdl, proxy: TCPProxy, args: list) -> None:
	if proxy:
		proxy.exit()


def reload(mdl, proxy: TCPProxy, args: list) -> dict | TCPProxy:
	if not mdl or not proxy:
		return {"status": False, "error": f"module: {mdl}, proxy: {proxy}"}
	logger.info(to_rainbow('Reloading Proxy'))
	mdl.RELOAD = True
	importlib.reload(mdl)
	tmp_sock = proxy.sock
	proxy.lock.acquire()
	proxy.is_running = False
	proxy.sample_connection()
	proxy.lock.acquire()
	proxy.lock.release()
	if SSL:
		tmp_sock.close()
		proxy = TCPProxy(logger, FROM_ADDR, TO_ADDR, FROM_PORT, TO_PORT)
	else:
		proxy = TCPProxy(logger, FROM_ADDR, TO_ADDR, FROM_PORT, TO_PORT, tmp_sock)
	proxy.start()
	return proxy


def info(mdl, proxy: TCPProxy, args: list) -> dict:
	pid = os.getpid()
	enums = len(threading.enumerate())
	logger.info(f'{HIGH_CYAN}PID{END}: {GREEN}{pid}{END}')
	logger.info(f'{HIGH_CYAN}Threads{END}: {GREEN}{enums}{END}')
	return {"status": True, "pid": pid, "enums": enums}


def log_up(mdl, proxy: TCPProxy, args: list) -> dict:
	loglevel_up()
	return {"status": True}


def log_down(mdl, proxy: TCPProxy, args: list) -> dict:
	loglevel_down()
	return {"status": True}


def ulimit(mdl, proxy: TCPProxy, args: list) -> dict:
	soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
	logger.info(f'{HIGH_GREEN}Current Limits:{HIGH_PURPLE} Soft {soft} {END}|{PURPLE} Hard {hard}{END}')
	if not len(args):
		return {"status": True, "soft": soft, "hard": hard}
	try:
		new_limit = int(args[0])
	except ValueError:
		logger.info(f'{HIGH_YELLOW}Invalid Limit: {HIGH_RED}{args[0]}{END}')
		return {"status": False, "error": "Invalid Limit"}
	if soft < new_limit:
		soft = new_limit
	if hard < new_limit:
		hard = new_limit
	try:
		resource.setrlimit(resource.RLIMIT_NOFILE,(soft,hard))
		logger.info(f'{HIGH_GREEN}New Limits:{HIGH_PURPLE} Soft {soft} {END}|{PURPLE} Hard {hard}{END}')
		return {"status": True, "soft": soft, "hard": hard}
	except (ValueError,resource.error) as e:
		logger.error(f"{e}")
		return {"status": False, "error": f"{e}"}


commands = {
	'q': quit,
	'r': reload,
	'i': info,
	'+': log_up,
	'-': log_down,
	'u': ulimit,
}


def execute_command(mdl, proxy: TCPProxy, cmd: str):
	cmd = cmd.split(' ', 1)
	args = []
	if len(cmd) > 1:
		args = cmd[1:]
	cmd = commands.get(cmd[0], None)
	if not cmd:
		return
	ret = cmd(mdl, proxy, args)
	return ret


ulimit(None, None, [str(ULIMIT)])
