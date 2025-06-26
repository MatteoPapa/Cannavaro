import os
import shlex
from time import time
from math import modf
from struct import pack
from subprocess import Popen, PIPE

PCAP_FOLDER = 'pcaps'
ROTATE_FLOW_COUNT = 50
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
        key = '%s:%d-%s:%d' % (src_host, src_port, dst_host, dst_port)
        session = self.sessions.get(key)
        if session is None:
            session = {'seq': 1}
            self.sessions[key] = session
        seq = session['seq']
        total = len(payload) + 20 + 20

        tcp_args = [src_port, dst_port, seq, 0, 0x50, 0x18, 0x0200, 0, 0]
        tcp = pack('>HHIIBBHHH', *tcp_args)
        ipv4_args = [0x45, 0, total, 0, 0, 0x40, 6, 0]
        ipv4_args.extend(map(int, src_host.split('.')))
        ipv4_args.extend(map(int, dst_host.split('.')))
        ipv4 = pack('>BBHHHBBHBBBBBBBB', *ipv4_args)
        link = b'\x00' * 12 + b'\x08\x00'

        usec, sec = modf(time())
        usec = int(usec * 1000 * 1000)
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
            self.packet(src_host, src_port,
                        dst_host, dst_port,
                        payload[i:i + limit])

class File(Exporter):

    def __init__(self, path):
        super().__init__()
        self.path = path
        if os.path.exists(path):
            self.file = open(path, 'ab')
        else:
            self.file = open(path, 'wb')
            self.header()

    def write(self, data):
        self.file.write(data)

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

    def __init__(self, createf=None):
        self.exporter = None
        self.flow_count = 0
        self.max_flows = ROTATE_FLOW_COUNT
        self.output_dir = PCAP_FOLDER
        os.makedirs(self.output_dir, exist_ok=True)
        self._open_new_file()

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

    def load(self, entry):
        pass  # Already initialized exporter

    def done(self):
        if self.exporter:
            self.exporter.close()

    def response(self, flow):
        # Skip IPv6
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
        proto = '%s %s %s\r\n' % (r.method, r.path, r.http_version)
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
            proto = '%s %s\r\n' % (r.http_version, r.status_code)
        else:
            headers.setdefault('Content-Length', str(len(r.raw_content)))
            proto = '%s %s %s\r\n' % (r.http_version, r.status_code, r.reason)

        payload = bytearray()
        payload.extend(proto.encode('ascii'))
        payload.extend(bytes(headers))
        payload.extend(b'\r\n')
        payload.extend(r.raw_content)
        self.exporter.packets(*server_addr, *client_addr, payload)

addons = [Addon(lambda: File('output.pcap'))]
#addons = [Addon(lambda: Pipe('weer -'))]