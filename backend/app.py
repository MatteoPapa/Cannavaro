from flask import Flask, jsonify, send_file
from flask_cors import CORS
import yaml
import os

from utils import *

app = Flask(__name__)
CORS(app)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
ssh = setup_ssh_authorized_key(config)

if ssh:
    print("✅ SSH connection established.")
    ensure_remote_dependencies(ssh)

@app.route("/api/vm_ip")
def get_vm_ip():
    return jsonify(config.get("vm_ip", "No VM IP configured"))

@app.route("/api/services")
def get_services():
    return jsonify(config.get("services", "No services configured"))

@app.route("/api/get_zip")
def get_zip():
    if not ssh:
        return jsonify({"error": "SSH not connected"}), 500

    try:
        remote_dir_to_zip = "/root"
        remote_zip_path = "/root/home_backup.zip"
        local_zip_dir = os.path.join(os.path.dirname(__file__), 'zip')
        local_zip_path = os.path.join(local_zip_dir, 'home_backup.zip')

        # Remove previous zip file to avoid recursive inclusion
        ssh.exec_command(f'rm -f {remote_zip_path}')

        # Create ZIP of all contents inside /root, excluding the zip file itself
        zip_cmd = f'cd {remote_dir_to_zip} && zip -r home_backup.zip *'
        stdin, stdout, stderr = ssh.exec_command(zip_cmd)
        stdout.channel.recv_exit_status()  # Wait for command to finish

        # Ensure local folder exists
        os.makedirs(local_zip_dir, exist_ok=True)

        # Download the ZIP using SFTP
        sftp = ssh.open_sftp()

        try:
            sftp.stat(remote_zip_path)  # raises IOError if not found
        except FileNotFoundError:
            return jsonify({"error": "ZIP file not found on VM"}), 404

        sftp.get(remote_zip_path, local_zip_path)
        sftp.close()

        return send_file(local_zip_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7001)
