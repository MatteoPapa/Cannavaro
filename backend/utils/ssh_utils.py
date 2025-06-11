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

def run_remote_command(ssh, command, raise_on_error=False):
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()

    if err.strip():
        log.warning(f"⚠️ {err.strip()}")
        if raise_on_error:
            raise Exception(f"Command failed: {err.strip()}")

    return out