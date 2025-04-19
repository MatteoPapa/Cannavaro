import paramiko
import os

def ensure_remote_dependencies(ssh):
    """
    Installs required packages on the remote VM using apt.
    Currently installs: zip
    """
    try:
        print("📦 Ensuring dependencies are installed on remote VM...")

        # Update apt and install zip silently
        update_cmd = "apt-get update -y"
        install_cmd = "apt-get install -y zip"

        # Run both commands and wait for them to complete
        for cmd in [update_cmd, install_cmd]:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                err = stderr.read().decode()
                raise Exception(f"Failed to run '{cmd}': {err}")

        print("✅ Remote dependencies installed.")
    except Exception as e:
        print("❌ Failed to install dependencies:", e)
        
def setup_ssh_authorized_key(config):
    vm_ip = config.get("vm_ip")
    ssh_port = config.get("ssh_port", 22)
    password = config.get("vm_password")

    pub_key_path = "/root/.ssh/id_rsa.pub"
    if not os.path.exists(pub_key_path):
        print("⚠️ SSH public key not found inside container:", pub_key_path)
        return None

    with open(pub_key_path, 'r') as key_file:
        pub_key = key_file.read().strip()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vm_ip, port=ssh_port, username='root', password=password)

        # Setup ~/.ssh and authorized_keys
        ssh.exec_command('mkdir -p ~/.ssh && chmod 700 ~/.ssh')
        ssh.exec_command('touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys')

        # Avoid duplicates
        check_and_add_cmd = f'grep -qxF "{pub_key}" ~/.ssh/authorized_keys || echo "{pub_key}" >> ~/.ssh/authorized_keys'
        _, stdout, stderr = ssh.exec_command(check_and_add_cmd)

        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print("STDOUT:", out)
        if err:
            print("STDERR:", err)

        print("✅ Public key successfully ensured on VM.")
        return ssh  # 👈 return the active session

    except Exception as e:
        print("❌ Failed to add public key to VM:", e)
        return None


