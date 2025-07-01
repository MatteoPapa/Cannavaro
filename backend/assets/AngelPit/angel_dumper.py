import os
import time
from datetime import datetime
from scapy.all import wrpcap, rdpcap, Ether, IP, TCP, Raw, PacketList
from mitmproxy import ctx, http
import logging
import threading
import sys 

# ==== Configuration ====
MTU = 1400
SEQ_START_CLIENT = 1000
SEQ_START_SERVER = 100000
DUMP_INTERVAL_SECONDS = 20

# ==== Logging Setup ====
logging.basicConfig(
    stream=sys.stdout,  # <-- Send logs to stdout
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("PCAPDumper")


class PCAPDumper:
    def __init__(self):
        self.client_streams = {}
        self.pcap_path = None
        self.temp_dir = None
        self.service_name = None

    def load(self, loader):
        loader.add_option(
            name="pcap_path", typespec=str, default="./pcaps",
            help="Directory where merged PCAPs will be saved."
        )
        loader.add_option(
            name="service_name", typespec=str, default="myservice",
            help="Name prefix for merged PCAP files."
        )
        
        self._is_running = True
        thread = threading.Thread(target=self._periodic_dumper, daemon=True)
        thread.start()

    def configure(self, updated):
        self.pcap_path = ctx.options.pcap_path
        self.service_name = ctx.options.service_name
        self.temp_dir = os.path.join(self.pcap_path, "tmp")

        os.makedirs(self.temp_dir, exist_ok=True)

        print(f"📂 PCAP path set to: {self.pcap_path}")
        print(f"🔧 Service name set to: {self.service_name}")
        print(f"📦 PCAP Dumper initialized for service: {self.service_name}")

        if not self._is_running:
            self._is_running = True
            thread = threading.Thread(target=self._periodic_dumper, daemon=True)
            thread.start()

    def done(self):
        self._is_running = False

    def _periodic_dumper(self):
        while self._is_running:
            time.sleep(DUMP_INTERVAL_SECONDS)
            try:
                print(f"⏳ Periodic PCAP dump at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                self._flush_active_streams()     
                self._concatenate_pcaps()    
            except Exception as e:
                print(f"❌ Error during periodic PCAP dump: {e}")

    def client_connected(self, client):
        # print(f"🔗 Client connected: {client.id} ({client.address})")
        self.client_streams[client.id] = {
            "client_addr": client.address,
            "flows": [],
            "server_addr": None,
            "start_time": time.time(),
        }

    def response(self, flow: http.HTTPFlow):
        stream = self.client_streams.get(flow.client_conn.id)
        if stream:
            stream["flows"].append(flow)
            if stream["server_addr"] is None:
                stream["server_addr"] = flow.server_conn.address

    def client_disconnected(self, client):
        # print(f"🔌 Client disconnected: {client.id} ({client.address})")
        stream = self.client_streams.pop(client.id, None)
        if not stream or not stream["flows"]:
            return

        client_addr = stream["client_addr"]
        server_addr = stream["server_addr"]
        flows = stream["flows"]

        packets = self._build_tcp_stream(client_addr, server_addr, flows)
        self._save_temp_pcap(packets, client_addr)

    def _save_temp_pcap(self, packets, client_addr):
        # print(f"📥 Saving temporary PCAP for {client_addr[0]}:{client_addr[1]}")
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{client_addr[0]}_{client_addr[1]}_{ts}.pcap"
        full_path = os.path.join(self.temp_dir, filename)
        try:
            wrpcap(full_path, packets)
            logger.info(f"📥 Temp PCAP saved: {full_path}")
        except Exception as e:
            logger.exception("❌ Failed to write temporary PCAP")

    def _flush_active_streams(self):
        for client_id, stream in self.client_streams.items():
            if not stream["flows"] or stream["server_addr"] is None:
                continue

            flows_to_dump = list(stream["flows"])  # clone current flows
            packets = self._build_tcp_stream(
                stream["client_addr"],
                stream["server_addr"],
                flows_to_dump
            )
            self._save_temp_pcap(packets, stream["client_addr"])

            stream["flows"].clear()  # ✅ clear flows so they don’t get re-dumped

    def _concatenate_pcaps(self):
        files = [os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir) if f.endswith(".pcap")]
        if not files:
            return

        all_packets = PacketList()
        for f in sorted(files):
            try:
                all_packets += rdpcap(f)
            except Exception as e:
                logger.warning(f"⚠️ Could not read {f}: {e}")

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.pcap_path, f"{self.service_name}_{ts}.pcap")
        try:
            wrpcap(output_path, all_packets)
            logger.info(f"📤 Merged PCAP written: {output_path} ({len(all_packets)} packets)")
        except Exception as e:
            logger.exception("❌ Failed to write merged PCAP")

        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove temp PCAP {f}: {e}")

    def _build_tcp_stream(self, client_addr, server_addr, flows):
        packets = PacketList()
        c_ip, c_port = client_addr
        s_ip, s_port = server_addr
        seq_c = SEQ_START_CLIENT
        seq_s = SEQ_START_SERVER
        ack_c = seq_s + 1
        ack_s = seq_c + 1
        t = time.time()
        delay = 0.001

        # 3-way handshake
        packets.append(self._pkt(c_ip, s_ip, c_port, s_port, seq_c, 0, "S", t))
        packets.append(self._pkt(s_ip, c_ip, s_port, c_port, seq_s, seq_c + 1, "SA", t + delay))
        packets.append(self._pkt(c_ip, s_ip, c_port, s_port, seq_c + 1, seq_s + 1, "A", t + 2 * delay))

        seq_c += 1
        seq_s += 1
        t += 3 * delay

        for flow in flows:
            request_data = self._build_http_request(flow.request)
            response_data = self._build_http_response(flow.response) if flow.response else b""

            # Client → Server
            offset = 0
            while offset < len(request_data):
                chunk = request_data[offset:offset + MTU]
                packets.append(self._pkt(c_ip, s_ip, c_port, s_port, seq_c, ack_c, "PA", t, chunk))
                seq_c += len(chunk)
                offset += len(chunk)
                t += delay

            # Server → Client
            offset = 0
            while offset < len(response_data):
                chunk = response_data[offset:offset + MTU]
                packets.append(self._pkt(s_ip, c_ip, s_port, c_port, seq_s, seq_c, "PA", t, chunk))
                seq_s += len(chunk)
                offset += len(chunk)
                t += delay

        # FIN
        packets.append(self._pkt(c_ip, s_ip, c_port, s_port, seq_c, seq_s, "FA", t))
        t += delay
        packets.append(self._pkt(s_ip, c_ip, s_port, c_port, seq_s, seq_c + 1, "A", t))

        return packets

    def _pkt(self, src_ip, dst_ip, sport, dport, seq, ack, flags, timestamp, payload=b""):
        ether = Ether(src="aa:aa:aa:aa:aa:aa", dst="bb:bb:bb:bb:bb:bb")
        ip = IP(src=src_ip, dst=dst_ip)
        tcp = TCP(sport=sport, dport=dport, flags=flags, seq=seq, ack=ack)
        pkt = ether / ip / tcp / (Raw(load=payload) if payload else b"")
        pkt.time = timestamp
        return pkt

    def _build_http_request(self, request):
        lines = [f"{request.method} {request.path} {request.http_version}"]
        for name, value in request.headers.items(multi=True):
            lines.append(f"{name}: {value}")
        raw = "\r\n".join(lines).encode("utf-8") + b"\r\n\r\n"
        raw += request.raw_content or b""
        return raw

    def _build_http_response(self, response):
        lines = [f"{response.http_version} {response.status_code} {response.reason}"]
        for name, value in response.headers.items(multi=True):
            lines.append(f"{name}: {value}")
        raw = "\r\n".join(lines).encode("utf-8") + b"\r\n\r\n"
        raw += response.raw_content or b""
        return raw


addons = [PCAPDumper()]
