import yaml
import os
import posixpath
import ast
import re
import tempfile
import os
import shlex
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

def render_jinja_proxy_script(service_name, from_port, to_port, target_ip, template_path, ssl_state):
    with open(template_path, "r") as f:
        template = Template(f.read())

    return template.render(
        FROM_PORT=from_port,
        TO_PORT=to_port,
        TARGET_IP=target_ip,
        SERVICE_PATH = "/root/" + service_name,
        SSL_ENABLED= ssl_state
    )

def is_proxy_installed(ssh, service_name):
    """
    Checks if the proxy file for the given service already exists on the VM.
    """
    remote_path = f"/root/{service_name}/proxy_folder_{service_name}"
    stdin, stdout, stderr = ssh.exec_command(f"test -d {remote_path} && echo exists || echo missing")
    output = stdout.read().decode().strip()
    log.info(f"Proxy check for {service_name}: {output}")
    return output == "exists"

# ----- MAIN FUNCTIONS -----
def install_proxy_for_service(ssh, config, parent, subservice, proxy_config):
    try:
        service_path = f"/root/{parent}"
        compose_path = find_compose_file(ssh, service_path)
        if not compose_path:
            return {"success": False, "error": "Compose file not found in service directory."}

        # Backup compose
        backup_path = f"{compose_path}.bak"
        run_remote_command(ssh, f"cp {compose_path} {backup_path}")
        raw_yaml = run_remote_command(ssh, f"cat {compose_path}")
        compose_data = yaml.safe_load(raw_yaml)

        service_def = compose_data['services'][subservice]
        ports = service_def.get("ports", [])
        if not ports:
            return {"success": False, "error": f"No ports defined for subservice '{subservice}'"}

        updated_ports = []
        original_port = None
        adjusted_port = None

        if proxy_config.get("port"):
            # Use custom port mapping
            original_port = int(proxy_config["port"])
            adjusted_port = original_port
            container_port = int(ports[0].split(":")[-1])
            updated_ports = [f"127.0.0.1:{original_port}:{container_port}"]
        else:
            # Shift all exposed ports +6
            for port in ports:
                parts = str(port).split(":")
                if len(parts) == 2:
                    host_port, container_port = map(int, parts)
                elif len(parts) == 3:
                    host_port = int(parts[1])
                    container_port = int(parts[2])
                else:
                    return {"success": False, "error": f"Unrecognized port format: '{port}'"}
                original_port = host_port
                adjusted_port = host_port + 6
                updated_ports.append(f"127.0.0.1:{adjusted_port}:{container_port}")

        service_def["ports"] = updated_ports

        # 🔐 Port usage check for adjusted_port (proxy listen port)
        port_check_cmd = f"ss -tuln | grep ':{adjusted_port} ' || true"
        port_check_result = run_remote_command(ssh, port_check_cmd).strip()

        if port_check_result:
            return {"success": False, "error": f"Port {adjusted_port} is already in use on the remote host."}

        # Update compose file
        new_yaml = yaml.dump(compose_data)
        escaped = new_yaml.replace("'", "'\\''")
        run_remote_command(ssh, f"echo '{escaped}' > {compose_path}")

        # Commit the change
        commit_msg = f"Install proxy: moved ports for subservice {subservice}"
        run_remote_command(ssh, f"""
            cd {service_path} && \
            git add {os.path.basename(compose_path)} && \
            git commit -m '{commit_msg}'
        """)

        # Copy proxy template folder (AngelPit)
        local_proxy_dir = os.path.join(os.path.dirname(__file__), "../assets/AngelPit")
        if not os.path.isdir(local_proxy_dir):
            return {"success": False, "error": "Proxy template folder AngelPit not found."}

        remote_proxy_dir = f"{service_path}/proxy_folder_{parent}"
        run_remote_command(ssh, f"mkdir -p {remote_proxy_dir}")
        sftp = ssh.open_sftp()

        for filename in os.listdir(local_proxy_dir):
            local_path = os.path.join(local_proxy_dir, filename)
            remote_path = posixpath.join(remote_proxy_dir, filename)
            sftp.put(local_path, remote_path)

        # Combine cert and key into combined.pem
               # Combine cert and key into combined.pem
        log.info(f"Proxy configuration: {proxy_config}")

        if proxy_config.get("tls_enabled"):
            cert_path = proxy_config.get("server_cert")
            key_path = proxy_config.get("server_key")
            log.info(f"Using cert: {cert_path}, key: {key_path}")

            cert_path = proxy_config.get("server_cert")
            key_path = proxy_config.get("server_key")
            combined_remote_path = posixpath.join(remote_proxy_dir, "combined.pem")

            log.info(f"Combining cert and key on remote: {cert_path}, {key_path} -> {combined_remote_path}")

            run_remote_command(ssh, f"cat {cert_path} {key_path} > {combined_remote_path}")


        # Create launch script
        protocol = proxy_config["protocol"]
        if proxy_config.get("tls_enabled"):
            protocol = {"http": "https", "tcp": "tls"}.get(protocol, protocol)

        if config["remote_host"] == "host.docker.internal":
            address = "host.docker.internal"
        else:
            address = "127.0.0.1"

        mitm_command = [
            "mitmdump",
            f"--mode reverse:{protocol}://{address}:{adjusted_port}",
            f"--listen-port {original_port}",
            '--certs "*=combined.pem"',
            "--quiet",
            "--ssl-insecure",
            "-s angel_pit_proxy.py"
        ]

        if proxy_config.get("dump_pcaps"):
            pcap_path = proxy_config.get("pcap_path") or "pcaps"
            mitm_command.extend([
                "-s angel_dumper.py",
                f"--set pcap_output={shlex.quote(pcap_path)}"
        ])

        launch_script = "#!/bin/bash\n\n" + " \\\n  ".join(mitm_command) + "\n"
        script_local_path = tempfile.NamedTemporaryFile("w", delete=False)
        script_local_path.write(launch_script)
        script_local_path.close()

        launch_remote_path = posixpath.join(remote_proxy_dir, "launch_proxy.sh")
        sftp.put(script_local_path.name, launch_remote_path)
        sftp.chmod(launch_remote_path, 0o755)
        os.remove(script_local_path.name)
        sftp.close()

        # Restart container
        rolling_restart_docker_service(ssh, service_path, [subservice])

        # Launch proxy via screen
        screen_name = f"proxy_{parent}"
        log_file = f"{remote_proxy_dir}/log_{screen_name}.txt"
        start_cmd = (
            f"screen -L -Logfile {log_file} "
            f"-S {screen_name} -dm bash -lic 'cd {remote_proxy_dir} && bash {os.path.basename(launch_remote_path)}'"
        )

        log.error(run_remote_command(ssh, start_cmd, raise_on_error=True))

        # Final git commit for proxy script
        run_remote_command(ssh, f"""
            cd {service_path} && \
            git add {os.path.basename(compose_path)} && \
            git commit -m '{commit_msg} + added proxy launcher'
        """, raise_on_error=True)

        return {"success": True, "message": f"Proxy installed for {parent} with subservice {subservice}"}

    except Exception as e:
        run_remote_command(ssh, f"mv {backup_path} {compose_path}")
        return {"success": False, "error": f"Failed to install proxy: {e}"}

def get_logs(ssh, service_name):
    log_path = f"/root/{service_name}/proxy_folder_{service_name}/log_proxy_{service_name}.txt"
    tmp_path = f"/root/{service_name}/proxy_folder_{service_name}/log_tmp.txt"

    try:
        cmd = f"""
        line_count=$(wc -l < "{log_path}")
        if [ "$line_count" -gt 10000 ]; then
            tail -n 10000 "{log_path}" > "{tmp_path}" && mv "{tmp_path}" "{log_path}" && \
            cd /root/{service_name} && \
            git add proxy_folder_{service_name}/log_proxy_{service_name}.txt && \
            git commit -m 'Trimmed log file to last 10000 lines for proxy {service_name}'
        fi
        tail -n 2000 "{log_path}"
        """
        stdin, stdout, stderr = ssh.exec_command(cmd)
        logs = stdout.read().decode()

        return {"success": True, "logs": logs}
    except Exception as e:
        return {"success": False, "error": str(e)}

logger_marker = "#PLACEHOLDER_FOR_CANNAVARO_DONT_TOUCH_THIS_LINE"

def get_code(ssh, service_name):
    """
    Retrieve the full contents of the angel_filters.py file for editing.
    """
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/angel_filters.py"

    try:
        stdin, stdout, stderr = ssh.exec_command(f"cat {code_path}")
        code = stdout.read().decode()
        err = stderr.read().decode()

        if err.strip():
            return {"success": False, "error": err.strip()}

        return {"success": True, "code": code}
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_code(ssh, service_name, new_code):
    """
    Overwrite the angel_filters.py file with new content.
    """
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/angel_filters.py"

    try:
        # Validate syntax before saving
        try:
            compile(new_code, "<string>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error in updated code: {e}"}

        # Write to temp file
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(new_code)
            tmp_path = tmp.name

        # Upload to remote
        sftp = ssh.open_sftp()
        sftp.put(tmp_path, code_path)
        sftp.chmod(code_path, 0o755)
        sftp.close()
        os.remove(tmp_path)

        # Git commit
        commit_msg = "Update angel_filters.py"
        run_remote_command(ssh, f"""
            cd /root/{service_name} && \
            git add proxy_folder_{service_name}/angel_filters.py && \
            git commit -m '{commit_msg}'
        """)

        return {"success": True, "message": "Code saved successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_regex(ssh, service_name):
    regex_path = f"/root/{service_name}/proxy_folder_{service_name}/angel_filters.py"

    try:
        stdin, stdout, stderr = ssh.exec_command(f"cat {regex_path}")
        code = stdout.read().decode()

        # Parse the full file into AST
        tree = ast.parse(code)

        regex_values = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "ALL_REGEXES":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Bytes):
                                    regex_values.append(elt.s.decode("utf-8"))

        return {"success": True, "regex": regex_values}
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_regex(ssh, service_name, new_regex_list):
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/angel_filters.py"

    try:
        # Read existing code
        stdin, stdout, stderr = ssh.exec_command(f"cat {code_path}")
        code = stdout.read().decode()

        # Build new ALL_REGEXES string
        formatted_items = [f"    {repr(r.encode())}" for r in new_regex_list]
        new_block = "ALL_REGEXES = [\n" + ",\n".join(formatted_items) + "\n]"

        # Replace ALL_REGEXES in the code
        regex_pattern = r'ALL_REGEXES\s*=\s*\[(?:[^\]]*?)\]'
        new_code, count = re.subn(regex_pattern, new_block, code, flags=re.DOTALL)

        if count == 0:
            return {"success": False, "error": "ALL_REGEXES not found in file"}

        # Validate syntax
        try:
            compile(new_code, "<string>", "exec")
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error in code: {e}"
            }

        # Write to temp file and upload
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(new_code)
            tmp_path = tmp.name

        sftp = ssh.open_sftp()
        sftp.put(tmp_path, code_path)
        sftp.chmod(code_path, 0o755)
        sftp.close()
        os.remove(tmp_path)

        # Git commit
        commit_msg = "Update ALL_REGEXES"
        run_remote_command(ssh, f"""
            cd /root/{service_name} && \
            git add proxy_folder_{service_name}/angel_filters.py && \
            git commit -m '{commit_msg}'
        """)

        return {"success": True, "message": "Regex updated and committed successfully"}

    except Exception as e:
        return {"success": False, "error": str(e)}
