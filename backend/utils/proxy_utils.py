import yaml
import os
import posixpath
import ast
import re
import tempfile
import os
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
    remote_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy.py"
    stdin, stdout, stderr = ssh.exec_command(f"test -f {remote_path} && echo exists || echo missing")
    output = stdout.read().decode().strip()
    return output == "exists"

# ----- MAIN FUNCTIONS -----
def install_proxy_for_service(ssh, config, parent, subservice, service):
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
            if isinstance(port, int):
                # Treat raw port as host and container (common for symmetric ports)
                host_port = container_port = port
            else:
                parts = port.split(":")
                if len(parts) == 2:
                    # "host:container"
                    host_port, container_port = parts
                elif len(parts) == 3:
                    # "ip:host:container"
                    _, host_port, container_port = parts
                else:
                    return {"success": False, "error": f"Unrecognized port format: '{port}'"}

            host_port = int(host_port)
            container_port = int(container_port)
            new_host_port = host_port + 6
            updated_ports.append(f"127.0.0.1:{new_host_port}:{container_port}")


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
        original_port = int(host_port)
        adjusted_port = original_port + 6

        # Determine TARGET_IP from config
        remote_host = config.get("remote_host", "")
        target_ip = remote_host if remote_host == "host.docker.internal" else "127.0.0.1"

        # Render the proxy script
        local_proxy_template = os.path.join(os.path.dirname(__file__), "../assets/demon_hill_template.py")
        if not os.path.exists(local_proxy_template):
            return {"success": False, "error": "Demon Hill proxy template not found."}

        ssl_state = "True" if service.get("tls", False) else "False"
        # ssl_state = "False"

        rendered_script = render_jinja_proxy_script(
            parent,
            original_port,
            adjusted_port,
            target_ip,
            local_proxy_template,
            ssl_state
        )

        if ssl_state == "True":
            return install_docker_proxy_folder(ssh, parent, rendered_script, subservice)


        # Upload the rendered proxy script
        proxy_folder = f"/root/{parent}/proxy_folder_{parent}"
        remote_path = posixpath.join(proxy_folder, "proxy.py")

        try:
            run_remote_command(ssh, f"mkdir -p {proxy_folder}")

            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write(rendered_script)
                tmp_path = tmp.name

            sftp = ssh.open_sftp()
            sftp.put(tmp_path, remote_path)
            sftp.chmod(remote_path, 0o755)
            sftp.close()
            os.remove(tmp_path)

            log.info(f"✅ Rendered Demon Hill proxy uploaded to {remote_path}")
            
            rolling_restart_docker_service(ssh, f"/root/{parent}", [subservice])

            screen_name = f"proxy_{parent}"
            log_file = f"{proxy_folder}/log_{screen_name}.txt"

            start_cmd = (
                f"screen -L -Logfile {log_file} "
                f"-S {screen_name} -dm bash -lic 'python3 {remote_path}'"
            )

            run_remote_command(ssh, start_cmd)

            run_remote_command(ssh, f"""
                cd /root/{parent} && \
                git add {os.path.basename(compose_path)} && \
                git commit -m '{commit_msg} + added proxy script'
            """)

        except Exception as e:
            return {"success": False, "error": f"Script rendered, but upload failed: {e}"}

        return {"success": True, "message": f"Proxy installed for {parent} with subservice {subservice}"}

    except Exception as e:
        # Restore backup if anything goes wrong
        run_remote_command(ssh, f"mv {backup_path} {compose_path}")
        return {"success": False, "error": f"Failed to install proxy: {e}"}

def install_docker_proxy_folder(ssh, service_name, rendered_script, subservice):
    folder = f"/root/{service_name}/proxy_folder_{service_name}"
    dockerfile = f"""
    FROM python:3.10-slim

    WORKDIR /app
    COPY proxy.py .
    COPY certs/server-key.pem certs/server-key.pem
    COPY certs/server-cert.pem certs/server-cert.pem
    COPY certs/ca-cert.pem certs/ca-cert.pem

    RUN pip install --no-cache-dir jinja2 requests certifi scapy

    # Create a folder to store pcaps
    RUN mkdir -p /app/pcaps

    # EXPOSE the FROM_PORT for visibility (optional; doesn't do anything in --network host)
    EXPOSE {rendered_script.split('FROM_PORT = ')[1].split()[0]}

    CMD ["python", "proxy.py"]
    """.strip()



    try:
        # Step 1: Create remote folder
        log.info(f"📁 Creating remote folder: {folder}")
        run_remote_command(ssh, f"mkdir -p {folder}")

        # Step 2: Upload files
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp_py:
            tmp_py.write(rendered_script)
            proxy_path = tmp_py.name

        with tempfile.NamedTemporaryFile("w", delete=False) as tmp_df:
            tmp_df.write(dockerfile)
            dockerfile_path = tmp_df.name

        sftp = ssh.open_sftp()
        sftp.put(proxy_path, f"{folder}/proxy.py")
        sftp.put(dockerfile_path, f"{folder}/Dockerfile")
        sftp.chmod(f"{folder}/proxy.py", 0o755)
        sftp.close()
        os.remove(proxy_path)
        os.remove(dockerfile_path)

        log.info(f"✅ Proxy and Dockerfile uploaded to {folder}")

        # Upload cert files
        run_remote_command(ssh, f"mkdir -p {folder}/certs")
        run_remote_command(ssh, f"cp /root/{service_name}/manager/*.pem {folder}/certs/")

        image_name = f"proxy_{service_name}_image".lower()
        screen_name = f"proxy_{service_name}"
        log_file = f"{folder}/log_{screen_name}.txt"

        # Step 3: Build Docker image
        log.info(f"🐳 Building Docker image '{image_name}'")
        build_output = run_remote_command(ssh, f"cd {folder} && docker build -t {image_name} .")
        log.info(f"🐳 Build output:\n{build_output}")

        # Step 4: Start container in screen
        from_port = rendered_script.split('FROM_PORT = ')[1].split()[0]

        # Do this right after the commit of compose changes
        rolling_restart_docker_service(ssh, f"/root/{service_name}", [subservice])

        start_cmd = (
            f"screen -L -Logfile {log_file} "
            f"-S {screen_name} -dm bash -lic 'cd {folder} && docker run -it --rm -p {from_port}:{from_port} {image_name}'"
        )


        log.info(f"🎬 Starting proxy container in screen: {screen_name}")
        run_remote_command(ssh, start_cmd)

        # Step 5: Verify screen started
        screen_check = run_remote_command(ssh, f"screen -ls | grep {screen_name} || echo NOT_FOUND")
        log.info(f"🔍 Screen status:\n{screen_check.strip()}")

        # Step 6: Show last few lines of screen log
        log_tail = run_remote_command(ssh, f"tail -n 10 {log_file} || echo '(no log file yet)'")
        log.info(f"📝 Screen log (last 10 lines):\n{log_tail.strip()}")

        return {"success": True, "message": f"Proxy Docker container launched for {service_name}"}

    except Exception as e:
        return {"success": False, "error": f"❌ Failed Docker proxy setup: {e}"}

def reload_proxy_screen(ssh, service_name):
    screen_name = f"proxy_{service_name}"
    log.info(f"Sending reload signal to proxy screen: {screen_name}")
    # Check if screen exists
    check_cmd = f"screen -list | grep {screen_name}"

    output = run_remote_command(ssh, check_cmd).strip()
    if screen_name not in output:
        log.error(f"No running screen session found for {screen_name}")
        return {"success": False, "error": f"No running screen session for {screen_name}"}
    
    # Send reload signal
    cmd = f"screen -S {screen_name} -X stuff 'r\\n'"
    run_remote_command(ssh, cmd)

    return {"success": True, "message": f"Reload signal sent to proxy {screen_name}"}

def get_logs(ssh, service_name):
    log_path = f"/root/{service_name}/proxy_folder_{service_name}/log_proxy_{service_name}.txt"

    try:
        stdin, stdout, stderr = ssh.exec_command(f"cat {log_path}")
        logs = stdout.read().decode()
        return {"success": True, "logs": logs}
    except Exception as e:
        return {"success": False, "error": str(e)}

logger_marker = "#PLACEHOLDER_FOR_CANNAVARO_DONT_TOUCH_THIS_LINE"

def get_code(ssh, service_name):
    """
    Extract the editable portions of the proxy code between placeholder markers.
    """
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy.py"

    try:
        stdin, stdout, stderr = ssh.exec_command(f"cat {code_path}")
        full_code = stdout.read().decode()

        # Split by markers
        parts = full_code.split(logger_marker)
        if len(parts) < 4:
            return {"success": False, "error": "Code format error: Not enough marker sections"}

        # Extract modifiable blocks (settings and filters)
        settings_block = parts[1].strip()
        filters_block = parts[3].strip()

        # Combine them for editing
        code = f"{settings_block}\n{logger_marker}\n{filters_block}"

        return {"success": True, "code": code}

    except Exception as e:
        return {"success": False, "error": str(e)}

def save_code(ssh, service_name, new_partial_code):
    """
    Replace the editable portions of the proxy code using new content.
    """
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy.py"


    try:
        # Read full original code
        stdin, stdout, stderr = ssh.exec_command(f"cat {code_path}")
        full_code = stdout.read().decode()

        parts = full_code.split(logger_marker)
        if len(parts) < 4:
            return {"success": False, "error": "Original code is missing expected marker sections"}

        # Parse new editable sections
        new_parts = new_partial_code.split(logger_marker)
        if len(new_parts) < 2:
            return {"success": False, "error": "New code must contain both sections separated by the marker"}

        new_settings = new_parts[0].strip()
        new_filters = new_parts[1].strip()

        # Reconstruct full code
        updated_code = (
            f"{parts[0].rstrip()}\n{logger_marker}\n"
            f"{new_settings}\n{logger_marker}\n"
            f"{parts[2].strip()}\n{logger_marker}\n"
            f"{new_filters}\n{logger_marker}\n"
            f"{parts[4].lstrip()}"
        )

        # Validate code syntax
        try:
            compile(updated_code, "<string>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error in updated code: {e}"}

        # Upload to remote
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(updated_code)
            tmp_path = tmp.name

        sftp = ssh.open_sftp()
        sftp.put(tmp_path, code_path)
        sftp.chmod(code_path, 0o755)
        sftp.close()
        os.remove(tmp_path)

        # Git commit
        commit_msg = "Update proxy code (partial edit)"
        run_remote_command(ssh, f"""
            cd /root/{service_name} && \
            git add proxy_folder_{service_name} && \
            git commit -m '{commit_msg}'
        """)

        return {"success": True, "message": "Partial code saved and committed successfully"}

    except Exception as e:
        return {"success": False, "error": str(e)}

def get_regex(ssh, service_name):
    regex_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy.py"

    try:
        stdin, stdout, stderr = ssh.exec_command(f"cat {regex_path}")
        code = stdout.read().decode()

        # Parse the full file into AST
        tree = ast.parse(code)

        regex_values = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "REGEX_MASKS":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Bytes):
                                    regex_values.append(elt.s.decode("utf-8"))

        return {"success": True, "regex": regex_values}
    except Exception as e:
        return {"success": False, "error": str(e)}
    
def save_regex(ssh, service_name, new_regex_list):
    code_path = f"/root/{service_name}/proxy_folder_{service_name}/proxy.py"


    try:
        # Step 1: Read existing code
        stdin, stdout, stderr = ssh.exec_command(f"cat {code_path}")
        code = stdout.read().decode()

        # Step 2: Build new REGEX_MASKS string
        formatted_items = [f"    {repr(r.encode())}" for r in new_regex_list]
        new_block = "REGEX_MASKS = [\n" + ",\n".join(formatted_items) + "\n]"

        # Step 3: Replace REGEX_MASKS in the code
        regex_pattern = r'(?m)^REGEX_MASKS\s*=\s*\[(?:.*?\n)*?\]'
        new_code, count = re.subn(regex_pattern, new_block, code, flags=re.DOTALL)

        if count == 0:
            return {"success": False, "error": "REGEX_MASKS not found in file"}

        # Step 4: Validate syntax
        try:
            compile(new_code, "<string>", "exec")
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error in code: {e}"
            }
        
        # Step 5: Write to temp file and upload
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(new_code)
            tmp_path = tmp.name

        sftp = ssh.open_sftp()
        sftp.put(tmp_path, code_path)
        sftp.chmod(code_path, 0o755)
        sftp.close()
        os.remove(tmp_path)

        # Step 6: Git commit
        commit_msg = "Update REGEX_MASKS"
        run_remote_command(ssh, f"""
            cd /root/{service_name} && \
            git add proxy_folder_{service_name} && \
            git commit -m '{commit_msg}'
        """)

        return {"success": True, "message": "Regex updated and committed successfully"}

    except Exception as e:
        return {"success": False, "error": str(e)}
