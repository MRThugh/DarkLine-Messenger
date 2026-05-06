import customtkinter as ctk
import socket
import threading
import json
import base64
from PIL import Image, ImageTk
from tkinter import filedialog
import io
import time
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import uuid
import os
import sqlite3
import bcrypt
import math

class DatabaseManager:
    def __init__(self, db_name="darkline.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (username TEXT PRIMARY KEY, password_hash BLOB)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, 
                      username TEXT, msg_type TEXT, content TEXT, 
                      timestamp TEXT, profile_image TEXT)''')
        self.conn.commit()

    def register_user(self, username, password):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        if c.fetchone(): 
            return False, "Username already exists."
        pwd_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pwd_hash))
        self.conn.commit()
        return True, "Registered successfully. You can now log in."

    def verify_user(self, username, password):
        c = self.conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if row and bcrypt.checkpw(password.encode('utf-8'), row[0]):
            return True, "Login successful."
        return False, "Invalid username or password."

    def save_message(self, room, username, msg_type, content, timestamp, profile_image):
        c = self.conn.cursor()
        c.execute("INSERT INTO messages (room, username, msg_type, content, timestamp, profile_image) VALUES (?, ?, ?, ?, ?, ?)",
                  (room, username, msg_type, content, timestamp, profile_image))
        self.conn.commit()

    def get_history(self, room, limit=50):
        c = self.conn.cursor()
        c.execute("SELECT username, msg_type, content, timestamp, profile_image FROM messages WHERE room=? ORDER BY id DESC LIMIT ?", (room, limit))
        rows = c.fetchall()
        return list(reversed(rows))


class DarklineMessenger:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Darkline Messenger")
        self.window.geometry("1150x650")
        
        self.fernet_key = None
        self.cipher_suite = None
        self.client_ciphers = {} 
        self.client_usernames = {} 
        self.authenticated = False
        
        self.db = None 

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.server_socket = None
        self.client_socket = None
        self.is_server = False
        self.connected = False
        self.username = "User"
        self.profile_image = None
        
        self.client_rooms = {} 
        self.chat_rooms = {"General": {"password": None, "clients": []}}
        self.current_room = "General"
        
        # Server-side pending files: file_id -> { room, file_id, filename, chunks_received, total_chunks, data_map, last_update }
        self.pending_files = {}

        self.bg_color = "#1e1e2e"
        self.sidebar_color = "#181825"
        self.message_bg = "#313244"
        self.accent_color = "#89b4fa"
        
        self.setup_ui()
        self.update_clock()
        
        # File transfer constants
        self.CHUNK_SIZE = 64 * 1024
        self.MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB DoS protection

        # Periodically clean up stale pending file transfers
        self.window.after(30000, self.cleanup_stale_files)

    def setup_ui(self):
        self.window.configure(fg_color=self.bg_color)
        
        self.sidebar = ctk.CTkFrame(self.window, width=280, fg_color=self.sidebar_color, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)
        
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color=self.sidebar_color, height=80)
        logo_frame.pack(fill="x", padx=15, pady=15)
        
        logo_label = ctk.CTkLabel(logo_frame, text="⚡ DARKLINE", font=("Arial", 24, "bold"), text_color=self.accent_color)
        logo_label.pack()
        
        subtitle = ctk.CTkLabel(logo_frame, text="Local Messenger", font=("Arial", 11), text_color="#6c7086")
        subtitle.pack()
        
        self.clock_label = ctk.CTkLabel(self.sidebar, text="", font=("Arial", 12), text_color="#a6e3a1")
        self.clock_label.pack(pady=5)
        
        profile_frame = ctk.CTkFrame(self.sidebar, fg_color=self.sidebar_color)
        profile_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(profile_frame, text="Profile:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,5))
        
        self.profile_btn = ctk.CTkButton(profile_frame, text="📷 Set Profile Picture", command=self.set_profile_image, fg_color=self.message_bg, hover_color="#45475a", height=35)
        self.profile_btn.pack(fill="x", pady=(0,10))
        
        ctk.CTkLabel(profile_frame, text="Username:", font=("Arial", 12)).pack(anchor="w", pady=(0,5))
        self.username_label_display = ctk.CTkLabel(profile_frame, text="Not Authenticated", font=("Arial", 12, "italic"), text_color="#f38ba8")
        self.username_label_display.pack(fill="x", pady=(0,10))
        
        conn_frame = ctk.CTkFrame(self.sidebar, fg_color=self.sidebar_color)
        conn_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(conn_frame, text="Connection:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,5))
        
        ctk.CTkLabel(conn_frame, text="Host IP:", font=("Arial", 11)).pack(anchor="w", pady=(0,3))
        self.ip_entry = ctk.CTkEntry(conn_frame, placeholder_text="192.168.1.x")
        self.ip_entry.pack(fill="x", pady=(0,8))
        
        ctk.CTkLabel(conn_frame, text="Port:", font=("Arial", 11)).pack(anchor="w", pady=(0,3))
        self.port_entry = ctk.CTkEntry(conn_frame, placeholder_text="5555")
        self.port_entry.insert(0, "5555")
        self.port_entry.pack(fill="x", pady=(0,10))
        
        self.host_btn = ctk.CTkButton(conn_frame, text="🖥️ Host Server", command=self.start_server, fg_color=self.accent_color, hover_color="#74c7ec")
        self.host_btn.pack(fill="x", pady=3)
        
        self.connect_btn = ctk.CTkButton(conn_frame, text="🔗 Connect", command=self.connect_to_server, fg_color="#a6e3a1", hover_color="#94e2d5", text_color="#1e1e2e")
        self.connect_btn.pack(fill="x", pady=3)
        
        self.network_ip_label = ctk.CTkLabel(self.sidebar, text=f"Your IP: {self.get_local_ip()}", font=("Arial", 10), text_color="#f9e2af")
        self.network_ip_label.pack(pady=5)
        
        rooms_frame = ctk.CTkFrame(self.sidebar, fg_color=self.sidebar_color)
        rooms_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(rooms_frame, text="Chat Rooms:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,5))
        
        self.create_room_btn = ctk.CTkButton(rooms_frame, text="➕ Create Room", command=self.create_chat_room, fg_color=self.message_bg, hover_color="#45475a", height=30)
        self.create_room_btn.pack(fill="x", pady=(0,5))
        self.create_room_btn.configure(state="disabled")
        
        self.rooms_list_frame = ctk.CTkScrollableFrame(rooms_frame, fg_color=self.sidebar_color, height=100)
        self.rooms_list_frame.pack(fill="x", pady=(0,5))
        self.update_rooms_list()
        
        self.status_label = ctk.CTkLabel(self.sidebar, text="● Disconnected", font=("Arial", 11), text_color="#f38ba8")
        self.status_label.pack(side="bottom", pady=15)
        
        # Chat container
        chat_container = ctk.CTkFrame(self.window, fg_color=self.bg_color)
        chat_container.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        
        header = ctk.CTkFrame(chat_container, height=60, fg_color=self.sidebar_color, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        self.room_label = ctk.CTkLabel(header, text=f"💬 {self.current_room}", font=("Arial", 18, "bold"), text_color=self.accent_color)
        self.room_label.pack(side="left", padx=20, pady=15)
        
        # Splitting Chat and Users List
        main_chat_area = ctk.CTkFrame(chat_container, fg_color=self.bg_color)
        main_chat_area.pack(fill="both", expand=True, padx=0, pady=0)

        self.messages_frame = ctk.CTkScrollableFrame(main_chat_area, fg_color=self.bg_color, corner_radius=0)
        self.messages_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.users_frame_container = ctk.CTkFrame(main_chat_area, width=150, fg_color=self.sidebar_color, corner_radius=0)
        self.users_frame_container.pack(side="right", fill="y", padx=0, pady=0)
        self.users_frame_container.pack_propagate(False)

        ctk.CTkLabel(self.users_frame_container, text="👥 Online", font=("Arial", 12, "bold"), text_color=self.accent_color).pack(pady=10)
        self.users_scrollable = ctk.CTkScrollableFrame(self.users_frame_container, fg_color=self.sidebar_color)
        self.users_scrollable.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Input Section
        input_container = ctk.CTkFrame(chat_container, fg_color=self.sidebar_color, height=80, corner_radius=0)
        input_container.pack(fill="x", padx=0, pady=0, side="bottom")
        input_container.pack_propagate(False)
        
        input_frame = ctk.CTkFrame(input_container, fg_color=self.sidebar_color)
        input_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.message_entry = ctk.CTkEntry(input_frame, placeholder_text="Type a message...", height=40, font=("Arial", 13))
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        self.file_btn = ctk.CTkButton(input_frame, text="📎", width=40, height=40, command=self.send_file, fg_color=self.message_bg, hover_color="#45475a")
        self.file_btn.pack(side="left", padx=(0,5))

        self.image_btn = ctk.CTkButton(input_frame, text="📷", width=40, height=40, command=self.send_image, fg_color=self.message_bg, hover_color="#45475a")
        self.image_btn.pack(side="left", padx=(0,5))
        
        self.send_btn = ctk.CTkButton(input_frame, text="Send", width=80, height=40, command=self.send_message, fg_color=self.accent_color, hover_color="#74c7ec")
        self.send_btn.pack(side="left")

        # Disable main controls until authenticated
        self.message_entry.configure(state="disabled")
        self.file_btn.configure(state="disabled")
        self.image_btn.configure(state="disabled")
        self.send_btn.configure(state="disabled")
    
    def update_clock(self):
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        self.clock_label.configure(text=f"🕐 {time_str}\n📅 {date_str}")
        self.window.after(1000, self.update_clock)
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def enable_chat_controls(self):
        self.create_room_btn.configure(state="normal")
        self.message_entry.configure(state="normal")
        self.file_btn.configure(state="normal")
        self.image_btn.configure(state="normal")
        self.send_btn.configure(state="normal")
    
    def set_profile_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if not file_path: return
        try:
            with Image.open(file_path) as img:
                img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                self.profile_image = base64.b64encode(buffer.getvalue()).decode()
                self.add_system_message("Profile picture set successfully")
        except Exception as e:
            self.add_system_message(f"Error setting profile picture: {str(e)}")
    
    def clear_messages(self):
        for widget in self.messages_frame.winfo_children():
            widget.destroy()

    def update_users_list(self, users):
        for widget in self.users_scrollable.winfo_children():
            widget.destroy()
        for u in users:
            ctk.CTkLabel(self.users_scrollable, text=f"• {u}", font=("Arial", 12), text_color="#cdd6f4").pack(anchor="w", pady=2)

    def create_chat_room(self):
        if not self.authenticated and not self.is_server:
            self.add_system_message("Please log in first.")
            return

        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Create Chat Room")
        dialog.geometry("350x250")
        dialog.configure(fg_color=self.bg_color)
        
        ctk.CTkLabel(dialog, text="Room Name:", font=("Arial", 12)).pack(pady=(20,5))
        room_name_entry = ctk.CTkEntry(dialog, width=250)
        room_name_entry.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Password (optional):", font=("Arial", 12)).pack(pady=(10,5))
        password_entry = ctk.CTkEntry(dialog, width=250, show="*")
        password_entry.pack(pady=5)
        
        def create():
            room_name = room_name_entry.get().strip()
            password = password_entry.get().strip() or None
            if not room_name: return
            if room_name in self.chat_rooms:
                self.add_system_message(f"Room '{room_name}' already exists")
                dialog.destroy()
                return
            
            self.chat_rooms[room_name] = {"password": password, "clients": []}
            self.update_rooms_list()
            self.add_system_message(f"Room '{room_name}' created")
            
            if self.connected:
                sync_data = {
                    'type': 'room_sync',
                    'room_name': room_name,
                    'password': password,
                    'msg_id': str(uuid.uuid4())
                }
                self.broadcast_message(sync_data)
                
            dialog.destroy()
        
        ctk.CTkButton(dialog, text="Create", command=create, fg_color=self.accent_color).pack(pady=20)
    
    def update_rooms_list(self):
        for widget in self.rooms_list_frame.winfo_children():
            widget.destroy()
        
        for room_name in self.chat_rooms.keys():
            has_password = self.chat_rooms[room_name]["password"] is not None
            lock_icon = "🔒" if has_password else "🔓"
            
            room_btn = ctk.CTkButton(
                self.rooms_list_frame,
                text=f"{lock_icon} {room_name}",
                command=lambda r=room_name: self.join_room(r),
                fg_color=self.accent_color if room_name == self.current_room else self.message_bg,
                hover_color="#45475a",
                height=30,
                anchor="w"
            )
            # Disable unauth join click
            if not self.authenticated:
                room_btn.configure(state="disabled")
            room_btn.pack(fill="x", pady=2)
    
    def join_room(self, room_name):
        if not self.authenticated and not self.is_server:
            self.add_system_message("Please log in first.")
            return

        room = self.chat_rooms.get(room_name)
        if not room: return
        
        def success_join():
            if self.connected:
                self.broadcast_message({'type': 'user_left', 'username': self.username, 'room': self.current_room})

            self.current_room = room_name
            self.room_label.configure(text=f"💬 {self.current_room}")
            self.update_rooms_list()
            self.clear_messages()
            self.update_users_list([]) # Clear users till updated
            self.add_system_message(f"Loading history for {self.current_room}...")
            
            if self.connected:
                self.broadcast_message({'type': 'join_room', 'room': self.current_room})
                self.broadcast_message({'type': 'user_joined', 'username': self.username, 'room': self.current_room})
            elif self.is_server:
                history = self.db.get_history(self.current_room)
                for h in history:
                    u, m_type, content, ts, p_img = h
                    is_own = (u == self.username)
                    if m_type == 'text':
                        self.add_message(u, content, is_own, p_img, ts)
                    elif m_type == 'image':
                        self.add_image_message(u, content, is_own, p_img, ts)
                self.add_system_message(f"Joined {self.current_room}")
                self.broadcast_users_list(self.current_room)
                
        if room["password"]:
            dialog = ctk.CTkToplevel(self.window)
            dialog.title("Enter Password")
            dialog.geometry("300x150")
            dialog.configure(fg_color=self.bg_color)
            
            ctk.CTkLabel(dialog, text="Password:", font=("Arial", 12)).pack(pady=(20,5))
            password_entry = ctk.CTkEntry(dialog, width=200, show="*")
            password_entry.pack(pady=5)
            
            def check_password():
                if password_entry.get() == room["password"]:
                    dialog.destroy()
                    success_join()
                else:
                    self.add_system_message("Incorrect password")
                    dialog.destroy()
            
            ctk.CTkButton(dialog, text="Join", command=check_password, fg_color=self.accent_color).pack(pady=10)
        else:
            success_join()
        
    def show_auth_dialog(self):
        self.auth_dialog = ctk.CTkToplevel(self.window)
        self.auth_dialog.title("Authentication")
        self.auth_dialog.geometry("350x380")
        self.auth_dialog.configure(fg_color=self.bg_color)
        self.auth_dialog.grab_set()
        
        ctk.CTkLabel(self.auth_dialog, text="🔒 Security Gateway", font=("Arial", 18, "bold"), text_color=self.accent_color).pack(pady=(20, 15))
        
        ctk.CTkLabel(self.auth_dialog, text="Username:", font=("Arial", 12)).pack(pady=(10,5))
        user_entry = ctk.CTkEntry(self.auth_dialog, width=250)
        user_entry.pack(pady=5)
        
        ctk.CTkLabel(self.auth_dialog, text="Password:", font=("Arial", 12)).pack(pady=(10,5))
        pass_entry = ctk.CTkEntry(self.auth_dialog, width=250, show="*")
        pass_entry.pack(pady=5)

        self.auth_error_label = ctk.CTkLabel(self.auth_dialog, text="", font=("Arial", 11), text_color="#f38ba8")
        self.auth_error_label.pack(pady=(5,5))

        def attempt_login():
            u = user_entry.get().strip()
            p = pass_entry.get().strip()
            if not u or not p:
                self.auth_error_label.configure(text="Please fill all fields.", text_color="#f38ba8")
                return
            
            if self.is_server:
                success, msg = self.db.verify_user(u, p)
                if success:
                    self.username = u
                    self.authenticated = True
                    self.username_label_display.configure(text=self.username, text_color="#a6e3a1")
                    self.auth_dialog.destroy()
                    self.enable_chat_controls()
                    self.join_room("General")
                else:
                    self.auth_error_label.configure(text=msg, text_color="#f38ba8")
            else:
                self.username = u 
                self.broadcast_message({'type': 'login', 'username': u, 'password': p})

        def attempt_register():
            u = user_entry.get().strip()
            p = pass_entry.get().strip()
            if not u or not p:
                self.auth_error_label.configure(text="Please fill all fields.", text_color="#f38ba8")
                return

            if self.is_server:
                success, msg = self.db.register_user(u, p)
                color = "#a6e3a1" if success else "#f38ba8"
                self.auth_error_label.configure(text=msg, text_color=color)
            else:
                self.broadcast_message({'type': 'register', 'username': u, 'password': p})

        ctk.CTkButton(self.auth_dialog, text="Login", command=attempt_login, fg_color=self.accent_color, width=250).pack(pady=(10,5))
        ctk.CTkButton(self.auth_dialog, text="Register", command=attempt_register, fg_color=self.message_bg, hover_color="#45475a", width=250).pack(pady=(5,20))

    def start_server(self):
        if self.connected: return
            
        port = int(self.port_entry.get() or 5555)
        
        try:
            self.db = DatabaseManager()
            self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.public_key = self.private_key.public_key()
            self.public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            self.fernet_key = Fernet.generate_key()
            self.cipher_suite = Fernet(self.fernet_key)

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)
            
            self.is_server = True
            self.connected = True
            self.client_rooms.clear()
            self.client_ciphers.clear()
            self.client_usernames.clear()
            self.status_label.configure(text="● Waiting for connection...", text_color="#f9e2af")
            self.add_system_message(f"Server started on {self.get_local_ip()}:{port}")
            
            threading.Thread(target=self.accept_connections, daemon=True).start()
            self.show_auth_dialog()

        except Exception as e:
            self.add_system_message(f"Error: {str(e)}")
    
    def accept_connections(self):
        while self.connected:
            try:
                client_socket, addr = self.server_socket.accept()
                b64_pub = base64.b64encode(self.public_pem)
                client_socket.send(b'RSA:' + b64_pub + b'\n')
                
                self.client_rooms[client_socket] = "AuthPending"
                self.window.after(0, lambda a=addr: self.status_label.configure(text=f"● Connected ({len(self.client_rooms)} users)", text_color="#a6e3a1"))
                self.window.after(0, lambda a=addr: self.add_system_message(f"Connection from {a[0]} (Authenticating...)"))
                
                threading.Thread(target=self.receive_messages, args=(client_socket,), daemon=True).start()
            except Exception:
                break
    
    def connect_to_server(self):
        if self.connected: return
            
        host = self.ip_entry.get()
        port = int(self.port_entry.get() or 5555)
        if not host:
            self.add_system_message("Please enter host IP")
            return
            
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            
            self.connected = True
            self.is_server = False
            self.window.after(0, lambda: self.status_label.configure(text="● Connected (Handshake...)", text_color="#f9e2af"))
            
            threading.Thread(target=self.receive_messages, args=(self.client_socket,), daemon=True).start()
        except Exception as e:
            self.add_system_message(f"Connection failed: {str(e)}")
    
    def broadcast_users_list(self, room):
        # Server gathers authenticated users in the requested room
        if not self.is_server: return
        users_in_room = [self.username] if (self.authenticated and self.current_room == room) else []
        for s, r in self.client_rooms.items():
            if r == room and s in self.client_usernames:
                users_in_room.append(self.client_usernames[s])
                
        list_data = {'type': 'users_list', 'room': room, 'users': users_in_room}
        self.broadcast_message(list_data)
        if self.current_room == room:
            self.window.after(0, lambda u=users_in_room: self.update_users_list(u))

    def send_message(self):
        if not self.connected or not self.cipher_suite or not self.authenticated:
            return
        message = self.message_entry.get().strip()
        if not message: return
            
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            data = {
                'type': 'text',
                'msg_id': str(uuid.uuid4()),
                'username': self.username,
                'content': message,
                'timestamp': timestamp,
                'profile_image': self.profile_image,
                'room': self.current_room
            }
            if self.is_server:
                self.db.save_message(self.current_room, self.username, 'text', message, timestamp, self.profile_image)

            self.broadcast_message(data)
            self.add_message(self.username, message, is_own=True, profile_img=self.profile_image, timestamp=timestamp)
            self.message_entry.delete(0, 'end')
        except Exception as e:
            self.add_system_message(f"Send error: {str(e)}")

    def send_file(self):
        if not self.connected or not self.cipher_suite or not self.authenticated:
            return
        file_path = filedialog.askopenfilename()
        if not file_path: return

        filesize = os.path.getsize(file_path)
        if filesize > self.MAX_FILE_SIZE:
            self.add_system_message(f"File too large. Max size is {self.MAX_FILE_SIZE//(1024*1024)}MB.")
            return

        def process_and_send():
            try:
                filename = os.path.basename(file_path)
                file_id = str(uuid.uuid4())
                total_chunks = math.ceil(filesize / self.CHUNK_SIZE)

                offer = {
                    'type': 'file_offer',
                    'room': self.current_room,
                    'file_id': file_id,
                    'filename': filename,
                    'filesize': filesize,
                    'total_chunks': total_chunks,
                    'chunk_size': self.CHUNK_SIZE
                }
                self.broadcast_message(offer)

                with open(file_path, "rb") as f:
                    for i in range(total_chunks):
                        chunk_data = f.read(self.CHUNK_SIZE)
                        data_b64 = base64.b64encode(chunk_data).decode('utf-8')
                        chunk_msg = {
                            'type': 'file_chunk',
                            'room': self.current_room,
                            'file_id': file_id,
                            'chunk_index': i,
                            'data_b64': data_b64
                        }
                        self.broadcast_message(chunk_msg)
                        self.window.after(0, lambda idx=i: self.add_system_message(f"Uploading file... {int((idx/total_chunks)*100)}%"))
                        time.sleep(0.01) # Small sleep to prevent swamping socket

                complete_msg = {'type': 'file_complete', 'room': self.current_room, 'file_id': file_id}
                self.broadcast_message(complete_msg)
                self.window.after(0, lambda: self.add_system_message(f"Upload complete: {filename}"))

            except Exception as e:
                self.window.after(0, lambda: self.add_system_message(f"File transfer error: {str(e)}"))

        threading.Thread(target=process_and_send, daemon=True).start()
    
    def send_image(self):
        if not self.connected or not self.cipher_suite or not self.authenticated:
            return
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if not file_path: return
        if os.path.getsize(file_path) > 5 * 1024 * 1024:
            self.add_system_message("Image is too large! Please select an image under 5MB.")
            return

        try:
            with Image.open(file_path) as img:
                max_size = (400, 400)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue()).decode()
                
            timestamp = datetime.now().strftime('%H:%M:%S')
            data = {
                'type': 'image',
                'msg_id': str(uuid.uuid4()),
                'username': self.username,
                'content': img_str,
                'timestamp': timestamp,
                'profile_image': self.profile_image,
                'room': self.current_room
            }
            if self.is_server:
                self.db.save_message(self.current_room, self.username, 'image', img_str, timestamp, self.profile_image)

            self.broadcast_message(data)
            self.add_image_message(self.username, img_str, is_own=True, profile_img=self.profile_image, timestamp=timestamp)
        except Exception as e:
            self.add_system_message(f"Image send error: {str(e)}")
    
    def broadcast_message(self, data):
        message_json = json.dumps(data).encode('utf-8')
        if self.is_server:
            target_room = data.get('room')
            # Only broadcast normal messages to authenticated users in the same room
            for client, room in list(self.client_rooms.items()):
                if data.get('type') in ['room_sync', 'auth_result'] or (room == target_room and client in self.client_usernames):
                    try:
                        target_cipher = self.client_ciphers.get(client)
                        if target_cipher:
                            payload = target_cipher.encrypt(message_json) + b'\n'
                            client.send(payload)
                    except:
                        self.remove_client(client)
        else:
            if not self.cipher_suite: return
            payload = self.cipher_suite.encrypt(message_json) + b'\n'
            try:
                self.client_socket.send(payload)
            except Exception as e:
                self.window.after(0, lambda: self.add_system_message(f"Failed to send to server: {str(e)}"))
                self.handle_disconnect()
    
    def receive_messages(self, sock):
        buffer = b""
        while self.connected:
            try:
                data = sock.recv(8192)
                if not data: break
                    
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if not line: continue
                    
                    if not self.is_server and line.startswith(b'RSA:'):
                        server_public_pem = base64.b64decode(line[4:])
                        server_public_key = serialization.load_pem_public_key(server_public_pem)
                        
                        self.fernet_key = Fernet.generate_key()
                        self.cipher_suite = Fernet(self.fernet_key)
                        
                        encrypted_fernet = server_public_key.encrypt(
                            self.fernet_key,
                            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                        )
                        sock.send(b'FERNET:' + base64.b64encode(encrypted_fernet) + b'\n')
                        self.window.after(0, lambda: self.status_label.configure(text="● Connected (Secured)", text_color="#a6e3a1"))
                        self.window.after(0, self.show_auth_dialog)
                        continue
                        
                    if self.is_server and line.startswith(b'FERNET:'):
                        encrypted_fernet = base64.b64decode(line[7:])
                        decrypted_fernet = self.private_key.decrypt(
                            encrypted_fernet,
                            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                        )
                        self.client_ciphers[sock] = Fernet(decrypted_fernet)
                        continue

                    cipher = self.client_ciphers.get(sock) if self.is_server else self.cipher_suite
                    if not cipher: continue

                    try:
                        decrypted_data = cipher.decrypt(line).decode('utf-8')
                        message_data = json.loads(decrypted_data)
                    except Exception:
                        continue 
                    
                    msg_type = message_data.get('type')
                    room = message_data.get('room')
                    
                    if self.is_server:
                        if msg_type == 'register':
                            u = message_data.get('username')
                            p = message_data.get('password')
                            success, msg = self.db.register_user(u, p)
                            result_data = {'type': 'auth_result', 'success': success, 'message': msg, 'action': 'register'}
                            sock.send(cipher.encrypt(json.dumps(result_data).encode('utf-8')) + b'\n')
                            continue

                        if msg_type == 'login':
                            u = message_data.get('username')
                            p = message_data.get('password')
                            success, msg = self.db.verify_user(u, p)
                            if success:
                                self.client_usernames[sock] = u
                                self.client_rooms[sock] = "General"
                                result_data = {'type': 'auth_result', 'success': True, 'message': msg, 'action': 'login', 'username': u}
                                sock.send(cipher.encrypt(json.dumps(result_data).encode('utf-8')) + b'\n')
                                for r_name, r_data in self.chat_rooms.items():
                                    if r_name != "General":
                                        sync_data = {'type': 'room_sync', 'room_name': r_name, 'password': r_data['password']}
                                        sock.send(cipher.encrypt(json.dumps(sync_data).encode('utf-8')) + b'\n')
                                self.broadcast_users_list("General")
                            else:
                                result_data = {'type': 'auth_result', 'success': False, 'message': msg, 'action': 'login'}
                                sock.send(cipher.encrypt(json.dumps(result_data).encode('utf-8')) + b'\n')
                            continue

                        if sock not in self.client_usernames:
                            continue

                        if msg_type in ['text', 'image']:
                            u = self.client_usernames.get(sock)
                            ts = message_data.get('timestamp', '')
                            p_img = message_data.get('profile_image')
                            content = message_data.get('content', '')
                            self.db.save_message(room, u, msg_type, content, ts, p_img)

                        if msg_type == 'join_room':
                            old_room = self.client_rooms.get(sock)
                            self.client_rooms[sock] = room
                            history = self.db.get_history(room)
                            hist_data = {'type': 'history', 'room': room, 'messages': history}
                            sock.send(cipher.encrypt(json.dumps(hist_data).encode('utf-8')) + b'\n')
                            
                            self.broadcast_users_list(old_room)
                            self.broadcast_users_list(room)
                            continue

                        # ---- Server File Transfer Handling ----
                        if msg_type == 'file_offer':
                            filesize = message_data.get('filesize', 0)
                            if filesize <= self.MAX_FILE_SIZE:
                                fid = message_data.get('file_id')
                                self.pending_files[fid] = {
                                    'room': room,
                                    'filename': os.path.basename(message_data.get('filename')),
                                    'total_chunks': message_data.get('total_chunks'),
                                    'chunks_received': 0,
                                    'data_map': {},
                                    'last_update': time.time()
                                }
                            continue

                        if msg_type == 'file_chunk':
                            fid = message_data.get('file_id')
                            if fid in self.pending_files:
                                pf = self.pending_files[fid]
                                idx = message_data.get('chunk_index')
                                pf['data_map'][idx] = base64.b64decode(message_data.get('data_b64', ''))
                                pf['chunks_received'] += 1
                                pf['last_update'] = time.time()
                            continue

                        if msg_type == 'file_complete':
                            fid = message_data.get('file_id')
                            if fid in self.pending_files:
                                pf = self.pending_files[fid]
                                if pf['chunks_received'] == pf['total_chunks']:
                                    save_dir = os.path.join("./received_files", pf['room'])
                                    os.makedirs(save_dir, exist_ok=True)
                                    safe_name = "".join(c for c in pf['filename'] if c.isalnum() or c in " ._-")
                                    save_path = os.path.join(save_dir, safe_name)
                                    
                                    with open(save_path, "wb") as f:
                                        for i in range(pf['total_chunks']):
                                            f.write(pf['data_map'].get(i, b''))
                                            
                                    sender_u = self.client_usernames.get(sock)
                                    ts = datetime.now().strftime('%H:%M:%S')
                                    notice = f"Shared file: '{safe_name}' (Saved locally on server)"
                                    
                                    notice_msg = {
                                        'type': 'text',
                                        'msg_id': str(uuid.uuid4()),
                                        'username': sender_u,
                                        'content': notice,
                                        'timestamp': ts,
                                        'profile_image': None,
                                        'room': room
                                    }
                                    self.db.save_message(room, sender_u, 'text', notice, ts, None)
                                    self.broadcast_message(notice_msg)
                                    
                                    if room == self.current_room:
                                        self.window.after(0, self.add_message, sender_u, notice, (sender_u == self.username), None, ts)
                                        
                                del self.pending_files[fid]
                            continue

                    if not self.is_server:
                        if msg_type == 'auth_result':
                            action = message_data.get('action')
                            success = message_data.get('success')
                            msg = message_data.get('message')
                            color = "#a6e3a1" if success else "#f38ba8"

                            if hasattr(self, 'auth_error_label'):
                                self.window.after(0, lambda c=color, m=msg: self.auth_error_label.configure(text=m, text_color=c))

                            if success and action == 'login':
                                self.authenticated = True
                                self.username = message_data.get('username')
                                self.window.after(0, lambda u=self.username: self.username_label_display.configure(text=u, text_color="#a6e3a1"))
                                self.window.after(0, self.enable_chat_controls)
                                self.window.after(0, self.auth_dialog.destroy)
                                self.window.after(0, lambda: self.join_room("General"))
                                self.window.after(0, self.update_rooms_list)
                            continue
                        
                        if msg_type == 'history':
                            if room == self.current_room:
                                messages = message_data.get('messages', [])
                                self.window.after(0, self.clear_messages)
                                for m in messages:
                                    u, m_type, content, ts, p_img = m
                                    is_own = (u == self.username)
                                    if m_type == 'text':
                                        self.window.after(0, self.add_message, u, content, is_own, p_img, ts)
                                    elif m_type == 'image':
                                        self.window.after(0, self.add_image_message, u, content, is_own, p_img, ts)
                                self.window.after(0, lambda: self.add_system_message(f"Loaded {len(messages)} past messages"))
                            continue
                            
                        if msg_type == 'users_list' and room == self.current_room:
                            self.window.after(0, lambda u=message_data.get('users', []): self.update_users_list(u))
                            continue

                    if msg_type == 'room_sync':
                        r_name = message_data.get('room_name')
                        r_pass = message_data.get('password')
                        if r_name and r_name not in self.chat_rooms:
                            self.chat_rooms[r_name] = {"password": r_pass, "clients": []}
                            self.window.after(0, self.update_rooms_list)
                            self.window.after(0, lambda name=r_name: self.add_system_message(f"New room synced: {name}"))
                    
                    elif room == self.current_room and msg_type in ['text', 'image', 'user_joined', 'user_left']:
                        profile_img = message_data.get('profile_image')
                        timestamp = message_data.get('timestamp', '')
                        sender_u = message_data.get('username', '')
                        is_own = (sender_u == self.username)
                        
                        if msg_type == 'text':
                            self.window.after(0, self.add_message, sender_u, message_data['content'], is_own, profile_img, timestamp)
                        elif msg_type == 'image':
                            self.window.after(0, self.add_image_message, sender_u, message_data['content'], is_own, profile_img, timestamp)
                        elif msg_type == 'user_joined':
                            self.window.after(0, lambda u=sender_u: self.add_system_message(f"User {u} joined the room"))
                        elif msg_type == 'user_left':
                            self.window.after(0, lambda u=sender_u: self.add_system_message(f"User {u} left the room"))
                    
                    if self.is_server:
                        target_room = room
                        for client, c_room in list(self.client_rooms.items()):
                            if client != sock and client in self.client_usernames and (msg_type == 'room_sync' or c_room == target_room):
                                try:
                                    target_cipher = self.client_ciphers.get(client)
                                    if target_cipher:
                                        enc_msg = target_cipher.encrypt(decrypted_data.encode('utf-8'))
                                        client.send(enc_msg + b'\n')
                                except:
                                    self.remove_client(client)
                                    
            except Exception:
                break
                
        self.remove_client(sock)
        
    def cleanup_stale_files(self):
        if self.is_server:
            now = time.time()
            to_del = [fid for fid, pf in self.pending_files.items() if (now - pf['last_update'] > 60)]
            for fid in to_del:
                del self.pending_files[fid]
        self.window.after(30000, self.cleanup_stale_files)

    def remove_client(self, sock):
        if self.is_server:
            if sock in self.client_rooms:
                room = self.client_rooms.get(sock)
                username = self.client_usernames.get(sock, "Unknown user")
                del self.client_rooms[sock]
                if sock in self.client_ciphers: del self.client_ciphers[sock]
                if sock in self.client_usernames: del self.client_usernames[sock]
                
                if username != "Unknown user":
                    leave_event = {'type': 'user_left', 'username': username, 'room': room}
                    self.broadcast_message(leave_event)
                    if room == self.current_room:
                        self.window.after(0, lambda u=username: self.add_system_message(f"User {u} left the room"))
                    self.broadcast_users_list(room)

                self.window.after(0, lambda: self.status_label.configure(text=f"● Connected ({len(self.client_rooms)} users)"))
            try: sock.close()
            except: pass
        else:
            self.handle_disconnect()
            
    def handle_disconnect(self):
        self.connected = False
        self.authenticated = False
        self.cipher_suite = None
        
        self.window.after(0, lambda: self.create_room_btn.configure(state="disabled"))
        self.window.after(0, lambda: self.message_entry.configure(state="disabled"))
        self.window.after(0, lambda: self.file_btn.configure(state="disabled"))
        self.window.after(0, lambda: self.image_btn.configure(state="disabled"))
        self.window.after(0, lambda: self.send_btn.configure(state="disabled"))
        self.window.after(0, self.update_rooms_list)
        self.window.after(0, lambda: self.update_users_list([]))
        
        self.window.after(0, lambda: self.username_label_display.configure(text="Not Authenticated", text_color="#f38ba8"))
        self.window.after(0, lambda: self.status_label.configure(text="● Disconnected", text_color="#f38ba8"))
        self.window.after(0, lambda: self.add_system_message("Connection lost"))
    
    def add_message(self, username, message, is_own=False, profile_img=None, timestamp=None):
        msg_container = ctk.CTkFrame(self.messages_frame, fg_color=self.bg_color)
        msg_container.pack(anchor="e" if is_own else "w", padx=10, pady=5, fill="x")
        
        msg_frame = ctk.CTkFrame(msg_container, fg_color=self.accent_color if is_own else self.message_bg, corner_radius=10)
        msg_frame.pack(side="right" if is_own else "left", padx=5)
        
        header_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(8,2))
        
        if profile_img and not is_own:
            try:
                img_data = base64.b64decode(profile_img)
                img = Image.open(io.BytesIO(img_data))
                img.thumbnail((30, 30), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(30, 30))
                
                img_label = ctk.CTkLabel(header_frame, image=photo, text="")
                img_label.image = photo
                img_label.pack(side="left", padx=(0,8))
            except: pass
        
        user_label = ctk.CTkLabel(header_frame, text=username, font=("Arial", 11, "bold"), text_color="#1e1e2e" if is_own else self.accent_color)
        user_label.pack(side="left")
        
        if timestamp:
            time_label = ctk.CTkLabel(header_frame, text=timestamp, font=("Arial", 9), text_color="#1e1e2e" if is_own else "#6c7086")
            time_label.pack(side="right", padx=(10,0))
        
        text_label = ctk.CTkLabel(msg_frame, text=message, font=("Arial", 13), text_color="#1e1e2e" if is_own else "#cdd6f4", wraplength=500, justify="left")
        text_label.pack(anchor="w", padx=10, pady=(0,8))
        
        self.messages_frame._parent_canvas.yview_moveto(1.0)
    
    def add_image_message(self, username, img_base64, is_own=False, profile_img=None, timestamp=None):
        msg_container = ctk.CTkFrame(self.messages_frame, fg_color=self.bg_color)
        msg_container.pack(anchor="e" if is_own else "w", padx=10, pady=5)
        
        msg_frame = ctk.CTkFrame(msg_container, fg_color=self.accent_color if is_own else self.message_bg, corner_radius=10)
        msg_frame.pack(side="right" if is_own else "left", padx=5)
        
        header_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(8,5))
        
        if profile_img and not is_own:
            try:
                prof_img_data = base64.b64decode(profile_img)
                img = Image.open(io.BytesIO(prof_img_data))
                img.thumbnail((30, 30), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(30, 30))
                
                img_label = ctk.CTkLabel(header_frame, image=photo, text="")
                img_label.image = photo
                img_label.pack(side="left", padx=(0,8))
            except: pass
        
        user_label = ctk.CTkLabel(header_frame, text=username, font=("Arial", 11, "bold"), text_color="#1e1e2e" if is_own else self.accent_color)
        user_label.pack(side="left")
        
        if timestamp:
            time_label = ctk.CTkLabel(header_frame, text=timestamp, font=("Arial", 9), text_color="#1e1e2e" if is_own else "#6c7086")
            time_label.pack(side="right", padx=(10,0))
        
        try:
            content_img_data = base64.b64decode(img_base64)
            img = Image.open(io.BytesIO(content_img_data))
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

            img_label = ctk.CTkLabel(msg_frame, image=photo, text="")
            img_label.image = photo
            img_label.pack(padx=10, pady=(0,5))

            save_btn = ctk.CTkButton(msg_frame, text="Download", width=80, height=25, command=lambda d=content_img_data: self.save_image(d), fg_color="#6c7086")
            save_btn.pack(pady=(0,8))

        except Exception:
            error_label = ctk.CTkLabel(msg_frame, text="[Image load error]", text_color="#f38ba8")
            error_label.pack(padx=10, pady=(0,8))

        self.messages_frame._parent_canvas.yview_moveto(1.0)

    def save_image(self, img_data):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")])
        if not file_path: return
        try:
            with open(file_path, "wb") as f:
                f.write(img_data)
            self.add_system_message("Image saved successfully")
        except Exception as e:
            self.add_system_message(f"Save error: {str(e)}")

    def add_system_message(self, message):
        msg_label = ctk.CTkLabel(self.messages_frame, text=f"ℹ {message}", font=("Arial", 11, "italic"), text_color="#6c7086")
        msg_label.pack(pady=5)
        self.messages_frame._parent_canvas.yview_moveto(1.0)

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = DarklineMessenger()
    app.run()
    
