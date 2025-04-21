import os
from datetime import datetime
from werkzeug.utils import secure_filename
from .db_utils import connect_to_mongo
import posixpath
import shutil

# Directory to save uploaded patch files
PATCH_UPLOAD_DIR = "uploaded_patches"
os.makedirs(PATCH_UPLOAD_DIR, exist_ok=True)

def save_patch_file(file):
    original_filename = secure_filename(file.filename)
    timestamped_filename = f"{datetime.utcnow().isoformat()}_{original_filename}"
    filepath = os.path.join(PATCH_UPLOAD_DIR, timestamped_filename)
    file.save(filepath)
    return original_filename, filepath

def log_patch_to_db(service, description, filename, filepath):
    client, db = connect_to_mongo()
    if db is None:
        raise Exception("Database connection failed")

    patch = {
        "service": service,
        "description": description,
        "timestamp": datetime.utcnow(),
        "filename": filename,
        "filepath": filepath,
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

BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

def apply_patch_on_vm_stream(ssh, filename, file_obj, service_name):
    if ssh is None:
        return {"success": False, "message": "SSH not connected"}

    try:
        # Step 1: Search for file on remote
        search_command = f"find /root/{service_name} -type f -name '{filename}'"
        stdin, stdout, stderr = ssh.exec_command(search_command)
        found_paths = stdout.read().decode().strip().split("\n")
        found_paths = [p for p in found_paths if p]

        if not found_paths:
            return {"success": False, "message": "File not found on VM"}

        remote_file_path = found_paths[0]
        remote_folder = posixpath.dirname(remote_file_path)
        parent_folder_name = posixpath.basename(remote_folder)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Step 2: Download folder to local temp, zip for backup
        temp_download_path = os.path.join("temp_downloads", f"{parent_folder_name}_{timestamp}")
        os.makedirs(temp_download_path, exist_ok=True)

        sftp = ssh.open_sftp()

        def recursive_download(remote_dir, local_dir):
            os.makedirs(local_dir, exist_ok=True)
            for entry in sftp.listdir_attr(remote_dir):
                remote_path = posixpath.join(remote_dir, entry.filename)
                local_path = os.path.join(local_dir, entry.filename)
                if str(entry.longname).startswith('d'):  # Directory
                    recursive_download(remote_path, local_path)
                else:
                    sftp.get(remote_path, local_path)

        recursive_download(remote_folder, temp_download_path)
        sftp.close()

        # Step 3: Zip the downloaded folder locally
        from utils.zip_utils import create_local_backup_zip
        BACKUP_DIR = "backups"
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_zip_name = f"{service_name}_backup_{timestamp}.zip"
        backup_zip_path = os.path.join(BACKUP_DIR, backup_zip_name)
        create_local_backup_zip(temp_download_path, backup_zip_path)

        # Optional: clean up the temp download
        shutil.rmtree(temp_download_path)

        # Step 4: Upload and replace the file on the VM using file_obj stream
        sftp = ssh.open_sftp()
        with sftp.file(remote_file_path, 'wb') as remote_file:
            file_obj.seek(0)
            shutil.copyfileobj(file_obj, remote_file)
        sftp.close()

        return {
            "success": True,
            "message": "Patch applied successfully",
            "backup": backup_zip_path
        }

    except Exception as e:
        return {"success": False, "message": str(e)}
