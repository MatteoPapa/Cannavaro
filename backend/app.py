import yaml, os
from utils.ssh_utils import ssh_connect, ensure_remote_dependencies, setup_ssh_authorized_key
from utils.git_utils import setup_ssh_key, initialize_all_repos
from utils.services_utils import initialize_services
from server import set_dependencies, run_server
import atexit

BASE_DIR = os.path.dirname(__file__)
SERVICES_YAML_PATH = os.path.join(BASE_DIR, 'services.yaml')
CONFIG_YAML_PATH = os.path.join(BASE_DIR, 'config.yaml')

def load_config():
    with open(CONFIG_YAML_PATH, "r") as f:
        return yaml.safe_load(f)
    
def save_config(config):
    with open(SERVICES_YAML_PATH, "w") as f:
        yaml.safe_dump(config['services'], f)

def main():
    config = load_config()

    # --- SSH Setup ---------------
    ssh = ssh_connect(config)
    if not ssh:
        exit(1)
    
    ensure_remote_dependencies(ssh)
    setup_ssh_authorized_key(ssh, config)
    # -----------------------------

    # --- Parse services ----------
    initialize_services(ssh, config, SERVICES_YAML_PATH)
    
    # --- Git Setup ---------------
    setup_ssh_key(ssh, config)
    initialize_all_repos(ssh, config)
    # -----------------------------

    # ---- Run Web Server -----------
    set_dependencies(config, ssh)
    run_server()
    
    save_config(config)
    ssh.close()

if __name__ == "__main__":
    main()