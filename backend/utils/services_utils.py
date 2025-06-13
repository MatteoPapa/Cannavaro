# utils/services_utils.py

import yaml
import io
import re
import os
from utils.logging_utils import log

def initialize_services(ssh, config, services_yaml_path):
    log.info("🔧 Initializing services...")
    discovered_services = list_vm_services_with_ports(ssh)
    if not discovered_services:
        log.warning("⚠️ No services discovered. Please ensure your VM is running Docker and has services configured.")
        return None
    log.info(f"Discovered {len(discovered_services)} services.")
    if not os.path.exists(os.path.dirname(services_yaml_path)):
        os.makedirs(os.path.dirname(services_yaml_path))
    save_services_to_yaml(discovered_services, services_yaml_path)
    config["services"] = discovered_services
    return discovered_services


def list_vm_services_with_ports(ssh, root_dir="/root"):
    stdin, stdout, stderr = ssh.exec_command(f"ls -d {root_dir}/*/")
    folders = stdout.read().decode().splitlines()

    services = []

    for folder in folders:
        folder_name = os.path.basename(folder.strip("/"))
        compose_candidates = ["docker-compose.yml", "compose.yml"]

        compose_content = None
        for candidate in compose_candidates:
            compose_path = os.path.join(folder, candidate)
            stdin, stdout, stderr = ssh.exec_command(f"cat {compose_path}")
            output = stdout.read()
            if output:
                compose_content = output.decode()
                break

        service_obj = {"name": folder_name}

        if not compose_content:
            log.warning(f"⚠️ No compose file found in {folder_name}")
            services.append(service_obj)
            continue

        try:
            compose_data = yaml.safe_load(io.StringIO(compose_content))
            services_in_compose = compose_data.get("services", {})
            extracted_ports = []
            service_names = list(services_in_compose.keys())

            for service_config in services_in_compose.values():
                ports = service_config.get("ports", [])
                for port_mapping in ports:
                    port_str = str(port_mapping).strip()
                    match = re.match(r"(?:[\d\.]+:)?(\d+):\d+", port_str)
                    if match:
                        extracted_ports.append(int(match.group(1)))

            if extracted_ports:
                service_obj["port"] = extracted_ports[0]  # Use first exposed port

            if service_names:
                service_obj["services"] = service_names

        except Exception as e:
            log.error(f"⚠️ Failed to parse compose file in {folder_name}: {e}")

        services.append(service_obj)

    return services

def save_services_to_yaml(services, path):
    formatted = []
    for s in services:
        entry = {
            "name": s.get("name"),
            "port": s.get("port") if "port" in s else None
        }
        if "services" in s:
            entry["services"] = s["services"]
        formatted.append(entry)

    with open(path, "w") as f:
        yaml.dump({"services": formatted}, f, sort_keys=False)
