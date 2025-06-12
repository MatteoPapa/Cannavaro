import os
import stat
from pathlib import Path
from utils.logging_utils import log
from utils.ssh_utils import run_remote_command

DEFAULT_BRANCH = "master"

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
        log.info("📩 Downloading private key to local machine...")
        sftp = ssh.open_sftp()
        Path(local_key_path).parent.mkdir(parents=True, exist_ok=True)
        sftp.get(remote_key_path, local_key_path)
        os.chmod(local_key_path, stat.S_IRUSR | stat.S_IWUSR)
        sftp.close()
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

    # 6. Set Git user name and email
    try:
        log.info(f"🛠 Setting Git identity for 'root'...")
        run_remote_command(ssh, "git config --global user.name \"Root User\"")
        run_remote_command(ssh, "git config --global user.email \"root@localhost\"")
        run_remote_command(ssh, f"git config --global init.defaultBranch \"{DEFAULT_BRANCH}\"")
    except Exception as e:
        log.error(f"❌ Failed to set Git identity for '{user}': {e}")
        return

    log.info("✅ Git user setup complete.")

def initialize_service_repo(ssh, config, root_dir, svc_name):
    user = config["gituser_name"]
    service_path = f"/root/{svc_name}"
    bare_path = service_path + ".git"

    try:
        log.info(f"📁 Checking if {bare_path} is already a bare Git repository...")
        is_git_repo = run_remote_command(ssh, f"test -d {bare_path} && echo exists || echo missing").strip()

        if is_git_repo == "missing":
            log.info(f"🧱 Initializing Git bare repository in {bare_path}...")
            run_remote_command(ssh, f"git init --bare --shared=group {bare_path}")
            run_remote_command(ssh, f"chown -R root:{user} {bare_path}")
            run_remote_command(ssh, f"chmod -R g+rwX {bare_path}")

        log.info(f"📁 Checking if {service_path} is already a Git repository...")
        is_git_repo = run_remote_command(ssh, f"test -d {service_path}/.git && echo exists || echo missing").strip()

        if is_git_repo == "missing":
            log.info(f"🧱 Initializing Git repository in {service_path}...")
            run_remote_command(ssh, f"git init {service_path}")
            run_remote_command(ssh, f"chown -R root:{user} {service_path}")
            run_remote_command(ssh, f"chown -R {user}:{user} {service_path}/.git")
            run_remote_command(ssh, f"chmod -R g+rwX {service_path}")

        # Fix dubious ownership
        run_remote_command(ssh, f"runuser -u {user} -- git config --global --add safe.directory {bare_path}")
        run_remote_command(ssh, f"git config --global --add safe.directory {bare_path}")
        run_remote_command(ssh, f"runuser -u {user} -- git config --global --add safe.directory {service_path}")
        run_remote_command(ssh, f"git config --global --add safe.directory {service_path}")

        # Set bare repo as remote origin in the working repo
        run_remote_command(ssh, f"cd {service_path} && git remote add origin {bare_path}")
        run_remote_command(ssh, f"cd {service_path} && git config receive.denyCurrentBranch updateInstead")

        # Check if repo has any commits
        has_commits = run_remote_command(ssh, f"cd {service_path} && git rev-parse --verify HEAD >/dev/null 2>&1 && echo yes || echo no").strip()
        if has_commits == "no":
            log.info("📦 Staging and committing existing files...")
            run_remote_command(ssh, f"cd {service_path} && git add .")
            run_remote_command(ssh, f"cd {service_path} && git commit -m 'Import service {svc_name}'")
        else:
            log.info("✅ Initial commit already exists.")

        # Push commits
        run_remote_command(ssh, f"cd {service_path} && git push origin {DEFAULT_BRANCH}")

        # Write the push hook
        hook_path = f"{bare_path}/hooks/post-receive"
        run_remote_command(ssh, f'echo "#!/bin/sh" > {hook_path}')
        run_remote_command(ssh, f'echo \'GIT_WORK_TREE="{service_path}" git checkout -f\' >> {hook_path}')
        run_remote_command(ssh, f"chmod +x {hook_path}")

        log.info("✅ Git repository setup complete and ready for collaboration.")
    except Exception as e:
        log.error(f"❌ Failed during Git repository setup: {e}")

def initialize_all_repos(ssh, config, root_dir="/root"):
    """
    Initializes a Git repository in /root if one doesn't exist.
    Sets shared group access, permissions, and makes an initial commit if needed.
    """

    services = config.get("services")
    for svc in services:
        initialize_service_repo(ssh, config, root_dir, svc['name'])
