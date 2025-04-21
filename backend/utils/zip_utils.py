# backend/utils/zip_utils.py
import zipfile
import os
import datetime

def setup_zip_dirs(base_dir):
    startup_zip_path = os.path.join(base_dir, 'home_backup_startup.zip')
    current_zip_dir = os.path.join(base_dir, 'current_zips')
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(current_zip_dir, exist_ok=True)
    return startup_zip_path, current_zip_dir

def create_and_download_zip(ssh, base_dir, filename="home_backup.zip"):
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

    local_zip_path = os.path.join(base_dir, filename)
    sftp.get(remote_zip_path, local_zip_path)

    # Clean up the remote zip after successful download
    try:
        sftp.remove(remote_zip_path)
    except Exception as e:
        print(f"⚠️ Warning: Failed to delete remote zip file: {e}")

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