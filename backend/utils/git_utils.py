import os
import stat
from pathlib import Path
from utils.logging_utils import log
from utils.ssh_utils import run_remote_command

def remote_file_exists(ssh, path):
    """Check if a file exists on the remote system."""
    cmd = f"test -f {path} && echo exists || echo missing"
    result = run_remote_command(ssh, cmd).strip()
    return result == "exists"

def remote_user_exists(ssh, user):
    """Check if a user exists on the remote system."""
    cmd = f"id -u {user} > /dev/null 2>&1 && echo exists || echo missing"
    result = run_remote_command(ssh, cmd).strip()
    return result == "exists"

def setup_git_user(ssh, config):
    user = config["gituser_name"]
    local_key_path = config["local_private_key_file"]
    remote_key_path = f"/home/{user}/.ssh/id_rsa"

    # 1. Create user if not exists
    try:
        log.info(f"👤 Checking if user '{user}' exists...")
        if not remote_user_exists(ssh, user):
            log.info(f"➕ Creating user '{user}'...")
            run_remote_command(ssh, f"useradd -m -s /bin/bash {user}")
        else:
            log.info(f"✅ User '{user}' already exists.")
    except Exception as e:
        log.error(f"❌ Failed to check/create user '{user}': {e}")
        return

    # 2. Generate SSH keypair if not exists
    try:
        log.info("🔐 Checking if SSH keypair exists...")
        if not remote_file_exists(ssh, remote_key_path):
            log.info("🧾 Generating SSH keypair...")
            run_remote_command(ssh, f"runuser -u {user} -- ssh-keygen -t rsa -b 4096 -N '' -f /home/{user}/.ssh/id_rsa")
        else:
            log.info("✅ SSH keypair already exists.")
    except Exception as e:
        log.error(f"❌ Failed to generate/check SSH keys for '{user}': {e}")
        return

    # 3. Download private key if not already downloaded
    try:
        log.info("📥 Checking if local private key exists...")
        if not Path(local_key_path).exists():
            log.info("📩 Downloading private key to local machine...")
            sftp = ssh.open_sftp()
            Path(local_key_path).parent.mkdir(parents=True, exist_ok=True)
            sftp.get(remote_key_path, local_key_path)
            os.chmod(local_key_path, stat.S_IRUSR | stat.S_IWUSR)
            sftp.close()
        else:
            log.info("✅ Local private key already exists.")
    except Exception as e:
        log.error(f"❌ Failed to fetch private key: {e}")
        return

    # 4. Ensure authorized_keys is set
    try:
        log.info("🔐 Ensuring authorized_keys is in place...")
        run_remote_command(ssh, f"cp /home/{user}/.ssh/id_rsa.pub /home/{user}/.ssh/authorized_keys")
        run_remote_command(ssh, f"chown -R {user}:{user} /home/{user}/.ssh")
    except Exception as e:
        log.error(f"❌ Failed to configure authorized_keys for '{user}': {e}")
        return

    # 5. Ensure /root is accessible by git user
    try:
        log.info("🔧 Ensuring user has access to /root git repo...")
        run_remote_command(ssh, f"chown -R root:{user} /root")
        run_remote_command(ssh, f"chmod -R g+rwX /root")
    except Exception as e:
        log.error(f"❌ Failed to assign permissions to /root: {e}")
        return

    log.info("✅ Git user setup complete.")

def initialize_service_repo(ssh, config, service_path):
    user = config["gituser_name"]

    try:
        log.info(f"📁 Checking if {service_path} is already a Git repository...")
        is_git_repo = run_remote_command(ssh, f"test -d {service_path}/.git && echo exists || echo missing").strip()

        if is_git_repo == "missing":
            log.info(f"🧱 Initializing Git repository in {service_path}...")
            run_remote_command(ssh, f"git init --bare {service_path}")

        # Configure shared repo access
        shared_mode = run_remote_command(ssh, f"git -C {service_path} config --get core.sharedRepository || echo none").strip()
        if shared_mode != "group":
            log.info("🔧 Configuring Git shared group access...")
            run_remote_command(ssh, f"git -C {service_path} config core.sharedRepository group")
        else:
            log.info("✅ Git already configured for shared group access.")

        # Ensure Git can update when pushed to
        run_remote_command(ssh, f"git -C {service_path} config receive.denyCurrentBranch updateInstead")

        # Check if repo has any commits
        has_commits = run_remote_command(ssh, f"git -C {service_path} rev-parse --verify HEAD >/dev/null 2>&1 && echo yes || echo no").strip()

        if has_commits == "no":
            log.info("📦 Staging and committing existing files...")
            run_remote_command(ssh, f"git -C {service_path} config user.name 'Root Automation'")
            run_remote_command(ssh, f"git -C {service_path} config user.email 'root@localhost'")
            run_remote_command(ssh, f"git -C {service_path} add .")
            run_remote_command(ssh, f"git -C {service_path} commit -m 'Import service'")
        else:
            log.info("✅ Initial commit already exists.")

        # Git repo ownership adjustments
        log.info(f"🔐 Ensuring permission for gituser on {service_path} and .git...")
        run_remote_command(ssh, f"chown -R root:{user} {service_path}")
        run_remote_command(ssh, f"chown -R {user}:{user} {service_path}/.git")
        run_remote_command(ssh, f"git -C {service_path} config receive.denyCurrentBranch updateInstead")
        run_remote_command(ssh, f"chmod -R g+rwX {service_path}")
        
        # Mark this repo as safe to suppress Git security warnings
        run_remote_command(ssh, f"git config --global --add safe.directory {service_path}")

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
        service_path = f"/root/{svc['name']}"
        initialize_service_repo(ssh, config, service_path)
