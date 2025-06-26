#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import glob
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# === CONFIGURATION ===
MITM_KEYLOG = Path("mitmkeys.log")
PCAP_DIR = Path("./encrypted_pcaps")
DECRYPTED_PCAPS_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("dec_pcaps")
INTERVAL = 10  # seconds
INTERFACE = "any"
PORT = sys.argv[1] if len(sys.argv) > 1 else "5001"

LABELS = {
    "CLIENT_RANDOM",
    "CLIENT_EARLY_TRAFFIC_SECRET",
    "CLIENT_HANDSHAKE_TRAFFIC_SECRET",
    "SERVER_HANDSHAKE_TRAFFIC_SECRET",
    "CLIENT_TRAFFIC_SECRET_0",
    "SERVER_TRAFFIC_SECRET_0",
    "EARLY_EXPORTER_SECRET",
    "EXPORTER_SECRET",
}

KEYLOG_RE = re.compile(
    fr'({"|".join(LABELS)}) ([0-9a-fA-F]{{64}}) ([0-9a-fA-F]{{64,128}})'
)

# === UTILS ===

def extract_pcap_randoms(pcap: Path) -> list:
    cmd = f"tshark -r {pcap} -Y tls.handshake.type==1 -T fields -e tls.handshake.random"
    print(f"[>] Running: {cmd}")  # verbose
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            check=True
        )
        return [r for r in proc.stdout.split() if len(r) == 64]
    except subprocess.CalledProcessError as e:
        print(f"[!] tshark failed:\nCommand: {e.cmd}\nExit code: {e.returncode}\nSTDERR:\n{e.stderr}")
        raise
    except Exception as e:
        print(f"[!] Unexpected error while running tshark: {e}")
        raise

def extract_keylog_randoms(keylog: Path, pcap_randoms: list) -> list:
    results = []
    with open(keylog) as f:
        for line in f:
            match = KEYLOG_RE.fullmatch(line.strip())
            if match and match.group(2) in pcap_randoms:
                results.append(line)
    return results

def inject_secrets(pcap: Path, keylog: Path) -> None:
    try:
        pcap_randoms = extract_pcap_randoms(pcap)
        keylog_randoms = extract_keylog_randoms(keylog, pcap_randoms)

        if not keylog_randoms:
            print("[!] No matching secrets found in keylog. Skipping decryption.")
            return

        DECRYPTED_PCAPS_PATH.mkdir(parents=True, exist_ok=True)
        fullPath = DECRYPTED_PCAPS_PATH / f"service_{time.strftime('%Y%m%d_%H%M%S')}.pcap"

        with tempfile.NamedTemporaryFile(mode='w+') as tmp:
            tmp.write(''.join(keylog_randoms))
            tmp.flush()
            cmd = f"editcap --log-level info --discard-all-secrets --inject-secrets tls,{tmp.name} {pcap} {fullPath}"
            print(f"[>] Running: {cmd}")  # verbose
            try:
                subprocess.run(
                    shlex.split(cmd),
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"[+] Decrypted pcap saved to: {fullPath}")
                with open(keylog, 'w'):
                    pass  # Truncate
                print(f"[+] Truncated {keylog}")
            except subprocess.CalledProcessError as e:
                print(f"[!] editcap failed:\nCommand: {e.cmd}\nExit code: {e.returncode}\nSTDERR:\n{e.stderr}")
                raise
    except Exception as e:
        print(f"[!] inject_secrets() encountered an error:\n{e}")
        raise

def find_latest_pcap(pattern: str) -> Path | None:
    files = glob.glob(pattern)
    return max(files, key=os.path.getctime) if files else None

def run_tcpdump_and_decrypt():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_base = PCAP_DIR / f"capture_{timestamp}"

    print(f"[+] Capturing traffic on port {PORT} for {INTERVAL} seconds -> {file_base}_00000.pcap")

    tcpdump_cmd = [
        "tcpdump",
        "-i", INTERFACE,
        "tcp", "port", PORT,
        "-G", str(INTERVAL),
        "-W", "1",
        "-w", f"{file_base}_%Y%m%d_%H%M%S.pcap"
    ]
    print(f"[>] Running tcpdump: {' '.join(tcpdump_cmd)}")  # verbose

    proc = subprocess.Popen(tcpdump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    try:
        proc.wait()
        stderr_output = proc.stderr.read().decode()
        if proc.returncode != 0:
            print(f"[!] tcpdump exited with code {proc.returncode}\nSTDERR:\n{stderr_output}")
    except KeyboardInterrupt:
        print("[!] Ctrl+C received, stopping tcpdump.")
        proc.send_signal(signal.SIGINT)
        proc.wait()
        raise
    except Exception as e:
        print(f"[!] Error while running tcpdump: {e}")
        raise

    pcap_file = find_latest_pcap(str(file_base) + "_*.pcap")
    if not pcap_file:
        print("[!] No pcap file found after tcpdump.")
        return

    print(f"[+] Decrypting {pcap_file}")
    try:
        inject_secrets(Path(pcap_file), MITM_KEYLOG)
        print(f"[+] Decryption complete. Removing original pcap: {pcap_file}")
        os.remove(pcap_file)
    except Exception as e:
        print(f"[!] Decryption error: {e}")

# === MAIN ===

def main():
    print("[*] Starting automated capture-decrypt loop.")
    PCAP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            run_tcpdump_and_decrypt()
    except KeyboardInterrupt:
        print("\n[!] Stopping the loop.")
    except Exception as e:
        print(f"[!] Fatal error in main loop: {e}")

if __name__ == "__main__":
    main()
