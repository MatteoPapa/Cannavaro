from flask import Flask, jsonify, send_file
from flask_cors import CORS
import yaml
import os
import datetime

from utils import *

app = Flask(__name__)
CORS(app)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
ssh = setup_ssh_authorized_key(config)

ZIP_BASE_DIR = os.path.join(os.path.dirname(__file__), 'zip')
STARTUP_ZIP_PATH = os.path.join(ZIP_BASE_DIR, 'home_backup_startup.zip')
CURRENT_ZIP_DIR = os.path.join(ZIP_BASE_DIR, 'current_zips')

os.makedirs(ZIP_BASE_DIR, exist_ok=True)
os.makedirs(CURRENT_ZIP_DIR, exist_ok=True)

def create_and_download_zip(filename="home_backup.zip"):
    remote_dir_to_zip = "/root"
    remote_zip_path = f"/root/{filename}"
    
    # Avoid recursive inclusion
    ssh.exec_command(f'rm -f {remote_zip_path}')
    zip_cmd = f'cd {remote_dir_to_zip} && zip -r {filename} *'
    stdin, stdout, stderr = ssh.exec_command(zip_cmd)
    stdout.channel.recv_exit_status()

    sftp = ssh.open_sftp()
    try:
        sftp.stat(remote_zip_path)
    except FileNotFoundError:
        sftp.close()
        return None

    local_zip_path = os.path.join(ZIP_BASE_DIR, filename)
    sftp.get(remote_zip_path, local_zip_path)
    sftp.close()

    return local_zip_path

# Create the startup zip at launch
if ssh:
    print("✅ SSH connection established.")
    ensure_remote_dependencies(ssh)
    startup_zip = create_and_download_zip("home_backup_startup.zip")
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
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"home_backup_{timestamp}.zip"
        zip_path = create_and_download_zip(filename)

        if not zip_path:
            return jsonify({"error": "Failed to create ZIP"}), 500

        # Move the zip to a dedicated current zip directory
        stored_path = os.path.join(CURRENT_ZIP_DIR, filename)
        os.rename(zip_path, stored_path)

        return send_file(stored_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7001, debug=False)
