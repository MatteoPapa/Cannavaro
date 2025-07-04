import os
import time
from datetime import datetime
from scapy.all import wrpcap, rdpcap, Ether, IP, TCP, Raw, PacketList
from scapy.utils import RawPcapReader, PcapWriter
from mitmproxy import ctx, http
import logging
import threading
import sys 
import gc

# ==== Configuration ====
MTU = 1400
SEQ_START_CLIENT = 1000
SEQ_START_SERVER = 100000
DUMP_INTERVAL_SECONDS = 20
CLIENT_TIMEOUT_SECONDS = 60  # TTL for client cleanup

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
        self._merge_thread = threading.Thread(target=self._merge_worker, daemon=True)
        self._merge_event = threading.Event()

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
        self._merge_thread.start()

    def configure(self, updated):
        self.pcap_path = ctx.options.pcap_path
        self.service_name = ctx.options.service_name
        self.temp_dir = os.path.join(self.pcap_path, "tmp")

        os.makedirs(self.temp_dir, exist_ok=True)

        print(f"\U0001F4C2 PCAP path set to: {self.pcap_path}")
        print(f"\U0001F527 Service name set to: {self.service_name}")
        print(f"\U0001F4E6 PCAP Dumper initialized for service: {self.service_name}")

        if not self._is_running:
            self._is_running = True
            thread = threading.Thread(target=self._periodic_dumper, daemon=True)
            thread.start()
            self._merge_thread.start()

    def done(self):
        self._is_running = False
        self._merge_event.set()

    def _periodic_dumper(self):
        while self._is_running:
            time.sleep(DUMP_INTERVAL_SECONDS)
            try:
                print(f"⏳ Periodic PCAP dump at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                self._flush_active_streams()
                self._cleanup_expired_clients()
                self._merge_event.set()
                gc.collect()
            except Exception as e:
                print(f"❌ Error during periodic PCAP dump: {e}")

    def _merge_worker(self):
        while self._is_running:
            self._merge_event.wait()
            self._merge_event.clear()
            try:
                self._concatenate_pcaps()
            except Exception as e:
                logger.warning(f"❌ Merge thread failed: {e}")

    def _cleanup_expired_clients(self):
        now = time.time()
        expired_ids = []
        for client_id, stream in self.client_streams.items():
            if now - stream["start_time"] > CLIENT_TIMEOUT_SECONDS:
                expired_ids.append(client_id)
        for client_id in expired_ids:
            logger.info(f"🧹 Cleaning up expired client: {client_id}")
            stream = self.client_streams.pop(client_id, None)
            if stream and stream['flows']:
                packets = self._build_tcp_stream(stream['client_addr'], stream['server_addr'], stream['flows'])
                self._save_temp_pcap(packets, stream['client_addr'])

    def client_connected(self, client):
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
        stream = self.client_streams.pop(client.id, None)
        if not stream or not stream["flows"]:
            return

        client_addr = stream["client_addr"]
        server_addr = stream["server_addr"]
        flows = stream["flows"]

        packets = self._build_tcp_stream(client_addr, server_addr, flows)
        self._save_temp_pcap(packets, client_addr)
        del flows
        del packets

    def _save_temp_pcap(self, packets, client_addr):
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

            flows_to_dump = list(stream["flows"])
            packets = self._build_tcp_stream(
                stream["client_addr"],
                stream["server_addr"],
                flows_to_dump
            )
            self._save_temp_pcap(packets, stream["client_addr"])

            stream["flows"].clear()
            del flows_to_dump
            del packets

    def _concatenate_pcaps(self):
        files = [os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir) if f.endswith(".pcap")]
        if not files:
            return

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.pcap_path, f"{self.service_name}_{ts}.pcap")

        try:
            writer = None
            for f in sorted(files):
                try:
                    for pkt_data, pkt_metadata in RawPcapReader(f):
                        if writer is None:
                            writer = PcapWriter(output_path, append=False, sync=True)
                        writer.write(pkt_data)
                except Exception as e:
                    logger.warning(f"⚠️ Could not read {f}: {e}")
            if writer:
                writer.close()
            logger.info(f"📤 Merged PCAP written: {output_path}")
        except Exception as e:
            logger.exception("❌ Failed to write merged PCAP")

        # Clean up temp files
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

        packets.append(self._pkt(c_ip, s_ip, c_port, s_port, seq_c, 0, "S", t))
        packets.append(self._pkt(s_ip, c_ip, s_port, c_port, seq_s, seq_c + 1, "SA", t + delay))
        packets.append(self._pkt(c_ip, s_ip, c_port, s_port, seq_c + 1, seq_s + 1, "A", t + 2 * delay))

        seq_c += 1
        seq_s += 1
        t += 3 * delay

        for flow in flows:
            request_data = self._build_http_request(flow.request)
            response_data = self._build_http_response(flow.response) if flow.response else b""

            offset = 0
            while offset < len(request_data):
                chunk = request_data[offset:offset + MTU]
                packets.append(self._pkt(c_ip, s_ip, c_port, s_port, seq_c, ack_c, "PA", t, chunk))
                seq_c += len(chunk)
                offset += len(chunk)
                t += delay

            offset = 0
            while offset < len(response_data):
                chunk = response_data[offset:offset + MTU]
                packets.append(self._pkt(s_ip, c_ip, s_port, c_port, seq_s, seq_c, "PA", t, chunk))
                seq_s += len(chunk)
                offset += len(chunk)
                t += delay

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
