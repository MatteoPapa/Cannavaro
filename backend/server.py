import os
import threading
import time
from flask import Flask, jsonify, send_file, request, after_this_request, send_from_directory
from flask_cors import CORS
from bson import ObjectId
from utils.zip_utils import *
from utils.services_utils import *
from utils.logging_utils import log
from utils.proxy_utils import *
from utils.ssh_utils import *

# ─── Paths & Constants ─────────────────────
BASE_DIR = os.path.dirname(__file__)
ZIP_BASE_DIR = os.path.join(BASE_DIR, 'zip')
STARTUP_ZIP_PATH, CURRENT_ZIP_DIR = setup_zip_dirs(ZIP_BASE_DIR)

# ─── Flask App ─────────────────────────────
app = Flask(__name__)
CORS(app)

# ─── Globals ───────────────────────────────
config = None
ssh = None

# ─── SSH Management ────────────────────────
def set_dependencies(ext_config, ext_ssh):
    global config, ssh
    config = ext_config
    ssh = ext_ssh


def get_active_ssh():
    global ssh
    if not is_ssh_active(ssh):
        log.warning("SSH inactive — reconnecting...")
        ssh = ssh_connect(config)
    return ssh

# ─── Utility ───────────────────────────────
def get_service_by_name(name):
    return next((s for s in config.get("services", []) if s["name"] == name), None)

# ─── Routes ────────────────────────────────
@app.route("/api/vm_ip")
def get_vm_ip():
    return jsonify(config.get("remote_host", "No VM IP configured"))

@app.route("/api/services")
def get_services():
    name = request.args.get("name")
    services = config.get("services", [])
    if not name:
        return jsonify(services)

    service = get_service_by_name(name)
    if service:
        return jsonify(service)
    return jsonify({"error": "Service not found", "available": [s['name'] for s in services]}), 400

@app.route("/api/service_locks", methods=["GET", "POST"])
def service_locks():
    if request.method == "GET":
        parent = request.args.get("parent")
        if not parent:
            return jsonify({"error": "Missing 'parent' param"}), 400
        service = get_service_by_name(parent)
        if not service:
            return jsonify({"error": "Service not found"}), 400
        locked = [s["name"] for s in service.get("services", []) if s.get("locked")]
        return jsonify({"locked": locked})

    data = request.get_json()
    parent = data.get("parent")
    sub = data.get("service")
    lock = data.get("lock")

    service = get_service_by_name(parent)
    if not service:
        return jsonify({"error": "Parent not found"}), 400

    for s in service.get("services", []):
        if s["name"] == sub:
            s["locked"] = bool(lock)
            break
    else:
        return jsonify({"error": "Subservice not found"}), 404

    locked = [s["name"] for s in service.get("services", []) if s.get("locked")]
    return jsonify({"locked": locked})

@app.route("/api/get_startup_zip")
def get_startup_zip():
    if not os.path.exists(STARTUP_ZIP_PATH):
        return jsonify({"error": "Startup ZIP not found"}), 404
    return send_file(STARTUP_ZIP_PATH, as_attachment=True)

@app.route("/api/get_current_zip")
def get_current_zip():
    try:
        active_ssh = get_active_ssh()
        filename = create_timestamped_filename()
        zip_path = create_and_download_zip(active_ssh, ZIP_BASE_DIR, filename)

        if not zip_path:
            return jsonify({"error": "Failed to create ZIP"}), 500

        dest_path = os.path.join(CURRENT_ZIP_DIR, filename)
        os.makedirs(CURRENT_ZIP_DIR, exist_ok=True)
        os.rename(zip_path, dest_path)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(dest_path)
            except Exception as e:
                log.error(f"Cleanup failed: {e}")
            return response

        return send_file(dest_path, as_attachment=True)
    except Exception as e:
        log.error(f"ZIP error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_git_key")
def get_git_key():
    path = config.get("local_private_key_file")
    if not path or not os.path.exists(path):
        return jsonify({"error": "Git key not configured or missing"}), 404
    return send_file(path, as_attachment=True)

@app.route("/api/reset_docker", methods=["POST"])
def reset_docker():
    data = request.get_json()
    parent, sub = data.get("service"), data.get("subservice")
    active_ssh = get_active_ssh()

    service = get_service_by_name(parent)
    if not service:
        return jsonify({"error": "Service not found"}), 404

    unlocked = [s["name"] for s in service["services"] if not s.get("locked")]
    to_restart = [sub] if sub else unlocked

    if not to_restart:
        return jsonify({"error": "No services to restart"}), 400

    path = f"/root/{parent}"
    if not sub:
        result = restart_docker_service(active_ssh, parent)
    else:
        result = rolling_restart_docker_service(active_ssh, path, to_restart)

    if result.get("success"):
        return jsonify({"message": "Services restarted", "restarted": result.get("restarted", [])})
    return jsonify({"error": result.get("error")}), 500

@app.route("/api/install_proxy", methods=["POST"])
def install_proxy():
    data = request.get_json()

    parent = data.get("service")
    sub = data.get("subservice")
    port = data.get("port", None)
    tls_enabled = data.get("tlsEnabled", False)
    server_cert = data.get("serverCert")
    server_key = data.get("serverKey")
    protocol = data.get("protocol", "http")
    dump_pcaps = data.get("dumpPcaps", False)
    pcap_path = data.get("pcapPath")
    proxy_type = data.get("proxyType", "AngelPit")

    active_ssh = get_active_ssh()

    #TODO: Multiple proxy for the same service?
    if is_proxy_installed(active_ssh, parent):
        return jsonify({"error": "Proxy already installed"}), 400

    service = get_service_by_name(parent)

    # Build a configuration dictionary to pass to the install function
    proxy_config = {
        "port": port,
        "tls_enabled": tls_enabled,
        "server_cert": server_cert,
        "server_key": server_key,
        "protocol": protocol,
        "dump_pcaps": dump_pcaps,
        "pcap_path": pcap_path,
        "proxy_type": proxy_type,
    }
    log.info(f"Installing proxy for {parent} with config: {proxy_config}")
    result = install_proxy_for_service(active_ssh, config, parent, sub, proxy_config)

    if result.get("success"):
        if service:
            service["proxied"] = True
        return jsonify({"message": "Proxy installed"})

    return jsonify({"error": result.get("error", "Unknown error")}), 500


@app.route("/api/get_proxy_logs", methods=["POST"])
def get_proxy_logs():
    data = request.get_json()

    service = data.get("service")
    if not service:
        return jsonify({"error": "Missing 'service' in request"}), 400

    active_ssh = get_active_ssh()
    if not active_ssh:
        return jsonify({"error": "SSH connection not available"}), 500

    result = get_logs(active_ssh, service)

    if result.get("success"):
        return jsonify({"logs": result["logs"]})

    return jsonify({"error": result.get("error")}), 500

@app.route("/api/get_proxy_code", methods=["POST"])
def get_proxy_code():
    data = request.get_json()

    service = data.get("service")
    if not service:
        return jsonify({"error": "Missing 'service' in request"}), 400

    active_ssh = get_active_ssh()
    if not active_ssh:
        return jsonify({"error": "SSH connection not available"}), 500

    result = get_code(active_ssh, service)

    if result.get("success"):
        return jsonify({"code": result["code"]})

    return jsonify({"error": result.get("error")}), 500

@app.route("/api/get_proxy_regex", methods=["POST"])
def get_proxy_regex():
    data = request.get_json()
    service = data.get("service")

    if not service:
        return jsonify({"error": "Missing 'service' in request"}), 400

    active_ssh = get_active_ssh()
    if not active_ssh:
        return jsonify({"error": "SSH connection not available"}), 500

    result = get_regex(active_ssh, service)

    if result.get("success"):
        return jsonify({"regex": result["regex"]})

    return jsonify({"error": result.get("error")}), 500

@app.route("/api/save_proxy_code", methods=["POST"])
def save_proxy_code():
    data = request.get_json()
    service = data.get("service")
    code = data.get("code")
    active_ssh = get_active_ssh()

    if not code:
        return jsonify({"error": "No code provided"}), 400

    result = save_code(active_ssh, service, code)
    if result.get("success"):
        return jsonify({"message": "Code saved successfully"})
    return jsonify({"error": result.get("error")}), 500

@app.route("/api/save_proxy_regex", methods=["POST"])
def save_proxy_regex():
    data = request.get_json()
    service = data.get("service")
    regex_list = data.get("regex")

    if not service:
        return jsonify({"error": "Missing 'service' in request"}), 400
    if not isinstance(regex_list, list):
        return jsonify({"error": "'regex' must be a list"}), 400

    active_ssh = get_active_ssh()
    if not active_ssh:
        return jsonify({"error": "SSH connection not available"}), 500

    result = save_regex(active_ssh, service, regex_list)

    if result.get("success"):
        return jsonify({"message": result.get("message", "Regex saved successfully")})

    return jsonify({"error": result.get("error")}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    target = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(target):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


def run_server():
    create_and_download_zip(get_active_ssh(), ZIP_BASE_DIR, filename="home_backup_startup.zip")
    app.run(host='0.0.0.0', port=7000, debug=False)

if __name__ == "__main__":
    run_server()
