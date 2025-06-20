import os
import stat
from pathlib import Path
from utils.logging_utils import log
from utils.ssh_utils import run_remote_command
import subprocess
DEFAULT_BRANCH = "master"

def remote_file_exists(ssh, path):
    """Check if a file exists on the remote system."""
    cmd = f"test -f {path} && echo exists || echo missing"
    result = run_remote_command(ssh, cmd).strip()
    return result == "exists"

def setup_ssh_key(ssh, config):
    local_key_path = config["local_private_key_file"]
    local_public_key = f"{local_key_path}.pub"

    # Generate SSH keypair locally if it doesn't exist
    if not os.path.exists(local_key_path):
        log.info(f"🔐 Creating local SSH keypair at {local_key_path}...")
        subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", local_key_path, "-N", ""], check=True)

    # Read the public key
    with open(local_public_key, "r") as f:
        pub_key = f.read().strip()

    # Copy public key to remote authorized_keys
    run_remote_command(ssh, "mkdir -p /root/.ssh && chmod 700 /root/.ssh")
    
    # Only append the key if it's not already in authorized_keys
    check_cmd = f"grep -qxF '{pub_key}' /root/.ssh/authorized_keys || echo '{pub_key}' >> /root/.ssh/authorized_keys"
    run_remote_command(ssh, check_cmd)

    run_remote_command(ssh, "chmod 600 /root/.ssh/authorized_keys && chown -R root:root /root/.ssh")

    try:
        log.info(f"🛠 Setting Git identity for 'root'...")
        run_remote_command(ssh, "git config --global user.name \"Root User\"")
        run_remote_command(ssh, "git config --global user.email \"skibidi@palleselvagge.com\"")
        run_remote_command(ssh, f"git config --global init.defaultBranch \"{DEFAULT_BRANCH}\"")
        # Add all service folders to Git's safe.directory list
        for svc in config.get("services", []):
            service_path = f"/root/{svc['name']}"
            run_remote_command(ssh, f"git config --global --add safe.directory {service_path}")
    except Exception as e:
        log.error(f"❌ Failed to set Git identity: {e}")
        return

    log.info("✅ Git setup complete.")

import tempfile

def initialize_service_repo(ssh, config, svc):
    """
    Initializes a Git repository in the specified path if one doesn't exist.
    Sets shared group access, permissions, and makes an initial commit if needed.
    """
    path = "/root/" + svc["name"]

    try:
        log.info(f"📁 Checking if {path} is already a Git repository...")
        is_git_repo = run_remote_command(ssh, f"test -d {path}/.git && echo exists || echo missing").strip()

        if is_git_repo == "missing":
            log.info(f"🧱 Initializing Git repository at {path}...")
            run_remote_command(ssh, f"git init {path}")

        # Configure shared repo access
        log.info("🔧 Configuring Git shared group access...")
        run_remote_command(ssh, f"cd {path} && git config core.sharedRepository group")

        # Collect volumes to ignore
        volumes_to_ignore = []
        for subservice in svc.get("services", []):
            for volume in subservice.get("volumes", []):
                if isinstance(volume, str):
                    host_path = volume.split(":")[0].strip()
                    if host_path and not host_path.startswith("/"):
                        clean_path = os.path.normpath(host_path).lstrip("./")
                        log.info(f"📦 Adding volume to ignore list: {clean_path}")
                        volumes_to_ignore.append(clean_path)

        unique_ignores = sorted(set(volumes_to_ignore))
        log.info(f"📦 Ignoring volumes: {', '.join(unique_ignores)}")

        gitignore_path = os.path.join(path, ".gitignore")
        # if not remote_file_exists(ssh, gitignore_path) and unique_ignores:
        if True:
            log.info(f"📄 Creating .gitignore at {gitignore_path}...")

            # Write content to a temporary file locally
            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write("\n".join(unique_ignores) + "\n")
                local_path = tmp.name
                log.info(f"Content written to temporary file: {local_path}")
                log.info(f"Unique ignores: {unique_ignores}")

            # Copy it to the remote using scp
            sftp = ssh.open_sftp()
            sftp.put(local_path, gitignore_path)
            sftp.close()

        # Git receive config
        run_remote_command(ssh, f"cd {path} && git config receive.denyCurrentBranch updateInstead")

        # Git commit if needed
        has_commits = run_remote_command(
            ssh, f"cd {path} && git rev-parse --verify HEAD >/dev/null 2>&1 && echo yes || echo no"
        ).strip()

        if has_commits == "no":
            log.info("📦 Staging and committing existing files...")
            run_remote_command(ssh, f"cd {path} && git add .")
            run_remote_command(ssh, f"cd {path} && git commit -m 'Initial commit: imported services'")
        else:
            log.info("✅ Initial commit already exists.")

        log.info("✅ Git repository setup complete and ready for collaboration.")

    except Exception as e:
        log.error(f"❌ Failed during Git repository setup: {e}")


def initialize_all_repos(ssh, config):
    """
    Initializes a Git repository in /root if one doesn't exist.
    Sets shared group access, permissions, and makes an initial commit if needed.
    """

    for svc in config.get("services", []):
        initialize_service_repo(ssh, config, svc)