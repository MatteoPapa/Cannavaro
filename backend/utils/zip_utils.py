# backend/utils/zip_utils.py
import zipfile
import os
import datetime
from utils.logging_utils import log
import threading

def setup_zip_dirs(base_dir):
    startup_zip_path = os.path.join(base_dir, 'home_backup_startup.zip')
    current_zip_dir = os.path.join(base_dir, 'current_zips')
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(current_zip_dir, exist_ok=True)
    return startup_zip_path, current_zip_dir

def create_and_download_zip(ssh, base_dir, filename="home_backup.zip"):
    # Ensure zip folder exists
    os.makedirs(base_dir, exist_ok=True)

    remote_dir_to_zip = "/root"
    remote_zip_path = f"/root/{filename}"

    # Avoid recursive inclusion
    ssh.exec_command(f'rm -f {remote_zip_path}')
    
    zip_cmd = f'cd {remote_dir_to_zip} && zip -r {filename} *'
    
    result = {}

    def run_zip():
        try:
            stdin, stdout, stderr = ssh.exec_command(zip_cmd)
            stdout.channel.recv_exit_status()
            result['status'] = 'success'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

    thread = threading.Thread(target=run_zip)
    thread.start()
    thread.join(timeout=5)

    if thread.is_alive():
        log.error("❌ Remote zip creation took too long (over 5 seconds). Aborting.")
        # Optional: clean up potentially partial zip
        ssh.exec_command(f'rm -f {remote_zip_path}')
        return None

    if result.get('status') == 'error':
        log.error(f"❌ Failed to run zip command: {result.get('error')}")
        return None

    sftp = ssh.open_sftp()
    try:
        sftp.stat(remote_zip_path)
    except FileNotFoundError:
        log.error(f"❌ Remote zip file {remote_zip_path} not found.")
        sftp.close()
        return None

    local_zip_path = os.path.join(base_dir, filename)
    sftp.get(remote_zip_path, local_zip_path)

    # Clean up the remote zip after successful download
    try:
        sftp.remove(remote_zip_path)
    except Exception as e:
        log.warning(f"⚠️ Failed to delete remote zip file: {e}")

    sftp.close()
    return local_zip_path


def create_timestamped_filename():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"home_backup_{timestamp}.zip"

def create_local_backup_zip(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, folder_path)
                zipf.write(full_path, rel_path)