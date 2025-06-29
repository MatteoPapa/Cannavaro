# unified_pcap_addon.py

from mitmproxy import ctx, http, tcp
from scapy.all import Ether, IP, TCP, Raw, PcapWriter, PcapNgWriter
import threading, datetime, time, shutil, os, logging

INTERVAL = 30  # Interval to dump PCAP files in seconds

# --- TCP/PCAP Dumper Thread ---
class Dumper(threading.Thread):
    def __init__(self, file_format, logger, service_name, dump_mode='pcap'):
        super().__init__(daemon=True)
        self.file_format = file_format
        self.logger = logger
        self.service_name = service_name
        self.dump_mode = dump_mode
        self.lock = threading.Lock()
        self.lock.acquire()

    def open(self, file):
        self.file = file
        if self.dump_mode == 'pcapng':
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
            tmp_file = f"/tmp/{self.service_name}_{os.path.basename(file)}.tmp"
            self.open(tmp_file)
            self.lock.release()
            time.sleep(INTERVAL)
            self.lock.acquire()
            self.close()
            shutil.move(tmp_file, file)
            self.logger.info(f"[{self.service_name}] PCAP dumped: {file}")


# --- TCP Packet Synthesizer ---
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
        s, d, sp, dp = (self.src, self.dst, self.sport, self.dport) if client else (self.dst, self.src, self.dport, self.sport)
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
        self.write_packet(self.seq, self.ack, client=True, mode='FA')
        self.seq += 1
        self.write_packet(self.ack, self.seq, client=False, mode='A')
        self.write_packet(self.ack, self.seq, client=False, mode='FA')
        self.ack += 1
        self.write_packet(self.seq, self.ack, client=True, mode='A')

    def add_packet(self, data, client=True):
        self.write_packet(self.seq, self.ack, client=client, data=data, mode='PA')
        self.seq, self.ack = self.ack, self.seq + len(data)
        self.client = client


# --- Mitmproxy Addon ---
class UnifiedDumpAddon:
    def __init__(self):
        self.logger = None
        self.dumper = None
        self.connections = {}

    def load(self, loader):
        loader.add_option(
            name="pcap_path",
            typespec=str,
            default="/tmp/pcaps",
            help="Directory to store PCAP files",
        )
        loader.add_option(
            name="service_name",
            typespec=str,
            default="default_service",
            help="Service name for labeling dumps and logs",
        )

    def configure(self, updated):
        path = ctx.options.pcap_path
        service_name = ctx.options.service_name
        os.makedirs(path, exist_ok=True)

        if not self.logger:
            self.logger = logging.getLogger(f"pcapdump.{service_name}")
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
            self.logger.addHandler(handler)

        if not self.dumper:
            pcap_file_format = os.path.join(path, f"{service_name}_%Y%m%d_%H%M%S.pcap")
            self.dumper = Dumper(pcap_file_format, self.logger, service_name)
            self.dumper.start()

    def request(self, flow: http.HTTPFlow):
        key = (flow.client_conn.id, flow.server_conn.id)
        tcpdump = TCPDump(
            self.dumper,
            flow.client_conn.address[0],
            flow.server_conn.address[0],
            flow.client_conn.address[1],
            flow.server_conn.address[1],
        )

        http_request_line = f"{flow.request.method} {flow.request.path} {flow.request.http_version}\r\n".encode()
        http_headers = b"".join(f"{k}: {v}\r\n".encode() for k, v in flow.request.headers.items())
        http_body = flow.request.raw_content or b""
        http_payload = http_request_line + http_headers + b"\r\n" + http_body
        tcpdump.add_packet(http_payload, client=True)
        self.connections[key] = tcpdump

    def response(self, flow: http.HTTPFlow):
        key = (flow.client_conn.id, flow.server_conn.id)
        tcpdump = self.connections.pop(key, None)
        if tcpdump:
            http_response_line = f"{flow.response.http_version} {flow.response.status_code} {flow.response.reason}\r\n".encode()
            http_headers = b"".join(f"{k}: {v}\r\n".encode() for k, v in flow.response.headers.items())
            http_body = flow.response.raw_content or b""
            http_payload = http_response_line + http_headers + b"\r\n" + http_body
            tcpdump.add_packet(http_payload, client=False)
            tcpdump.close()

    def tcp_start(self, flow: tcp.TCPFlow):
        key = (flow.client_conn.id, flow.server_conn.id)
        self.logger.info(f"[{ctx.options.service_name}] TCP START {key}")
        self.connections[key] = TCPDump(
            self.dumper,
            flow.client_conn.address[0],
            flow.server_conn.address[0],
            flow.client_conn.address[1],
            flow.server_conn.address[1],
        )

    def tcp_message(self, flow: tcp.TCPFlow):
        key = (flow.client_conn.id, flow.server_conn.id)
        tcpdump = self.connections.get(key)
        if tcpdump:
            tcpdump.add_packet(flow.message.content, client=flow.message.from_client)

    def tcp_end(self, flow: tcp.TCPFlow):
        key = (flow.client_conn.id, flow.server_conn.id)
        tcpdump = self.connections.pop(key, None)
        if tcpdump:
            tcpdump.close()
            self.logger.info(f"[{ctx.options.service_name}] TCP END {key}")


addons = [UnifiedDumpAddon()]
