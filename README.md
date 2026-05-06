# ⚡ DarkLine Messenger

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-CustomTkinter-89b4fa)
![Encryption](https://img.shields.io/badge/Security-RSA%20%2B%20Fernet-a6e3a1)

**DarkLine Messenger** is a secure, local-network, client-server desktop chat application built with Python. It features robust end-to-end encryption, real-time presence tracking, secure file sharing, and an elegant, modern dark-themed UI.

Created by **MR.Thugh / Ali Kamrani** ([@MRThugh](https://github.com/MRThugh)).

---

## 📖 Table of Contents
- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [Architecture & Security](#-architecture--security)
- [Installation](#-installation)
- [Usage](#-usage)
- [Discussion & Philosophy](#-discussion--philosophy)
- [License](#-license)
- [Author](#-author)

---

## 💡 About the Project

DarkLine Messenger was designed to provide a secure and reliable way to communicate over local networks without relying on third-party servers. Whether you need a private chat system for your office, home network, or a LAN party, DarkLine ensures your data remains yours. 

The software includes a built-in server host, meaning any client can easily act as the central node for the network. It tracks users in real-time, stores encrypted chat history, and allows for large file transfers—all wrapped in a sleek `CustomTkinter` graphical interface.

---

## ✨ Key Features

- **🔒 Startup Security Gateway**: Users must log in or register before accessing any chat controls or rooms. Passwords are securely hashed using `bcrypt`.
- **🔑 Hybrid Encryption**: Uses RSA for secure key exchange, transitioning to high-speed Fernet (AES) symmetric encryption for real-time messaging.
- **👥 Live Online Users List**: Real-time tracking of active users in your current chat room.
- **📁 Secure Chunked File Transfer**: Share files up to 50MB. Files are broken into 64KB chunks, Base64 encoded, encrypted, and reassembled on the server before being saved locally.
- **🖼️ Image Sharing & Profiles**: Set custom profile pictures and share images directly in the chat with inline rendering.
- **🏠 Room Management**: Create open or password-protected chat rooms dynamically.
- **🗄️ Database Integration**: Persistent storage of user credentials and chat history using `SQLite3`.

---

## 🏗️ Architecture & Security

DarkLine operates on a standard **Client-Server architecture** using standard TCP sockets. 

1. **Handshake & Key Exchange**: When a client connects, the server sends its public RSA key. The client generates a random Fernet key, encrypts it with the server's public RSA key, and sends it back. All subsequent communication is encrypted with this Fernet key.
2. **Authentication**: Credentials are cross-checked against a local SQLite database (`darkline.db`). Passwords are NEVER stored in plaintext (secured via `bcrypt` salting/hashing).
3. **Event-Driven Protocol**: All actions (text, file chunks, room syncs, presence updates) are packaged into structured JSON objects, encrypted, and broadcasted to the appropriate sockets.

---

## ⚙️ Installation

### Prerequisites
Make sure you have **Python 3.8+** installed on your system.

### 1. Clone the Repository
```bash
git clone https://github.com/MRThugh/DarkLine-Messenger.git
cd DarkLine-Messenger
```
### 2. Install Dependencies
Install the required Python packages using `pip`:
bash
pip install customtkinter cryptography Pillow bcrypt

---

## 🚀 Usage

You can run the application directly via Python.

```bash
python main.py
```

### Hosting a Server
1. Launch the app.
2. Under **Connection**, specify the port (default `5555`).
3. Click **🖥️ Host Server**.
4. The server will initialize, generate encryption keys, and set up the SQLite database. Register an account and log in.

### Connecting as a Client
1. Launch the app on another machine (or the same machine for testing).
2. Enter the **Host IP** (the IP address of the machine running the server) and **Port**.
3. Click **🔗 Connect**.
4. Register or log in through the Security Gateway to start chatting!

*(Note: Shared files will be saved in the `./received_files/<room_name>/` directory on the server machine).*

---

## 💬 Discussion & Philosophy

DarkLine Messenger was built with the belief that **privacy should be the default**. In an era where cloud servers process every keystroke, DarkLine brings the power back to local networks. 

By remaining **Open Source**, the community can audit the encryption flow, verify the security measures, and contribute to the protocol. The choice of Python allows for rapid development and easy cross-platform compatibility (Windows, macOS, Linux), while `CustomTkinter` proves that desktop applications don't need web frameworks like Electron to look modern and beautiful.

Contributions, forks, and pull requests are highly encouraged!

---

## 📜 License

This project is open-source and available under the **MIT License**. 
You are free to use, modify, and distribute this software as per the terms of the license.

text
MIT License

Copyright (c) 2026 Ali Kamrani (MR.Thugh)

Permission is hereby granted, free of charge, to any person obtaining a copy
...
*(See the [LICENSE](LICENSE) file for the full text).*

---

## 👨‍💻 Author

**Ali Kamrani / MR.Thugh**
- GitHub: [@MRThugh](https://github.com/MRThugh)
- Project Link: [https://github.com/MRThugh/DarkLine-Messenger](https://github.com/MRThugh/DarkLine-Messenger)

---
*If you like this project, please consider giving it a ⭐ on GitHub!*
