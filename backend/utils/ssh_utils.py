import paramiko
import os

def ensure_remote_dependencies(ssh):
    """
    Installs required packages on the remote VM using apt.
    Currently installs: zip, rsync
    """
    try:
        print("📦 Ensuring dependencies (zip, rsync) are installed on remote VM...")

        commands = [
            "apt-get update -y",
            "apt-get install -y zip rsync"
        ]

        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                err = stderr.read().decode()
                raise Exception(f"Failed to run '{cmd}': {err}")

        print("✅ Remote dependencies installed.")
    except Exception as e:
        print("❌ Failed to install dependencies:", e)
        
def setup_ssh_authorized_key(config):
    vm_ip = config.get("vm_ip")
    ssh_port = config.get("ssh_port", 22)
    password = config.get("vm_password")

    pub_key_path = "/root/.ssh/id_rsa.pub"
    if not os.path.exists(pub_key_path):
        print("⚠️ SSH public key not found inside container:", pub_key_path)
        return None

    with open(pub_key_path, 'r') as key_file:
        pub_key = key_file.read().strip()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vm_ip, port=ssh_port, username='root', password=password)

        # Setup ~/.ssh and authorized_keys
        ssh.exec_command('mkdir -p ~/.ssh && chmod 700 ~/.ssh')
        ssh.exec_command('touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys')

        # Avoid duplicates
        check_and_add_cmd = f'grep -qxF "{pub_key}" ~/.ssh/authorized_keys || echo "{pub_key}" >> ~/.ssh/authorized_keys'
        _, stdout, stderr = ssh.exec_command(check_and_add_cmd)

        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print("STDOUT:", out)
        if err:
            print("STDERR:", err)

        print("✅ Public key successfully ensured on VM.")
        return ssh  # 👈 return the active session

    except Exception as e:
        print("❌ Failed to add public key to VM:", e)
        return None

import yaml
import io
import re

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
                    services.append({
                        "name": folder_name,
                        "port": port
                    })
            else:
                services.append({"name": folder_name})  # No ports found, just name

        except Exception as e:
            print(f"⚠️ Failed to parse compose file in {folder_name}: {e}")
            services.append({"name": folder_name})
            continue

    return services

def save_services_to_yaml(services, path):
    # Ensure each service has both keys, even if port is None
    formatted_services = []
    for svc in services:
        formatted_services.append({
            "name": svc.get("name"),
            "port": svc.get("port") if "port" in svc else None
        })

    with open(path, 'w') as file:
        yaml.dump({"services": formatted_services}, file, sort_keys=False)
