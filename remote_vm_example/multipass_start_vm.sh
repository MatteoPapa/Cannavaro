#!/bin/bash

# === LAUNCH VM ===
echo "🚀 Launching Multipass VM..."
multipass launch --name docker-vm --cloud-init cloud-config.yaml

# === COPY PROJECT FOLDERS (into /root using sudo) ===
VM_NAME="docker-vm"
SOURCE_BASE="/home/matteo-papa/Scrivania/Cannavaro/remote_vm_example"
PROJECTS=("Mudarabah" "Notes" "PCSS" "Pwnzer0tt1Shop")
REMOTE_TARGET="/root"

for folder in "${PROJECTS[@]}"; do
  LOCAL_PATH="$SOURCE_BASE/$folder"
  if [ -d "$LOCAL_PATH" ]; then
    echo "📁 Copying $folder to /home/ubuntu inside VM..."
    multipass transfer --recursive "$LOCAL_PATH" "$VM_NAME:/home/ubuntu/"
    echo "🚚 Moving $folder into /root inside VM..."
    multipass exec "$VM_NAME" -- sudo mv "/home/ubuntu/$(basename "$folder")" /root/
  else
    echo "⚠️ Skipping: $LOCAL_PATH does not exist"
  fi
done

# === GET IP ADDRESS ===
IP_ADDR=$(multipass info "$VM_NAME" | grep IPv4 | awk '{print $2}')