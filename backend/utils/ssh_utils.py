import os
import paramiko
from utils.logging_utils import log

def ssh_connect(config):
    """
    Establishes an SSH connection to the remote VM using password authentication.
    Handles and logs connection issues gracefully.
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        log.info("Connecting using password...")
        ssh.connect(
            config["remote_host"],
            port=config["remote_port"],
            username=config["root_user"],
            password=config["vm_password"]
        )
        return ssh
    except Exception as e:
        log.error(f"SSH connection failed: {type(e).__name__}: {e}")
        return None

def ensure_remote_dependencies(ssh):
    """
    Installs required packages on the remote VM using apt.
    """
    try:
        log.info("📦 Ensuring dependencies are installed on remote VM...")

        commands = [
            "apt-get update -y",
            "apt-get install -y zip rsync git"
        ]

        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                err = stderr.read().decode()
                raise Exception(f"Failed to run '{cmd}': {err}")

        log.info("✅ Remote dependencies installed.")
    except Exception as e:
        log.error(f"❌ Failed to install dependencies: {e}")

def setup_ssh_authorized_key(config):
    vm_ip = config.get("remote_host")
    ssh_port = config.get("remote_port", 22)
    password = config.get("vm_password")

    pub_key_path = config.get("pub_key_path", "/root/.ssh/id_rsa.pub")
    if not os.path.exists(pub_key_path):
        log.error("⚠️ SSH public key not found inside container:", pub_key_path)
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
            log.info("STDOUT:", out)
        if err:
            log.warning("STDERR:", err)

        log.info("✅ Public key successfully ensured on VM.")
        return ssh 

    except Exception as e:
        log.error(f"❌ Failed to add public key to VM: {e}")
        return None

def run_remote_command(ssh, command, raise_on_error=False):
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()

    if err.strip():
        log.warning(f"⚠️ {err.strip()}")
        if raise_on_error:
            raise Exception(f"Command failed: {err.strip()}")

    return out