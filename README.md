# Cannavaro 🛡️  
*A Defensive Line for A/D CTFs – Now with Git Magic*

<h3 align="center">
  <img src="https://github.com/user-attachments/assets/fb32d4e0-c403-48b5-8dab-5f74b3015e21" alt="Cannavaro Screenshot" />
</h3>

**Cannavaro**  is a tactical automation toolkit built for the defense side of Attack/Defense Capture The Flag (CTF) competitions.
It streamlines service patching by initializing and configuring Git repositories on remote VMs, enabling clean version control, collaborative workflows, and rollback-friendly deployments.
Designed for speed, clarity, and control, Cannavaro automates SSH setup, Git bootstrapping, patch delivery, and Docker restarts — so you can focus on defending, not debugging.
Named after Fabio Cannavaro — the last defender you want to get past.
---

## 🧠 What It Does

- 🔐 **SSH Automation** – Securely sets up SSH access to remote virtual machines and installs authorized keys.
- 📦 **Git Repo Magic** – Initializes a Git repository for each service and configures it for collaboration.
- 🔍 **Service Discovery** – Lists all configured services and subservices.
- 🕹️ **Easy File Download** – Download current and startup versions of remote files as ZIPs for fast recovery.
- 🔄 **Docker Restarts** – Restart Docker services (selectively or in bulk), respecting service lock status.

---

## 🚀 Getting Started

1. **Edit Configuration**  
   Modify `backend/config.yaml` to match your environment and services.

2. **Start Cannavaro**  
   Using Docker Compose:
   ```bash
   docker compose up --build
   ```

3. **Access**  
   By default Cannavaro is exposed on port 7000.

---

## ⚙️ Tech Stack

- 🧠 **Backend**: Flask (Python)
- 🎨 **Frontend**: React + Vite.js
- 🧩 **UI**: Material UI
- 🐋 **Containerization**: Docker + Docker Compose

---

## 🤝 Contributions

Coming soon — but feel free to fork and adapt during competitions!

---

Good luck, and may your services never go down! 🛡️⚔️
