import os
import shlex
from time import time
from math import modf
from struct import pack
from subprocess import Popen, PIPE
from mitmproxy import ctx
import socket  # at the top
import ipaddress
import errno

ROTATE_FLOW_COUNT = 200
DEFAULT_PCAP_FOLDER = 'pcaps'

class Exporter:
    def __init__(self):
        self.sessions = {}

    def write(self, data):
        raise NotImplementedError()

    def flush(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def header(self):
        data = pack('<IHHiIII', 0xa1b2c3d4, 2, 4, 0, 0, 0x040000, 1)
        self.write(data)

    def packet(self, src_host, src_port, dst_host, dst_port, payload):
        # Resolve hostnames to IPv4
        try:
            src_ip = str(ipaddress.IPv4Address(src_host))
        except ipaddress.AddressValueError:
            try:
                src_ip = socket.gethostbyname(src_host)
            except Exception:
                print(f"[⚠️] Cannot resolve source host: {src_host}")
                return

        try:
            dst_ip = str(ipaddress.IPv4Address(dst_host))
        except ipaddress.AddressValueError:
            try:
                dst_ip = socket.gethostbyname(dst_host)
            except Exception:
                print(f"[⚠️] Cannot resolve dest host: {dst_host}")
                return

        key = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}"
        session = self.sessions.get(key)
        if session is None:
            session = {'seq': 1}
            self.sessions[key] = session
        seq = session['seq']
        total = len(payload) + 20 + 20

        tcp_args = [src_port, dst_port, seq, 0, 0x50, 0x18, 0x0200, 0, 0]
        tcp = pack('>HHIIBBHHH', *tcp_args)
        ipv4_args = [0x45, 0, total, 0, 0, 0x40, 6, 0]
        ipv4_args.extend(map(int, src_ip.split('.')))
        ipv4_args.extend(map(int, dst_ip.split('.')))
        ipv4 = pack('>BBHHHBBHBBBBBBBB', *ipv4_args)
        link = b'\x00' * 12 + b'\x08\x00'

        usec, sec = modf(time())
        usec = int(usec * 1000000)
        sec = int(sec)
        size = len(link) + len(ipv4) + len(tcp) + len(payload)
        head = pack('<IIII', sec, usec, size, size)

        self.write(head)
        self.write(link)
        self.write(ipv4)
        self.write(tcp)
        self.write(payload)
        session['seq'] = seq + len(payload)

    def packets(self, src_host, src_port, dst_host, dst_port, payload):
        limit = 40960
        for i in range(0, len(payload), limit):
            self.packet(
                src_host, src_port,
                dst_host, dst_port,
                payload[i:i + limit]
            )

class File(Exporter):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self._open_file()

    def _open_file(self):
        if os.path.exists(self.path):
            self.file = open(self.path, 'ab')
        else:
            self.file = open(self.path, 'wb')
        self.file_inode = os.fstat(self.file.fileno()).st_ino  
        if self.file.tell() == 0:
            self.header() 

    def write(self, data):
        try:
            # Check if file was deleted (inode mismatch)
            if not os.path.exists(self.path) or os.stat(self.path).st_ino != self.file_inode:
                print(f"[⚠️] PCAP file {self.path} was deleted. Recreating it.")
                self.file.close()
                self._open_file()

            self.file.write(data)
        except OSError as e:
            if e.errno == errno.ENOENT:
                print(f"[❗] PCAP file disappeared, reopening: {self.path}")
                self._open_file()
                self.file.write(data)
            else:
                raise

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()

class Pipe(Exporter):
    def __init__(self, cmd):
        super().__init__()
        self.proc = Popen(shlex.split(cmd), stdin=PIPE)
        self.header()

    def write(self, data):
        self.proc.stdin.write(data)

    def flush(self):
        self.proc.stdin.flush()

    def close(self):
        self.proc.terminate()
        self.proc.poll()

class Addon:
    def __init__(self):
        self.exporter = None
        self.flow_count = 0
        self.max_flows = ROTATE_FLOW_COUNT
        self.output_dir = DEFAULT_PCAP_FOLDER
        self._open_new_file_called = False

    def load(self, loader):
        loader.add_option(
            name="pcap_output",
            typespec=str,
            default=DEFAULT_PCAP_FOLDER,
            help="Folder to save PCAP files"
        )

    def configure(self, updated):
        self.output_dir = ctx.options.pcap_output
        os.makedirs(self.output_dir, exist_ok=True)
        if not self._open_new_file_called:
            self._open_new_file()
            self._open_new_file_called = True

    def _open_new_file(self):
        timestamp = int(time())
        filename = os.path.join(self.output_dir, f"pcap_{timestamp}.pcap")
        self.exporter = File(filename)
        self.flow_count = 0
        print(f"[💾] Opened new PCAP: {filename}")

    def _rotate_file(self):
        if self.exporter:
            self.exporter.close()
        self._open_new_file()

    def done(self):
        if self.exporter:
            self.exporter.close()

    def response(self, flow):
        client_addr = list(flow.client_conn.address)
        server_addr = list(flow.server_conn.address)
        client_ip = client_addr[0].replace('::ffff:', '')
        server_ip = server_addr[0].replace('::ffff:', '')

        if '.' not in client_ip or '.' not in server_ip:
            return  # skip non-IPv4

        client_addr[0] = client_ip
        server_addr[0] = server_ip

        self.export_request(client_addr, server_addr, flow.request)
        self.export_response(client_addr, server_addr, flow.response)
        self.exporter.flush()

        self.flow_count += 1
        if self.flow_count >= self.max_flows:
            self._rotate_file()

    def export_request(self, client_addr, server_addr, r):
        proto = f"{r.method} {r.path} {r.http_version}\r\n"
        payload = bytearray()
        payload.extend(proto.encode('ascii'))
        payload.extend(bytes(r.headers))
        payload.extend(b'\r\n')
        payload.extend(r.raw_content)
        self.exporter.packets(*client_addr, *server_addr, payload)

    def export_response(self, client_addr, server_addr, r):
        headers = r.headers.copy()
        if r.http_version.startswith('HTTP/2'):
            headers.setdefault('content-length', str(len(r.raw_content)))
            proto = f"{r.http_version} {r.status_code}\r\n"
        else:
            headers.setdefault('Content-Length', str(len(r.raw_content)))
            proto = f"{r.http_version} {r.status_code} {r.reason}\r\n"

        payload = bytearray()
        payload.extend(proto.encode('ascii'))
        payload.extend(bytes(headers))
        payload.extend(b'\r\n')
        payload.extend(r.raw_content)
        self.exporter.packets(*server_addr, *client_addr, payload)

addons = [Addon()]
