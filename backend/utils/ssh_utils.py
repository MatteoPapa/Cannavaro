import os
import paramiko
from utils.logging_utils import log

def is_ssh_active(ssh):
    try:
        return ssh is not None and ssh.get_transport() and ssh.get_transport().is_active()
    except Exception:
        return False

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
            "apt-get install -y zip rsync git screen software-properties-common libffi-dev",
            "add-apt-repository ppa:deadsnakes/ppa -y",
            "apt install -y python3.10 python3.10-venv python3.10-dev",
            "python3.10 -m pip install cffi scapy requests",
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

def setup_ssh_authorized_key(ssh, config):
    """
    Ensures the current public key is present in the remote VM's ~/.ssh/authorized_keys.
    Uses the given SSH connection (must be authenticated).
    """
    pub_key_path = "/root/.ssh/id_rsa.pub"
    if not pub_key_path:
        log.info("Skipped adding SSH key to authorized_keys")
        return False

    if not os.path.exists(pub_key_path) or os.path.isdir(pub_key_path):
        log.error(f"⚠️ SSH public key not found at path: {pub_key_path}")
        return False

    with open(pub_key_path, 'r') as key_file:
        pub_key = key_file.read().strip()

    try:
        log.info("🔐 Setting up authorized_keys on remote VM...")

        # Ensure .ssh folder and authorized_keys file
        ssh.exec_command('mkdir -p ~/.ssh && chmod 700 ~/.ssh')
        ssh.exec_command('touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys')

        # Avoid duplicates before appending key
        check_and_add_cmd = f'grep -qxF "{pub_key}" ~/.ssh/authorized_keys || echo "{pub_key}" >> ~/.ssh/authorized_keys'
        stdin, stdout, stderr = ssh.exec_command(check_and_add_cmd)

        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if out:
            log.info(f"STDOUT: {out}")
        if err:
            log.warning(f"STDERR: {err}")

        log.info("✅ Public key ensured on VM.")
        return True

    except Exception as e:
        log.error(f"❌ Failed to setup authorized key: {type(e).__name__}: {e}")
        return False

def run_remote_command(ssh, command, raise_on_error=False):
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()

    if err.strip():
        log.warning(f"⚠️ {err.strip()}")
        if raise_on_error:
            raise Exception(f"Command failed: {err.strip()}")

    return out
