# utils/services_utils.py

import yaml
import io
import re
import os

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

        if not compose_content:
            print(f"⚠️ No compose file found in {folder_name}")
            services.append({"name": folder_name})
            continue

        try:
            compose_data = yaml.safe_load(io.StringIO(compose_content))
            services_in_compose = compose_data.get("services", {})

            extracted_ports = []
            for service_config in services_in_compose.values():
                ports = service_config.get("ports", [])
                for port_mapping in ports:
                    port_str = str(port_mapping).strip()
                    match = re.match(r"(?:[\d\.]+:)?(\d+):\d+", port_str)
                    if match:
                        extracted_ports.append(int(match.group(1)))

            if extracted_ports:
                for port in extracted_ports:
                    services.append({"name": folder_name, "port": port})
            else:
                services.append({"name": folder_name})

        except Exception as e:
            print(f"⚠️ Failed to parse compose file in {folder_name}: {e}")
            services.append({"name": folder_name})

    return services

def save_services_to_yaml(services, path):
    formatted = []
    for s in services:
        formatted.append({
            "name": s.get("name"),
            "port": s.get("port") if "port" in s else None
        })

    with open(path, "w") as f:
        f.write("# 🔧 Add missing port numbers below before continuing\n")
        yaml.dump({"services": formatted}, f, sort_keys=False)
