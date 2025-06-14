import yaml
import os
import posixpath
from utils.ssh_utils import run_remote_command
from utils.services_utils import rolling_restart_docker_service
from utils.logging_utils import log

def find_compose_file(ssh, service_path):
    possible_names = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
    for name in possible_names:
        full_path = f"{service_path}/{name}"
        stdin, stdout, stderr = ssh.exec_command(f"test -f {full_path} && echo exists || echo missing")
        if stdout.read().decode().strip() == "exists":
            return full_path
    return None

def install_proxy_for_service(ssh, parent, subservice):
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
            host, container = port.split(":")
            host = str(int(host) - 1)  # Decrease host port by 1
            updated_ports.append(f"{host}:{container}")

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

        # Upload demon hill proxy script
        remote_path = posixpath.join("/root", f"{parent}_proxy.py")
        local_proxy_path = os.path.join(os.path.dirname(__file__), "../assets/demon_hill.py")
        try:
            sftp = ssh.open_sftp()
            sftp.put(local_proxy_path, remote_path)
            sftp.chmod(remote_path, 0o755)
            sftp.close()
            log.info(f"✅ Demon Hill proxy script uploaded to {remote_path}")
        except Exception as e:
            return {"success": False, "error": f"Subservice modified, but demon hill proxy script upload failed: {e}"}

        return rolling_restart_docker_service(ssh, f"/root/{parent}", [subservice])

    except Exception as e:
        # Restore backup if anything goes wrong
        run_remote_command(ssh, f"mv {backup_path} {compose_path}")
        return {"success": False, "error": f"Failed to install proxy: {e}"}

def upload_proxy_script(ssh, local_path, service_name):
    """
    Uploads the proxy file to the remote VM under /root/{service}_proxy
    """
    import posixpath

    remote_path = posixpath.join("/root", f"{service_name}_proxy")
    try:
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.chmod(remote_path, 0o755)
        sftp.close()
        log.info(f"✅ Proxy script uploaded to {remote_path}")
        return {"success": True}
    except Exception as e:
        log.error(f"❌ Failed to upload proxy script: {e}")
        return {"success": False, "error": str(e)}