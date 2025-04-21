# core/initializer.py

import yaml
import os
from utils.ssh_utils import *
from utils.services_utils import *
from utils.zip_utils import *
from utils.db_utils import *
import shutil

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

    # If services.yaml is missing, reset local state
    if not os.path.exists(services_yaml_path):
        print("🧨 services.yaml not found. Triggering local reset...")
        reset_local_state()

    # After potential reset, check if we can skip SSH steps
    if is_fully_initialized(services_yaml_path, startup_zip_path):
        print("✅ Detected prior initialization — skipping initial steps.")
        with open(services_yaml_path, "r") as f:
            config["services"] = yaml.safe_load(f).get("services", [])
        ssh = setup_ssh_authorized_key(config)
        return config, ssh

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

def reset_local_state():
    folders_to_delete = ["backups", "uploaded_patches","zip"]

    print("🧹 Cleaning up local project folders...")

    for folder in folders_to_delete:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"✅ Deleted folder: {folder}")
            except Exception as e:
                print(f"❌ Failed to delete {folder}: {e}")
        else:
            print(f"⚠️ Folder not found (skipped): {folder}")

    print("\n🧼 Resetting MongoDB collections...")

    try:
        client, db = connect_to_mongo()
        if db is not None:
            # Drop specific collections
            for collection_name in db.list_collection_names():
                db.drop_collection(collection_name)
                print(f"🗑️ Dropped collection: {collection_name}")
        else:
            print("❌ Could not connect to MongoDB.")
    except Exception as e:
        print(f"❌ MongoDB reset failed: {e}")

    print("\n✅ Local reset complete.")
