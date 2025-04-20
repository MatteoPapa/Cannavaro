from flask import Flask, jsonify, send_file
from flask_cors import CORS
import yaml
import os

from utils.ssh_utils import *
from utils.zip_utils import setup_zip_dirs, create_and_download_zip, create_timestamped_filename

app = Flask(__name__)
CORS(app)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
ssh = setup_ssh_authorized_key(config)

ZIP_BASE_DIR = os.path.join(os.path.dirname(__file__), 'zip')
STARTUP_ZIP_PATH, CURRENT_ZIP_DIR = setup_zip_dirs(ZIP_BASE_DIR)

SERVICES_YAML_PATH = os.path.join(os.path.dirname(__file__), 'services.yaml')

if ssh:
    print("✅ SSH connection established.")
    ensure_remote_dependencies(ssh)

    # Discover & persist services
    discovered_services = list_vm_services_with_ports(ssh)
    print(f"🔍 Discovered services: {discovered_services}")
    save_services_to_yaml(discovered_services, SERVICES_YAML_PATH)

    # Get folder names from /root to validate coverage
    stdin, stdout, stderr = ssh.exec_command("ls -d /root/*/")
    all_folders = [os.path.basename(path.strip("/")) for path in stdout.read().decode().splitlines()]

    missing_services = [s["name"] for s in discovered_services if "port" not in s]


    if missing_services:
        print(f"⚠️ Missing service ports for: {missing_services}")
        print(f"⏸️  Please update {SERVICES_YAML_PATH} manually with missing entries.")
        input("🔁 Press Enter when done to continue...")

        # Reload manually updated services.yaml
        with open(SERVICES_YAML_PATH, "r") as f:
            updated_services = yaml.safe_load(f).get("services", [])
            config["services"] = updated_services
    else:
        config["services"] = discovered_services


    # Create startup zip
    startup_zip = create_and_download_zip(ssh, ZIP_BASE_DIR, "home_backup_startup.zip")
    if startup_zip:
        print(f"📦 Startup backup saved: {startup_zip}")
    else:
        print("⚠️ Failed to create startup zip.")

@app.route("/api/vm_ip")
def get_vm_ip():
    return jsonify(config.get("vm_ip", "No VM IP configured"))

@app.route("/api/services")
def get_services():
    return jsonify(config.get("services", "No services configured"))

@app.route("/api/get_startup_zip")
def get_startup_zip():
    if not os.path.exists(STARTUP_ZIP_PATH):
        return jsonify({"error": "Startup ZIP not found"}), 404
    return send_file(STARTUP_ZIP_PATH, as_attachment=True)

@app.route("/api/get_current_zip")
def get_current_zip():
    if not ssh:
        return jsonify({"error": "SSH not connected"}), 500

    try:
        filename = create_timestamped_filename()
        temp_zip_path = create_and_download_zip(ssh, ZIP_BASE_DIR, filename)

        if not temp_zip_path:
            return jsonify({"error": "Failed to create ZIP"}), 500

        stored_path = os.path.join(CURRENT_ZIP_DIR, filename)
        os.rename(temp_zip_path, stored_path)

        return send_file(stored_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7001, debug=False)
