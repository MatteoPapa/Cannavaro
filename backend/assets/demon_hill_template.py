import importlib
import socket, threading
import os, sys, re
import logging
import random, string
import time
##############################   CONFIG   ##############################


LOG_LEVEL = 'info'

FROM_PORT = {{FROM_PORT}} # type: ignore
TO_PORT = {{TO_PORT}} # type: ignore

SERVER_HISTORY_SIZE = 1024 * 1024
CLIENT_HISTORY_SIZE = 1024 * 1024


FLAG_LEN = 32
FLAG_REGEX = rb'[A-Z0-9]{31}='

REGEX_MASKS = [
]

REGEX_MASKS_2 = [
	#rb'filename=".*"',
]


##############################   MAIN   ##############################

if __name__ == '__main__':
	module = __file__.split('/')[-1][:-3]
	this = importlib.import_module(module)

	if len(sys.argv) == 3:
		this.FROM_PORT = int(sys.argv[1])
		this.TO_PORT = int(sys.argv[2])

	proxy = this.TCPProxy(this.logger, '0.0.0.0', '{{TARGET_IP}}', this.FROM_PORT, this.TO_PORT)
	proxy.start()

	reload_string = this.to_rainbow('Reloading Proxy')

	while True:
		try:
			cmd = input()

			if cmd[:1] == 'q':
				os._exit(0)

			if cmd[:1] == 'r':
				this.logger.info(reload_string)
				importlib.reload(this)
				proxy.close()
				proxy.lock.acquire()
				proxy = this.TCPProxy(this.logger, '0.0.0.0', '{{TARGET_IP}}', this.FROM_PORT, this.TO_PORT)
				proxy.start()

		except KeyboardInterrupt:
			proxy.close()
			proxy.lock.acquire()
			os._exit(0)
		except Exception as e:
			this.logger.error(str(e))




##############################   UTILS   ##############################


def random_flag(length:int=FLAG_LEN-1):
	return "".join(random.choices(string.ascii_uppercase + string.digits, k=length)) + "="


def replace_flag(logger: logging.Logger, data: bytes, id: int) -> bytes:
	def callback(match_obj):
		new_flag = random_flag()
		logger.warning(f"{match_obj.group().decode()} -> {new_flag}")
		return new_flag.encode()

	logger.warning(f"Reciving Attack from {id}")
	search = re.search(FLAG_REGEX, data)
	if search:
		data = re.sub(FLAG_REGEX, callback, data)
	#else:
	#	data = b"HTTP/2 404 Not Found\n"
	return data


##############################   FILTERS   ##############################


def custom_filter(logger:logging.Logger, data:bytes, server_history:bytes, client_history:bytes, id:int) -> bytes:

	# write here

	return data


def regex_filter(logger:logging.Logger, data:bytes, server_history:bytes, client_history:bytes, id:int) -> bytes:
	for exclusion in REGEX_MASKS:
		if re.search(exclusion, client_history):
			data = replace_flag(logger, data, id)
			break
	return data

# CLIENT ------------> PROXY ------(client_filters)------> SERVER

# CLIENT <------(server_filters)------ PROXY <------------ SERVER

def regex_filter_2(logger:logging.Logger, data:bytes, server_history:bytes, client_history:bytes, id:int) -> bytes:
	for exclusion in REGEX_MASKS_2:
		res = re.search(exclusion, client_history)
		if res:
			filename = client_history[res.start():].split(b'"')[1]
			logger.critical(f"{filename}")
			if filename != b'program':
				data = replace_flag(logger, data, id)
				break
	return data

SERVER_FILTERS = [
	regex_filter,
]

CLIENT_FILTERS = [
]

##############################   LOGGER   ##############################

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


##############################   SERVER   ##############################


class Proxy2Server(threading.Thread):
	def __init__(self, logger:logging.Logger, host:str, port:int):
		super(Proxy2Server, self).__init__()
		self.logger = logger
		self.port = port
		self.host = host
		self.error = None
		self.client = None
		self.c2p = None
		self.history = b""
		self.lock = threading.Lock()
		try:
			self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			#CHANGE: Added more attempts to connect
			for attempt in range(10):
				try:
					self.server.connect((host, port))
					break
				except ConnectionRefusedError as e:
					self.error = f'{e}'
					self.logger.warning(f'{e} (attempt {attempt+1}/10)')
					time.sleep(1)
				except Exception as e:
					self.error = f'{e}'
					self.logger.critical(f'{e}')
					break
			else:
				self.logger.critical(f"Failed to connect to target server at {host}:{port} after 10 attempts.")
				self.server = None

		except ConnectionRefusedError as e:
			self.error = f'{e}'
			self.logger.warning(f'{e}')
		except Exception as e:
			self.error = f'{e}'
			self.logger.critical(f'{e}')


	def run(self):
		while True:
			try:
				data = b''
				if self.server:
					data = self.server.recv(4096)

			except OSError:
				self.close()
				self.logger.info(f"server {CYAN}{self.c2p.id}{END} exit: recive")
				sys.exit()

			if not data:
				if self.client:
					self.c2p.close()
				self.logger.info(f"server {CYAN}{self.c2p.id}{END} exit: closed")
				sys.exit()

			try:
				if len(self.history) + len(data) < SERVER_HISTORY_SIZE:
					self.history += data
				self.logger.debug(data)
				for f in SERVER_FILTERS:
					data = f(self.logger, data, self.history, self.c2p.history, self.c2p.id)
				self.c2p.lock.acquire()
				if self.client and self.server:
					self.client.sendall(data)
				self.c2p.lock.release()

			except Exception as e:
				self.logger.error(f'server[{self.port} {self.c2p.id}]: {e}')


	def close(self):
		self.logger.info(f"server {CYAN}{self.c2p.id}{END} closed")
		self.lock.acquire()
		try:
			self.server.close()
		except AttributeError:
			pass
		self.server = None
		self.lock.release()


##############################   CLIENT   ##############################


class Client2Proxy(threading.Thread):
	def __init__(self, logger:logging.Logger, host:str, port:int, sock:socket.socket):
		super(Client2Proxy, self).__init__()
		self.logger = logger
		self.port = port
		self.host = host
		self.error = None
		self.server = None
		self.p2s = None
		self.history = b""
		self.lock = threading.Lock()
		try:
			self.client, addr = sock.accept()
			client_ip, client_port = addr
			self.id = client_port
			self.logger.info(f"client {CYAN}{self.id}{END} connected")
		except OSError as e:
			self.error = f'{e}'


	def run(self):
		while True:
			try:
				data = b''
				if self.client:
					data = self.client.recv(4096)
			except OSError:
				self.close()
				self.logger.info(f"client {CYAN}{self.id}{END} exit: recive")
				sys.exit()

			if not data:
				if self.server:
					self.p2s.close()
				self.logger.info(f"client {CYAN}{self.id}{END} exit: closed")
				sys.exit()

			try:
				if len(self.history) + len(data) < CLIENT_HISTORY_SIZE:
					self.history += data
				self.logger.debug(data)
				for f in CLIENT_FILTERS:
					data = f(self.logger, data, self.p2s.history, self.history, self.id)
				self.p2s.lock.acquire()
				if self.server and self.client:
					self.server.sendall(data)
				self.p2s.lock.release()

			except Exception as e:
				self.logger.error(f'client[{self.port} {self.id}]: {e}')


	def close(self):
		self.logger.info(f"client {CYAN}{self.id}{END} closed")
		self.lock.acquire()
		try:
			self.client.close()
		except AttributeError:
			pass
		self.client = None
		self.lock.release()


##############################   PROXY   ##############################


class TCPProxy(threading.Thread):
	def __init__(self, logger:logging.Logger, from_host:str, to_host:str, from_port:int, to_port:int):
		super(TCPProxy, self).__init__()
		self.logger = logger
		self.from_host = from_host
		self.to_host = to_host
		self.from_port = from_port
		self.to_port = to_port
		self.lock = threading.Lock()


	def run(self):
		try:
			self.lock.acquire()
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.sock.bind((self.from_host, self.from_port))
			self.sock.listen(1)
			self.logger.info(f"Serving {GREEN}{self.from_port}{END} -> {GREEN}{self.to_port}{END}")
		except Exception as e:
			self.logger.critical('Error while opening Main Proxy Socket')
			self.logger.critical(f'{e}')

		while True:
			c2p = Client2Proxy(self.logger, self.from_host, self.from_port, self.sock)
			if c2p.error:
				break

			p2s = Proxy2Server(self.logger, self.to_host, self.to_port)
			if p2s.error:
				c2p.close()
				continue

			c2p.server = p2s.server
			p2s.client = c2p.client
			p2s.c2p = c2p
			c2p.p2s = p2s

			c2p.start()
			p2s.start()

		self.logger.info(f"Shutting {HIGH_RED}{self.from_port}{END} -> {HIGH_RED}{self.to_port}{END}")
		self.lock.release()


	def close(self):
		self.sock.close()
		self.sample_connection()


	def sample_connection(self):
		try:
			server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			server.connect(('127.0.0.1', self.from_port))
			server.close()
		except ConnectionRefusedError as e:
			self.logger.warning(f'{e}')
		except Exception as e:
			self.logger.critical(f'{e}')
