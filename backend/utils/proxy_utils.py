import yaml
import os
import posixpath
import ast
import re
import tempfile
import os
import socket
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

def create_start_script(sftp, script_path, screen_name, log_file, command_body):
    """
    Creates a start_proxy.sh script to launch the proxy inside a screen session.
    """
    script_content = (
        "#!/bin/bash\n\n"
        f"screen -L -Logfile {log_file} "
        f"-S {screen_name} -dm bash -lic '{command_body}'\n"
    )

    with tempfile.NamedTemporaryFile("w", delete=False) as tmp_file:
        tmp_file.write(script_content)
        tmp_local_path = tmp_file.name

    sftp.put(tmp_local_path, script_path)
    sftp.chmod(script_path, 0o755)
    os.remove(tmp_local_path)

# ----- MAIN FUNCTIONS -----
def install_proxy_for_service(ssh, config, parent, subservice, proxy_config):
    try:
        service_path = f"/root/{parent}"
        compose_path = find_compose_file(ssh, service_path)
        if not compose_path:
            return {"success": False, "error": "Compose file not found in service directory."}

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
            original_port = int(proxy_config["port"])
            adjusted_port = original_port
            container_port = int(ports[0].split(":")[-1])
            updated_ports = [f"127.0.0.1:{original_port}:{container_port}"]
        else:
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

        port_check_cmd = f"ss -tuln | grep ':{adjusted_port} ' || true"
        port_check_result = run_remote_command(ssh, port_check_cmd).strip()
        if port_check_result:
            return {"success": False, "error": f"Port {adjusted_port} is already in use on the remote host."}

        new_yaml = yaml.dump(compose_data)
        escaped = new_yaml.replace("'", "'\\''")
        run_remote_command(ssh, f"echo '{escaped}' > {compose_path}")

        commit_msg = f"Install proxy: moved ports for subservice {subservice}"
        run_remote_command(ssh, f"""
            cd {service_path} && \
            git add {os.path.basename(compose_path)} && \
            git commit -m '{commit_msg}'
        """)

        if proxy_config.get("proxy_type") == "AngelPit":
            log.info("Installing AngelPit proxy")
            result = install_angel_pit_proxy(
                ssh, config, proxy_config, service_path,
                parent, subservice, adjusted_port, original_port
            )
            if not result.get("success"):
                return result
        elif proxy_config.get("proxy_type") == "Mini-Proxad":
            log.info("Installing Mini-Proxad proxy")
            result = install_mini_proxad(
                ssh, config, proxy_config, service_path,
                parent, subservice, adjusted_port, original_port
            )
            if not result.get("success"):
                return result

        # Final commit
        run_remote_command(ssh, f"""
            cd {service_path} && \
            git add {os.path.basename(compose_path)} && \
            git commit -m '{commit_msg} + added proxy launcher'
        """, raise_on_error=True)

        return {"success": True, "message": f"Proxy installed for {parent} with subservice {subservice}"}

    except Exception as e:
        run_remote_command(ssh, f"mv {backup_path} {compose_path}")
        return {"success": False, "error": f"Failed to install proxy: {e}"}

# ----- PROXY TYPES -----
def render_template_file(template_path, replacements):
    with open(template_path, "r") as f:
        content = f.read()
    for key, value in replacements.items():
        placeholder = f"{{{{{key}}}}}"
        content = content.replace(placeholder, str(value))
    return content

def install_angel_pit_proxy(ssh, config, proxy_config, service_path, parent, subservice, adjusted_port, original_port):
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

    # 🔐 Handle TLS
    if proxy_config.get("tls_enabled"):
        cert_path = proxy_config.get("server_cert")
        key_path = proxy_config.get("server_key")
        combined_remote_path = posixpath.join(remote_proxy_dir, "combined.pem")
        run_remote_command(ssh, f"cat {cert_path} {key_path} > {combined_remote_path}")

    # 🔄 Proxy Launch Script
    protocol = proxy_config["protocol"]
    if proxy_config.get("tls_enabled"):
        protocol = {"http": "https", "tcp": "tls"}.get(protocol, protocol)

    address = "host.docker.internal" if config["remote_host"] == "host.docker.internal" else "127.0.0.1"

    mitm_command = [
        # "SSLKEYLOGFILE=mitmkeys.log mitmdump",
        f"mitmdump --mode reverse:{protocol}://{address}:{adjusted_port}",
        f"--listen-port {original_port}",
        '--certs "*=combined.pem"' if proxy_config.get("tls_enabled") else "",
        "--quiet",
        "--ssl-insecure",
        "--set block_global=false",
        "-s angel_pit_proxy.py"
    ]

    if proxy_config.get("dump_pcaps"):
        mitm_command.append("-s angel_dumper.py")
        mitm_command.append(f"--set pcap_path={proxy_config.get('pcap_path', 'pcaps')}")
        mitm_command.append(f"--set service_name={parent}")

    launch_remote_path = posixpath.join(remote_proxy_dir, "angelpit_command.sh")
    mitm_cmd_str = " \\\n  ".join(filter(None, mitm_command))
    with tempfile.NamedTemporaryFile("w", delete=False) as mitm_file:
        mitm_file.write("#!/bin/bash\n\n" + mitm_cmd_str + "\n")
        mitm_file_path = mitm_file.name
    sftp.put(mitm_file_path, launch_remote_path)
    sftp.chmod(launch_remote_path, 0o755)
    os.remove(mitm_file_path)

    # Start script generation
    start_script_path = posixpath.join(remote_proxy_dir, "start_proxy.sh")
    screen_name = f"proxy_{parent}"
    log_file = f"{remote_proxy_dir}/log_{screen_name}.txt"
    command_body = f"cd {remote_proxy_dir} && bash {os.path.basename(launch_remote_path)}"
    create_start_script(sftp, start_script_path, screen_name, log_file, command_body)

    # 🔁 Restart docker subservice
    rolling_restart_docker_service(ssh, service_path, [subservice])

    # Launch start_proxy.sh
    run_remote_command(ssh, f"bash {start_script_path}", raise_on_error=True)


    return {"success": True}

def install_mini_proxad(ssh, config, proxy_config, service_path, parent, subservice, adjusted_port, original_port):
    local_proxy_dir = os.path.join(os.path.dirname(__file__), "../assets/Mini-Proxad")
    if not os.path.isdir(local_proxy_dir):
        return {"success": False, "error": "Proxy template folder Mini-Proxad not found."}

    remote_proxy_dir = f"{service_path}/proxy_folder_{parent}"
    run_remote_command(ssh, f"mkdir -p {remote_proxy_dir}")
    sftp = ssh.open_sftp()

    if config["remote_host"] == "host.docker.internal":
        address = socket.gethostbyname("host.docker.internal")
    else:
        address = "127.0.0.1"

    replacements = {
        "SERVICE_NAME": parent,
        "FROM_PORT": original_port,
        "TO_PORT": adjusted_port,
        "TO_IP": address,
        "CERT_PATH": proxy_config.get("server_cert", ""),
        "KEY_PATH": proxy_config.get("server_key", ""),
        "TLS_ENABLED": str(proxy_config.get("tls_enabled", False)).lower(),
        "DUMP_ENABLED": str(proxy_config.get("dump_pcaps", False)).lower(),
        "DUMP_PATH": proxy_config.get("pcap_path", "pcaps"),
    }

    for filename in os.listdir(local_proxy_dir):
        local_path = os.path.join(local_proxy_dir, filename)
        remote_path = posixpath.join(remote_proxy_dir, filename)

        if filename.endswith(".yaml") or filename.endswith(".yml"):
            rendered = render_template_file(local_path, replacements)
            with sftp.open(remote_path, 'w') as f:
                f.write(rendered)
        else:
            sftp.put(local_path, remote_path)

    # 🔐 TLS: concatenate cert + key if enabled
    if proxy_config.get("tls_enabled"):
        cert_path = proxy_config.get("server_cert")
        key_path = proxy_config.get("server_key")
        combined_remote_path = posixpath.join(remote_proxy_dir, "combined.pem")
        run_remote_command(ssh, f"cat {cert_path} {key_path} > {combined_remote_path}")

    # 🔁 Restart subservice container to ensure the proxy can bind to the target port
    rolling_restart_docker_service(ssh, service_path, [subservice])

    # ⏯️ Launch Mini-Proxad via screen
    screen_name = f"proxy_{parent}"
    log_file = f"{remote_proxy_dir}/log_{screen_name}.txt"
    start_script_path = posixpath.join(remote_proxy_dir, "start_proxy.sh")
    command_body = (
        f"chmod +x {remote_proxy_dir}/mini-proxad.bin && "
        f"{remote_proxy_dir}/mini-proxad.bin --config {remote_proxy_dir}/config.yaml"
    )
    create_start_script(sftp, start_script_path, screen_name, log_file, command_body)

    # Launch the start script
    run_remote_command(ssh, f"bash {start_script_path}", raise_on_error=True)


    sftp.close()
    return {"success": True}

# ----- COMMON FUNCTIONS -----

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

def get_code(ssh, service_name):
    """
    Retrieve the full contents of the proxy_filters.py file for editing.
    """
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy_filters.py"

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
    Overwrite the proxy_filters.py file with new content.
    """
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy_filters.py"

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
        commit_msg = "Update proxy_filters.py"
        run_remote_command(ssh, f"""
            cd /root/{service_name} && \
            git add proxy_folder_{service_name}/proxy_filters.py && \
            git commit -m '{commit_msg}'
        """)

        return {"success": True, "message": "Code saved successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_regex(ssh, service_name):
    regex_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy_filters.py"

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
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy_filters.py"

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
            git add proxy_folder_{service_name}/proxy_filters.py && \
            git commit -m '{commit_msg}'
        """)

        return {"success": True, "message": "Regex updated and committed successfully"}

    except Exception as e:
        return {"success": False, "error": str(e)}
