<div align="center">
  
  <br>
  <h1>⚡ DarkLine Messenger</h1>
  <p>
    <b>A modern, secure, and blazing-fast local network messenger built with Python.</b>
  </p>
  
  [![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
  [![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-darkgreen.svg?style=for-the-badge)](https://github.com/TomSchimansky/CustomTkinter)
  [![Security](https://img.shields.io/badge/Encryption-AES--128-red.svg?style=for-the-badge)](https://cryptography.io/en/latest/fernet/)
  [![Developer](https://img.shields.io/badge/Developer-MRThugh-purple.svg?style=for-the-badge&logo=github)](https://github.com/MRThugh)

  *Crafted with passion by [MRThugh](https://github.com/MRThugh).*
  
</div>

---

## 📖 About The Project

**DarkLine Messenger** is a fully-featured, decentralized LAN (Local Area Network) chat application. Designed with a sleek, modern, dark-themed UI using `customtkinter`, it allows users on the same network to host servers, connect as clients, create private chat rooms, share media, and communicate securely using real-time AES encryption.

Whether you're looking for a private communication tool for your office/home network or an excellent example of Python socket programming and GUI design, DarkLine is built to impress.

## ✨ God-Tier Features

*   🛡️ **End-to-End Encryption:** All messages and images are encrypted locally before transmission using AES (Advanced Encryption Standard via `cryptography.fernet`).
*   🎨 **Modern Dark UI:** Beautiful, responsive, and intuitive graphical interface powered by `CustomTkinter` with a custom "blue" color theme.
*   🏠 **Dynamic Chat Rooms:** Create custom chat channels on the fly. You can even lock rooms with **passwords** for private group conversations!
*   🖼️ **Media Sharing & Profiles:** 
    *   Set custom Profile Pictures (resized automatically and transmitted via Base64).
    *   Send, receive, and download image messages directly within the chat.
*   🖥️ **Built-in Server Hosting:** No third-party servers required. Host a server directly from the client with one click.
*   📡 **Smart Networking:** Auto-detects your local IP address and displays real-time connection status and active user counts.
*   🕒 **Live Dashboard:** Integrated real-time clock, date display, and system event logging (connection drops, new rooms, etc.).

---

## 📸 Screenshots

| Login & Server Setup | Chat Room & Image Sharing | Private Rooms |
| :---: | :---: | :---: |
| <img src="https://via.placeholder.com/300x200.png?text=Login+Screen" width="300"/> | <img src="https://via.placeholder.com/300x200.png?text=Chat+Interface" width="300"/> | <img src="https://via.placeholder.com/300x200.png?text=Password+Protected" width="300"/> |

---

## 🚀 Getting Started

### Prerequisites

You need Python 3.8 or higher installed on your machine. You will also need to install the required dependencies.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MRThugh/DarkLine-Messenger.git
   cd DarkLine-Messenger
   ```

2. **Install required packages:**
   ```bash
   pip install customtkinter Pillow cryptography
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

---

## 🕹️ How to Use

### Hosting a Server (Host)
1. Launch the app.
2. Enter your desired **Username** and click `📷 Set Profile Picture` (optional).
3. The app will show your **Local IP** on the sidebar.
4. Enter a **Port** (default `5555`) and click **🖥️ Host Server**.
5. You are now hosting the chat! Tell your friends your Local IP and Port.

### Connecting to a Server (Client)
1. Launch the app on another computer on the same network.
2. Enter your **Username** and set a **Profile Picture**.
3. Under Connection, enter the **Host IP** (the IP of the person hosting) and the **Port**.
4. Click **🔗 Connect**.
5. Start chatting in the "General" room, or create your own locked rooms!

---

## 🧠 Under the Hood (Architecture)

*   **Networking:** Pure Python `socket` library utilizing TCP streams (`SOCK_STREAM`).
*   **Concurrency:** Utilizes Python `threading` to keep the UI responsive while simultaneously listening for incoming network packets.
*   **Data Serialization:** Payloads (text, timestamps, Base64 images) are packaged into `JSON` formats before transmission.
*   **Security:** `Fernet` symmetric encryption ensures that any packet intercepted on the network is completely unreadable without the secret key.

---

## 🛠️ Future Roadmap

- [ ] Add Emojis / Sticker support.
- [ ] Implement file sharing (PDFs, ZIPs).
- [ ] Add a global configuration file (`config.json`) for custom encryption keys.
- [ ] Notification sounds for new messages.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/MRThugh/DarkLine-Messenger/issues).
