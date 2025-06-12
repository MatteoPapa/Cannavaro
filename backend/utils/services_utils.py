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

def extract_ports(ports):
    extracted = []
    for port_mapping in ports:
        port_str = str(port_mapping).strip()
        match = re.match(r"(?:[\d\.]+:)?(\d+):\d+", port_str)
        if match:
            extracted.append(int(match.group(1)))
        else:
            log.warn(f"Failed to extract port from {port_mapping}")

    return extracted

def list_vm_services_with_ports(ssh, root_dir="/root"):
    stdin, stdout, stderr = ssh.exec_command(
            f"find {root_dir} -maxdepth 2 -type f \\( -name 'docker-compose.yml' -o -name 'compose.yml' \\)")

    compose_paths = stdout.read().decode().splitlines()
    services = []

    for path in compose_paths:
        folder_name = os.path.basename(os.path.dirname(path))
        stdin, stdout, stderr = ssh.exec_command(f"cat {path}")
        compose_content = stdout.read().decode()

        service_obj = {"name": folder_name}

        if not compose_content:
            log.warning(f"⚠️ No compose file found in {folder_name}")
            services.append(service_obj)
            continue

        try:
            compose_data = yaml.safe_load(io.StringIO(compose_content))

            subservices = []
            all_ports = []
            main_service = None

            for name, value in compose_data.get("services", {}).items():
                service = {
                    'name': name,
                    'ports': extract_ports(value.get('ports', [])),
                    'volumes': value.get('volumes', []),
                    'environment': value.get('environment', []),
                }

                if 'image' in value:
                    service['image'] = value['image']

                subservices.append(service)
                all_ports.extend(service['ports'])

                # high chances its the main (?)
                if not main_service:
                    if 'build' in value and value['build'] in ['.', './']:
                        main_service = service

            if main_service and main_service['ports']:
                the_ports = main_service['ports']
            else:
                the_ports = all_ports

            if the_ports:
                service_obj["port"] = the_ports[0]
                if len(the_ports) > 1:
                    log.warn(f"Found more than one port for service {folder_name}!")
            else:
                log.error(f"No ports found for service {folder_name}")

            service_obj["services"] = subservices

        except Exception as e:
            log.error(f"⚠️ Failed to parse compose file in {folder_name}: {e}")

        services.append(service_obj)

    return services

def save_services_to_yaml(services, path):
    formatted = []
    for s in services:
        entry = {
            "name": s.get("name"),
            "port": s.get("port", None)
        }

        if "services" in s:
            entry["services"] = s["services"]
        formatted.append(entry)

    with open(path, "w") as f:
        yaml.dump({"services": formatted}, f, sort_keys=False)

def restart_docker_service(ssh, service_name):
    service_path = f"/root/{service_name}"  # Adjust this path as needed
    commands = [
        f"cd {service_path} && docker compose build",
        f"cd {service_path} && docker compose down && docker compose up -d"
    ]
    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        if stdout.channel.recv_exit_status() != 0:
            error = stderr.read().decode().strip()
            print(f"[ERROR] Failed to run: {cmd}\n{error}")
            return {"success": False, "error": error}
    return {"success": True}
