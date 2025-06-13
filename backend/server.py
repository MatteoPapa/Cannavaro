from flask import Flask, jsonify, send_file, request, after_this_request, send_from_directory
from flask_cors import CORS
import os
from bson import ObjectId
from utils.zip_utils import *
from utils.services_utils import *
from utils.logging_utils import log


# ─── Paths & Constants ─────────────────────
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')
ZIP_BASE_DIR = os.path.join(BASE_DIR, 'zip')
STARTUP_ZIP_PATH, CURRENT_ZIP_DIR = setup_zip_dirs(ZIP_BASE_DIR)

# ─── Flask App ─────────────────────────────
app = Flask(__name__)
CORS(app)

# ─── Globals  ──────────────────────────
config = None
ssh = None

def set_dependencies(ext_config, ext_ssh):
    global config, ssh
    config = ext_config
    ssh = ext_ssh

# ─── API Routes ────────────────────────────
@app.route("/api/vm_ip")
def get_vm_ip():
    return jsonify(config.get("remote_host", "No VM IP configured"))

@app.route("/api/services")
def get_services():
    services = config.get("services", None)
    if not services:
        return jsonify({"error": "No services configured"}), 400

    name = request.args.get("name")
    if not name:
        return jsonify(services)

    match = next((s for s in services if s["name"] == name), None)
    if match:
        return jsonify(match)

    return jsonify({"error": "Service not found", "available": [s['name'] for s in services]}), 400

YAML_FILE = "services.yaml"

@app.route("/api/service_locks")
def get_service_locks():
    parent = request.args.get("parent")
    if not parent:
        return jsonify({"error": "Missing 'parent' query param"}), 400

    # Load YAML
    with open(YAML_FILE, "r") as f:
        services = yaml.safe_load(f)

    locked_services = []
    for group in services.get("services", []):
        if group["name"] == parent:
            for subservice in group.get("services", []):
                if subservice.get("locked"):
                    locked_services.append(subservice["name"])
            break

    return jsonify({"locked": locked_services})

@app.route("/api/service_locks", methods=["POST"])
def update_service_locks():
    data = request.get_json()
    parent = data.get("parent")
    service_name = data.get("service")
    lock = data.get("lock")

    if not parent or not service_name:
        return jsonify({"error": "Missing 'parent' or 'service' in body"}), 400

    services = config.get("services")
    if not services:
        return jsonify({"error": "No services configured"}), 400

    updated = False
    for service in services:
        if service["name"] == parent:
            for subservice in service.get("services", []):
                if subservice["name"] == service_name:
                    subservice["locked"] = bool(lock)
                    updated = True
                    break
            break  # parent found, no need to keep looping

    if not updated:
        return jsonify({"error": "Service not found"}), 404

    # Return currently locked services for this parent
    locked = [
        s["name"]
        for g in services
        if g["name"] == parent
        for s in g.get("services", [])
        if s.get("locked") is True
    ]

    return jsonify({"locked": locked})

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

        # Ensure target folder exists
        os.makedirs(CURRENT_ZIP_DIR, exist_ok=True)

        os.rename(temp_zip_path, stored_path)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(stored_path)
            except Exception as e:
                log.error(f"Failed to delete temporary zip: {e}")
            return response

        return send_file(stored_path, as_attachment=True)

    except Exception as e:
        log.error(f"Error creating current zip: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/reset_docker", methods=["POST"])
def reset_docker():
    # 1. Get service name (parent) from request body
    data = request.get_json(silent=True) or {}
    parent = data.get("service")

    if not parent:
        return jsonify({"error": "Missing 'service' in request"}), 400
    
    # 2. Locate the parent entry
    parent_entry = next((s for s in config.get("services", []) if s["name"] == parent), None)
    if not parent_entry:
        return jsonify({"error": f"Parent service '{parent}' not found in config"}), 404

    subservices = parent_entry.get("services", [])

    service_path = f"/root/{parent}"
    log.info(f"Resetting Docker for parent service: {parent} at path {service_path}")

    failed, restarted = [], []
    to_restart = []
    has_locked = False
    for svc_obj in subservices:
        svc = svc_obj['name']
        if svc_obj.get("locked"):
            log.info(f"Skipping locked service: {svc}")
            has_locked = True
        else:
            to_restart.append(svc)

    if not has_locked:
        result = restart_docker_service(ssh, parent) # Common docker restart
    else:
        result = rolling_restart_docker_service(ssh, service_path, to_restart) # Rolling restart

    if result.get("success"):
        restarted.extend(result.get("restarted", []))
    else:
        failed.append({"service": svc, "error": result.get("error")})

    if failed:
        return jsonify({
            "error": "Some services failed to restart",
            "details": failed
        }), 500

    return jsonify({
        "message": "Unlocked services restarted successfully."
    }), 200

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        log.info(f"Serving static file: {path}")
        return send_from_directory(app.static_folder, path)
    else:
        log.info("Serving index.html")
        return send_from_directory(app.static_folder, 'index.html')

def run_server():
    app.run(host='0.0.0.0', port=7000, debug=False)

if __name__ == "__main__":
    run_server()
