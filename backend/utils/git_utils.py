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
        run_remote_command(ssh, "git config --global user.email \"skibidi@palleselvaggie.com\"")
        run_remote_command(ssh, f"git config --global init.defaultBranch \"{DEFAULT_BRANCH}\"")
    except Exception as e:
        log.error(f"❌ Failed to set Git identity: {e}")
        return

    log.info("✅ Git setup complete.")

def initialize_service_repo(ssh, config, path):
    """
    Initializes a Git repository in the specified path if one doesn't exist.
    Sets shared group access, permissions, and makes an initial commit if needed.
    """
    user = config["gituser_name"]

    try:
        log.info(f"📁 Checking if {path} is already a Git repository...")
        is_git_repo = run_remote_command(ssh, f"test -d {path}/.git && echo exists || echo missing").strip()

        if is_git_repo == "missing":
            log.info(f"🧱 Initializing Git repository at {path}...")
            run_remote_command(ssh, f"git init {path}")

        # Configure shared repo access
        log.info("🔧 Configuring Git shared group access...")
        run_remote_command(ssh, f"cd {path} && git config core.sharedRepository group")

        # Ensure Git can update when pushed to
        run_remote_command(ssh, f"cd {path} && git config receive.denyCurrentBranch updateInstead")

        # Check if repo has any commits
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

    services = config.get("services")

    for svc in services:
        path = "/root/" + svc["name"]
        initialize_service_repo(ssh, config, path)