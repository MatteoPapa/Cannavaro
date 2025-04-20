# core/initializer.py

import yaml
import os
from utils.ssh_utils import (
    setup_ssh_authorized_key,
    ensure_remote_dependencies
)
from utils.services_utils import (
    list_vm_services_with_ports,
    save_services_to_yaml
)
from utils.zip_utils import create_and_download_zip

def load_config(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

def is_fully_initialized(services_path, startup_zip_path):
    if not os.path.exists(services_path):
        return False

    with open(services_path, 'r') as f:
        try:
            data = yaml.safe_load(f)
            services = data.get("services", [])
            if not services:
                return False

            for svc in services:
                if "name" not in svc or "port" not in svc or svc["port"] is None:
                    return False
        except Exception:
            return False

    return os.path.exists(startup_zip_path)

def initialize_vm_and_services(config_path, services_yaml_path, zip_base_dir):
    config = load_config(config_path)
    startup_zip_path = os.path.join(zip_base_dir, "home_backup_startup.zip")

    # Skip SSH if everything is already done
    if is_fully_initialized(services_yaml_path, startup_zip_path):
        print("✅ Detected prior initialization — skipping SSH and setup.")
        with open(services_yaml_path, "r") as f:
            config["services"] = yaml.safe_load(f).get("services", [])
        return config, None  # Return None for ssh

    # Otherwise, run full flow
    ssh = setup_ssh_authorized_key(config)
    if not ssh:
        print("❌ SSH setup failed.")
        return config, None

    print("✅ SSH connection established.")
    ensure_remote_dependencies(ssh)

    discovered_services = list_vm_services_with_ports(ssh)
    print(f"🔍 Discovered services: {discovered_services}")
    save_services_to_yaml(discovered_services, services_yaml_path)

    missing_ports = [s["name"] for s in discovered_services if "port" not in s]
    if missing_ports:
        print(f"⚠️ Missing service ports for: {missing_ports}")
        print(f"⏸️  Please update {services_yaml_path} manually with missing entries.")
        input("🔁 Press Enter when done to continue...")

        with open(services_yaml_path, "r") as f:
            updated_services = yaml.safe_load(f).get("services", [])
            config["services"] = updated_services
    else:
        config["services"] = discovered_services

    startup_zip = create_and_download_zip(ssh, zip_base_dir, "home_backup_startup.zip")
    if startup_zip:
        print(f"📦 Startup backup saved: {startup_zip}")
    else:
        print("⚠️ Failed to create startup zip.")

    return config, ssh
