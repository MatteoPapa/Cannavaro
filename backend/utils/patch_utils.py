import os
from datetime import datetime
from werkzeug.utils import secure_filename
from .db_utils import connect_to_mongo
import posixpath
import shutil
import tempfile
from utils.logging_utils import log
# Directory to save uploaded patch files
PATCH_UPLOAD_DIR = "uploaded_patches"
BACKUP_DIR = "backups"
os.makedirs(PATCH_UPLOAD_DIR, exist_ok=True)

def save_patch_file(file):
    original_filename = secure_filename(file.filename)
    timestamped_filename = f"{datetime.utcnow().isoformat()}_{original_filename}"
    filepath = os.path.join(PATCH_UPLOAD_DIR, timestamped_filename)
    file.save(filepath)
    return original_filename, filepath

def log_patch_to_db(service, description, filename, filepath, backup_zip_path=None):
    client, db = connect_to_mongo()
    if db is None:
        raise Exception("Database connection failed")

    patch = {
        "service": service,
        "description": description,
        "timestamp": datetime.utcnow(),
        "filename": filename,
        "filepath": filepath,
        "backup_zip_path": backup_zip_path,
        "status": "pending"
    }

    result = db.patches.insert_one(patch)
    return result.inserted_id

def get_patches_by_service(service_name):
    client, db = connect_to_mongo()
    if db is None:
        raise Exception("Database connection failed")

    patches = db.patches.find({"service": service_name}).sort("timestamp", -1)
    return [
        {
            "id": str(patch["_id"]),
            "service": patch["service"],
            "description": patch["description"],
            "filename": patch["filename"],
            "filepath": patch["filepath"],
            "timestamp": patch.get("timestamp"),
            "status": patch.get("status"),
        }
        for patch in patches
    ]

def apply_patch_on_vm_stream(ssh, filename, file_obj, service_name):
    if ssh is None:
        return {"success": False, "message": "SSH not connected"}

    try:
        print(f"Searching for '{filename}' in /root/{service_name}")
        search_command = f"find /root/{service_name} -type f -name '{filename}'"
        stdin, stdout, stderr = ssh.exec_command(search_command)
        found_paths = stdout.read().decode().strip().split("\n")
        found_paths = [p for p in found_paths if p]

        if not found_paths:
            print("Target file not found on VM")
            return {"success": False, "message": "File not found on VM"}

        remote_file_path = found_paths[0]
        print(f"Target file path: {remote_file_path}")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Step 2: Download just that file to a temp directory
        temp_dir = tempfile.mkdtemp(prefix=f"{service_name}_patch_")
        local_backup_path = os.path.join(temp_dir, filename)

        sftp = ssh.open_sftp()
        sftp.get(remote_file_path, local_backup_path)
        sftp.close()
        print(f"Downloaded file for backup: {local_backup_path}")

        # Step 3: Create zip backup of the file
        from utils.zip_utils import create_local_backup_zip
        backup_zip_name = f"{service_name}_{filename}_backup_{timestamp}.zip"
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_zip_path = os.path.join(BACKUP_DIR, backup_zip_name)
        create_local_backup_zip(temp_dir, backup_zip_path)
        if not os.path.exists(backup_zip_path):
            raise FileNotFoundError(f"Expected backup zip was not created: {backup_zip_path}")
        else:
            print(f"Backup zip exists: {backup_zip_path}")

        shutil.rmtree(temp_dir)

        # Step 4: Upload and overwrite the file on the VM
        print("Uploading new file content to VM")
        sftp = ssh.open_sftp()
        with sftp.file(remote_file_path, 'wb') as remote_file:
            file_obj.seek(0)
            shutil.copyfileobj(file_obj, remote_file)
        sftp.close()

        print("Patch applied successfully")
        return {
            "success": True,
            "message": "Patch applied successfully",
            "backup": backup_zip_path,
            "filepath": remote_file_path,
        }

    except Exception as e:
        print("Failed to apply patch")
        return {"success": False, "message": str(e)}

def rolling_restart_docker_service(ssh, container_name, service_path, exclude_containers=None):
    """
    Perform a rolling restart:
    - Build all services in the project (non-blocking)
    - Restart each container (excluding locked ones), one at a time
    """
    import logging
    log = logging.getLogger(__name__)

    log.info("Rolling restart: %s (path: %s)", container_name, service_path)
    exclude_containers = set(exclude_containers or [])

    # 1. Get list of services
    list_cmd = f"cd {service_path} && docker compose config --services"
    stdin, stdout, stderr = ssh.exec_command(list_cmd)
    services = stdout.read().decode().splitlines()
    if stdout.channel.recv_exit_status() != 0:
        error = stderr.read().decode().strip()
        log.error("[ERROR] Failed to list services: %s", error)
        return {"success": False, "error": error}

    restart_targets = [s for s in services if s not in exclude_containers]
    if not restart_targets:
        return {"success": True, "message": "No services to restart (all excluded)."}

    # 2. Build everything up-front
    build_cmd = f"cd {service_path} && docker compose build {' '.join(restart_targets)}"
    log.info("Building: %s", build_cmd)
    stdin, stdout, stderr = ssh.exec_command(build_cmd)
    if stdout.channel.recv_exit_status() != 0:
        error = stderr.read().decode().strip()
        log.error("[ERROR] Build failed:\n%s", error)
        return {"success": False, "error": error}

    # 3. Restart each service one-by-one
    failed = {}
    for svc in restart_targets:
        restart_cmd = f"cd {service_path} && docker compose up -d --no-deps --force-recreate {svc}"
        log.info("Restarting service: %s", svc)
        stdin, stdout, stderr = ssh.exec_command(restart_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            failed[svc] = stderr.read().decode().strip()

    if failed:
        for svc, msg in failed.items():
            log.error("[ERROR] Restart failed for %s: %s", svc, msg)
        return {"success": False, "error": failed}

    return {"success": True, "restarted": restart_targets}



