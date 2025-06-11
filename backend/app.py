import yaml
from utils.ssh_utils import ssh_connect, ensure_remote_dependencies 
from utils.git_utils import setup_git_user, initialize_git_repo

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    
    # --- SSH Setup ---------------
    ssh = ssh_connect(config)
    if not ssh:
        exit(1)
    ensure_remote_dependencies(ssh)
    # -----------------------------

    # --- Git Setup ---------------
    setup_git_user(ssh, config)
    initialize_git_repo(ssh, config)
    # -----------------------------

    ssh.close()

if __name__ == "__main__":
    main()
