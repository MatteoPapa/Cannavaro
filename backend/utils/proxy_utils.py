import yaml
import os
import posixpath
from utils.ssh_utils import run_remote_command
from utils.services_utils import rolling_restart_docker_service
from utils.logging_utils import log
from jinja2 import Template

# ----- HELPER FUNCTIONS -----
def find_compose_file(ssh, service_path):
    possible_names = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
    for name in possible_names:
        full_path = f"{service_path}/{name}"
        stdin, stdout, stderr = ssh.exec_command(f"test -f {full_path} && echo exists || echo missing")
        if stdout.read().decode().strip() == "exists":
            return full_path
    return None

def render_jinja_proxy_script(service_name, from_port, to_port, target_ip, template_path):
    with open(template_path, "r") as f:
        template = Template(f.read())

    return template.render(
        FROM_PORT=from_port,
        TO_PORT=to_port,
        TARGET_IP=target_ip
    )
# ------------------------

# ----- MAIN FUNCTIONS -----
def install_proxy_for_service(ssh, config, parent, subservice):
    service_path = f"/root/{parent}"
    compose_path = find_compose_file(ssh, service_path)

    if not compose_path:
        return {"success": False, "error": "Compose file not found in service directory."}

    backup_path = f"{compose_path}.bak"

    # Backup original
    run_remote_command(ssh, f"cp {compose_path} {backup_path}")

    # Read and parse YAML
    raw_yaml = run_remote_command(ssh, f"cat {compose_path}")
    compose_data = yaml.safe_load(raw_yaml)

    try:
        service_def = compose_data['services'][subservice]
        ports = service_def.get("ports", [])

        if not ports:
            return {"success": False, "error": f"No ports defined for subservice '{subservice}'"}
        
        updated_ports = []

        for port in ports:
            if isinstance(port, int):  # Rare case: raw number
                from_port = port - 1
                updated_ports.append(f"{from_port}:{port}")
                continue

            parts = port.split(":")

            if len(parts) == 2:
                # "3000:3000" → host:container
                host, container = parts
                from_port = str(int(host) - 1)
                updated_ports.append(f"{from_port}:{container}")

            elif len(parts) == 3:
                # "0.0.0.0:3000:3000" → ip:host:container
                ip, host, container = parts
                from_port = str(int(host) - 1)
                updated_ports.append(f"{ip}:{from_port}:{container}")

            else:
                return {"success": False, "error": f"Unrecognized port format: '{port}'"}


        service_def["ports"] = updated_ports

        # Write back to remote file
        new_yaml = yaml.dump(compose_data)
        escaped = new_yaml.replace("'", "'\\''")
        run_remote_command(ssh, f"echo '{escaped}' > {compose_path}")

        # Git commit
        commit_msg = f"Install proxy: moved ports for subservice {subservice}"
        run_remote_command(ssh, f"""
            cd /root/{parent} && \
            git add {os.path.basename(compose_path)} && \
            git commit -m '{commit_msg}'
        """)
        
         # Determine FROM and TO port
        original_port = int(host)
        adjusted_port = original_port - 1

        # Determine TARGET_IP from config
        remote_host = config.get("remote_host", "")
        target_ip = remote_host if remote_host == "host.docker.internal" else "127.0.0.1"

        # Render the proxy script
        local_proxy_template = os.path.join(os.path.dirname(__file__), "../assets/demon_hill_template.py")
        if not os.path.exists(local_proxy_template):
            return {"success": False, "error": "Demon Hill proxy template not found."}

        rendered_script = render_jinja_proxy_script(
            parent,
            original_port,
            adjusted_port,
            target_ip,
            local_proxy_template
        )

        # Upload the rendered proxy script
        remote_path = posixpath.join("/root", f"proxy_{parent}.py")
        try:
            import tempfile
            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write(rendered_script)
                tmp_path = tmp.name

            sftp = ssh.open_sftp()
            sftp.put(tmp_path, remote_path)
            sftp.chmod(remote_path, 0o755)
            sftp.close()
            os.remove(tmp_path)

            log.info(f"✅ Rendered Demon Hill proxy uploaded to {remote_path}")
            screen_name = (f"proxy_{parent}")
            start_cmd = f"screen -S {screen_name} -dm bash -c 'python3 {remote_path}'"
            run_remote_command(ssh, start_cmd)
        except Exception as e:
            return {"success": False, "error": f"Script rendered, but upload failed: {e}"}

        return rolling_restart_docker_service(ssh, f"/root/{parent}", [subservice])

    except Exception as e:
        # Restore backup if anything goes wrong
        run_remote_command(ssh, f"mv {backup_path} {compose_path}")
        return {"success": False, "error": f"Failed to install proxy: {e}"}
    
def is_proxy_installed(ssh, service_name):
    """
    Checks if the proxy file for the given service already exists on the VM.
    """
    remote_path = f"/root/proxy_{service_name}.py"
    stdin, stdout, stderr = ssh.exec_command(f"test -f {remote_path} && echo exists || echo missing")
    output = stdout.read().decode().strip()
    return output == "exists"
