from flask import Flask, jsonify, send_file, request, after_this_request, send_from_directory
from flask_cors import CORS
import os
from bson import ObjectId
from core.initializer import *
from utils.zip_utils import *
from utils.db_utils import *
from utils.patch_utils import *

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

# ─── Init Database ─────────────────────────
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

        # Ensure target folder exists
        os.makedirs(CURRENT_ZIP_DIR, exist_ok=True)

        os.rename(temp_zip_path, stored_path)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(stored_path)
            except Exception as e:
                print(f"Failed to delete temporary zip: {e}")
            return response

        return send_file(stored_path, as_attachment=True)

    except Exception as e:
        print(f"Error creating current zip: {e}")   
        return jsonify({"error": str(e)}), 500

@app.route("/api/patches/<service_name>")
def get_patches(service_name):
    try:
        patches = get_patches_by_service(service_name)
        return jsonify(patches), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/upload_patch", methods=["POST"])
def upload_patch():
    if "file" not in request.files or not request.form.get("service") or not request.form.get("description"):
        return jsonify({"error": "Missing file, service name, or description"}), 400

    file = request.files["file"]
    service = request.form["service"]
    description = request.form["description"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        # Step 1: Use the original filename
        filename = secure_filename(file.filename)

        # Step 2: Apply patch directly using file stream
        result = apply_patch_on_vm_stream(ssh, filename, file, service)

        if not result["success"]:
            print(f"Patch application failed: {result['message']}")
            return jsonify({"error": result["message"]}), 404

        # Step 3: Log patch only if all successful
        patch_id = log_patch_to_db(
            service,
            description,
            filename,
            result.get("filepath"),
            result.get("backup")
        )


        return jsonify({
            "message": "Patch uploaded, applied, and logged successfully",
            "patch_id": str(patch_id),
            "filename": filename,
            "backup": result.get("backup")
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/revert_patch/<patch_id>", methods=["POST"])
def revert_patch(patch_id):
    try:
        print(f"[REVERT] Reverting patch with ID: {patch_id}")

        if not ssh:
            print("[ERROR] SSH not connected")
            return jsonify({"error": "SSH not connected"}), 500

        patch = db.patches.find_one({"_id": ObjectId(patch_id)})
        if not patch:
            print(f"[ERROR] Patch not found: {patch_id}")
            return jsonify({"error": "Patch not found"}), 404

        if not patch.get("backup_zip_path") or not patch.get("filepath"):
            print(f"[ERROR] Missing backup or original filepath for patch: {patch_id}")
            return jsonify({"error": "Backup or filepath missing"}), 400

        backup_zip = patch["backup_zip_path"]
        original_remote_path = patch["filepath"]  # Exact remote file path
        filename = patch["filename"]
        remote_zip_path = f"/tmp/{os.path.basename(backup_zip)}"
        extracted_path = f"/tmp/{filename}"

        # Step 1: Transfer the backup zip to the VM
        print(f"[STEP 1] Sending ZIP to VM: {backup_zip} -> {remote_zip_path}")
        sftp = ssh.open_sftp()
        sftp.put(backup_zip, remote_zip_path)
        sftp.close()

        # Step 2: Unzip just that file in /tmp
        unzip_command = f"unzip -o {remote_zip_path} '{filename}' -d /tmp"
        print(f"[STEP 2] Unzipping on VM: {unzip_command}")
        stdin, stdout, stderr = ssh.exec_command(unzip_command)
        if stdout.channel.recv_exit_status() != 0:
            error_msg = stderr.read().decode().strip()
            print(f"[ERROR] Unzip failed: {error_msg}")
            return jsonify({"error": "Unzip failed", "details": error_msg}), 500

        # Step 3: Overwrite the file with the restored backup
        print(f"[STEP 3] Restoring file to: {original_remote_path}")
        copy_command = f"cp /tmp/{filename} {original_remote_path}"
        stdin, stdout, stderr = ssh.exec_command(copy_command)
        if stdout.channel.recv_exit_status() != 0:
            error_msg = stderr.read().decode().strip()
            print(f"[ERROR] Copy failed: {error_msg}")
            return jsonify({"error": "Restore failed", "details": error_msg}), 500

        # Step 4: Cleanup
        print(f"[STEP 4] Cleaning up ZIP and temp files")
        cleanup_commands = [
            f"rm -f {remote_zip_path}",
            f"rm -f /tmp/{filename}"
        ]
        for cmd in cleanup_commands:
            ssh.exec_command(cmd)

        # Step 5: Remove the patch record
        db.patches.delete_one({"_id": patch["_id"]})
        print(f"[SUCCESS] Patch reverted and deleted: {patch_id}")

        return jsonify({"message": f"Patch reverted and original file restored."}), 200

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/confirm_patch/<patch_id>", methods=["POST"])
def confirm_patch(patch_id):
    try:
        db.patches.update_one(
            {"_id": ObjectId(patch_id)},
            {"$set": {"status": "confirmed"}}
        )
        return jsonify({"message": "Patch confirmed."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        print(f"Serving static file: {path}")
        return send_from_directory(app.static_folder, path)
    else:
        print("Serving index.html")
        return send_from_directory(app.static_folder, 'index.html')
    
# ─── Run Server ────────────────────────────
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7000, debug=False)
