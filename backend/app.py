import yaml, os
from utils.ssh_utils import ssh_connect, ensure_remote_dependencies
from utils.git_utils import setup_git_user, initialize_all_repos
from utils.services_utils import initialize_services
from server import set_dependencies, run_server

BASE_DIR = os.path.dirname(__file__)
SERVICES_YAML_PATH = os.path.join(BASE_DIR, 'services.yaml')

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

    # --- Parse services ----------
    initialize_services(ssh, config, SERVICES_YAML_PATH)

    # --- Git Setup ---------------
    setup_git_user(ssh, config)
    initialize_all_repos(ssh, config)
    # -----------------------------

    # ---- Run Web Server -----------
    set_dependencies(config, ssh)
    run_server()


    ssh.close()

if __name__ == "__main__":
    main()
