# Cannavaro 🛡️

<h3 align="center">
  <img src="https://github.com/user-attachments/assets/fb32d4e0-c403-48b5-8dab-5f74b3015e21" alt="Cannavaro Screenshot" />
</h3>

**Cannavaro** is a powerful tool built to streamline and support the defense side of Attack/Defense Capture The Flag (CTF) competitions.

It automates tedious tasks, enables easy patching of remote services, and provides a modern interface for applying and managing changes on-the-fly.

---

## 🧠 What It Does

- 🔐 Seamless SSH setup – Automatically configures SSH access to remote virtual machines.
- 🔍 Service discovery – Detects and lists all active services on the remote VM, along with their exposed ports.
- 📦 File versioning – Allows you to download both the original and current versions of remote files as ZIP archives.
- 🩹 Effortless patching – Apply patches by simply dragging and dropping the modified files.
- ↩️ One-click rollback – Instantly revert to a previous state if a patch doesn't work as expected.

---

## 🚀 Getting Started

You can run **Cannavaro** using Docker Compose. Even easier, just use the provided startup scripts:

- On **Windows**: run `start.bat`
- On **Linux/macOS/WSL**: run `start.sh`

### Manual Setup

If a services.yaml file is present in the backend/ directory, the server will resume from the previous session.
To start fresh, simply delete this file before launching the containers.

```bash
docker compose down
docker compose up --build
```

---

## ⚙️ Tech Stack

- 🧠 **Backend**: Flask (Python)
- 🎨 **Frontend**: React + Vite.js
- 🧩 **UI**: Material UI for a sleek, modern interface
- 🐋 **Containerization**: Docker + Docker Compose
- 🧱 **Database**: MongoDB (used for storing and retrieving session-related data)

---

## 📁 Project Structure

```
Cannavaro/
├── backend/
│   ├── services.yaml (generated during usage)
│   └── ... (Flask app)
├── frontend/
│   └── ... (React app)
├── start.sh
├── start.bat
└── docker-compose.yml
```

---

## 🤝 Contributions

Coming soon — for now, feel free to fork the repo or use it privately during competitions!

---

## 📢 Notes

- Designed for fast-paced competitive environments — keep your head in the game, not in the terminal.
- Cannavaro is named after Fabio Cannavaro — a wall in defense, just like this tool aims to be.

Good luck, and happy defending! 🛡️⚔️
