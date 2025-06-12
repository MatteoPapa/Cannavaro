from flask import Flask, jsonify, send_file, request, after_this_request, send_from_directory
from flask_cors import CORS
import os
from bson import ObjectId
from utils.zip_utils import *
from utils.db_utils import *
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

# ─── Init Database ─────────────────────────
mongo_client, db = connect_to_mongo()

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


@app.route("/api/service_locks")
def get_service_locks():
    parent = request.args.get("parent")
    if not parent:
        return jsonify({"error": "Missing 'parent' query param"}), 400
    doc = db.service_locks.find_one({"parent": parent})
    locked = doc.get("locked", []) if doc else []
    return jsonify({"locked": locked})

@app.route("/api/service_locks", methods=["POST"])
def update_service_locks():
    data = request.get_json()
    parent = data.get("parent")
    service = data.get("service")
    lock = data.get("lock")  # true to lock, false to unlock

    if not parent or not service:
        return jsonify({"error": "Missing 'parent' or 'service' in body"}), 400

    doc = db.service_locks.find_one({"parent": parent}) or {"parent": parent, "locked": []}
    locked = set(doc.get("locked", []))

    if lock:
        locked.add(service)
    else:
        locked.discard(service)

    db.service_locks.update_one(
        {"parent": parent},
        {"$set": {"locked": list(locked)}},
        upsert=True
    )
    return jsonify({"locked": list(locked)})


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
    """
    POST body:
        {
          "service": "parent-stack-name"
        }
    """
    data = request.get_json(silent=True) or {}
    parent = data.get("service")

    if not parent:
        return jsonify({"error": "Missing 'service' in request"}), 400

    # Get the parent entry
    parent_entry = next((s for s in config["services"] if s["name"] == parent), None)
    if not parent_entry:
        return jsonify({"error": f"Parent service '{parent}' not found in config"}), 404

    subservices = parent_entry.get("services", [])

    # 2. Get locked services from DB
    lock_doc = db.service_locks.find_one({"parent": parent}) or {}
    locked = set(lock_doc.get("locked", []))
    service_path = f"/root/{parent}"
    log.info(f"Resetting Docker for parent service: {parent} at path {service_path}")
    failed, restarted = [], []

    for svc_obj in subservices:
        svc = svc_obj['name']

        if svc in locked:
            continue

        result = rolling_restart_docker_service(ssh, svc, service_path)
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
        "message": "Unlocked services restarted successfully.",
        "restarted": restarted
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
