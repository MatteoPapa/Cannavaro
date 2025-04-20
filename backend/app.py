from flask import Flask, jsonify, send_file
from flask_cors import CORS
import os
from core.initializer import *
from utils.zip_utils import *
from utils.db_utils import *

# ─── Paths & Constants ─────────────────────
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')
SERVICES_YAML_PATH = os.path.join(BASE_DIR, 'services.yaml')
ZIP_BASE_DIR = os.path.join(BASE_DIR, 'zip')
STARTUP_ZIP_PATH, CURRENT_ZIP_DIR = setup_zip_dirs(ZIP_BASE_DIR)

# ─── Flask App ─────────────────────────────
app = Flask(__name__)
CORS(app)

# ─── Init VM & Services ────────────────────
config, ssh = initialize_vm_and_services(CONFIG_PATH, SERVICES_YAML_PATH, ZIP_BASE_DIR)

# ─── Init Database ────────────────────────────
mongo_client, db = connect_to_mongo()

# ─── API Routes ────────────────────────────
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

# ─── Run Server ────────────────────────────
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7001, debug=False)
