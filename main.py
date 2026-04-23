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

class DarklineMessenger:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Darkline Messenger")
        self.window.geometry("1000x650")
        
      
        self.cipher_suite = Fernet(b'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=')

        # --- Favicon Configuration ---
        try:
            # For Windows (.ico):
            # self.window.iconbitmap("favicon.ico")
            
            # For Linux/Mac/Windows (.png):
            # icon_img = ImageTk.PhotoImage(Image.open("favicon.png"))
            # self.window.iconphoto(False, icon_img)
            pass # Remove this pass when you uncomment the lines above
        except Exception as e:
            print(f"Failed to load favicon: {e}")
        # -----------------------------

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Network variables
        self.server_socket = None
        self.client_socket = None
        self.is_server = False
        self.connected = False
        self.username = "User"
        self.profile_image = None
        self.clients = []
        self.chat_rooms = {"General": {"password": None, "clients": []}}
        self.current_room = "General"
        
        # Colors
        self.bg_color = "#1e1e2e"
        self.sidebar_color = "#181825"
        self.message_bg = "#313244"
        self.accent_color = "#89b4fa"
        
        self.setup_ui()
        self.update_clock()
        
    def setup_ui(self):
        # Main container
        self.window.configure(fg_color=self.bg_color)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self.window, width=280, fg_color=self.sidebar_color, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)
        
        # Logo area
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color=self.sidebar_color, height=80)
        logo_frame.pack(fill="x", padx=15, pady=15)
        
        logo_label = ctk.CTkLabel(
            logo_frame, 
            text="⚡ DARKLINE", 
            font=("Arial", 24, "bold"),
            text_color=self.accent_color
        )
        logo_label.pack()
        
        subtitle = ctk.CTkLabel(
            logo_frame,
            text="Local Messenger",
            font=("Arial", 11),
            text_color="#6c7086"
        )
        subtitle.pack()
        
        # Clock display
        self.clock_label = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=("Arial", 12),
            text_color="#a6e3a1"
        )
        self.clock_label.pack(pady=5)
        
        # Profile section
        profile_frame = ctk.CTkFrame(self.sidebar, fg_color=self.sidebar_color)
        profile_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(profile_frame, text="Profile:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,5))
        
        # Profile image button
        self.profile_btn = ctk.CTkButton(
            profile_frame,
            text="📷 Set Profile Picture",
            command=self.set_profile_image,
            fg_color=self.message_bg,
            hover_color="#45475a",
            height=35
        )
        self.profile_btn.pack(fill="x", pady=(0,10))
        
        ctk.CTkLabel(profile_frame, text="Username:", font=("Arial", 12)).pack(anchor="w", pady=(0,5))
        self.username_entry = ctk.CTkEntry(profile_frame, placeholder_text="Enter your name")
        self.username_entry.pack(fill="x", pady=(0,10))
        
        # Connection section
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
        
        # Connection buttons
        self.host_btn = ctk.CTkButton(
            conn_frame,
            text="🖥️ Host Server",
            command=self.start_server,
            fg_color=self.accent_color,
            hover_color="#74c7ec"
        )
        self.host_btn.pack(fill="x", pady=3)
        
        self.connect_btn = ctk.CTkButton(
            conn_frame,
            text="🔗 Connect",
            command=self.connect_to_server,
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            text_color="#1e1e2e"
        )
        self.connect_btn.pack(fill="x", pady=3)
        
        # Network IP display
        self.network_ip_label = ctk.CTkLabel(
            self.sidebar,
            text=f"Your IP: {self.get_local_ip()}",
            font=("Arial", 10),
            text_color="#f9e2af"
        )
        self.network_ip_label.pack(pady=5)
        
        # Chat rooms section
        rooms_frame = ctk.CTkFrame(self.sidebar, fg_color=self.sidebar_color)
        rooms_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(rooms_frame, text="Chat Rooms:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,5))
        
        self.create_room_btn = ctk.CTkButton(
            rooms_frame,
            text="➕ Create Room",
            command=self.create_chat_room,
            fg_color=self.message_bg,
            hover_color="#45475a",
            height=30
        )
        self.create_room_btn.pack(fill="x", pady=(0,5))
        
        # Rooms list
        self.rooms_list_frame = ctk.CTkScrollableFrame(
            rooms_frame,
            fg_color=self.sidebar_color,
            height=100
        )
        self.rooms_list_frame.pack(fill="x", pady=(0,5))
        self.update_rooms_list()
        
        # Status
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="● Disconnected",
            font=("Arial", 11),
            text_color="#f38ba8"
        )
        self.status_label.pack(side="bottom", pady=15)
        
        # Chat area
        chat_container = ctk.CTkFrame(self.window, fg_color=self.bg_color)
        chat_container.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        
        # Header
        header = ctk.CTkFrame(chat_container, height=60, fg_color=self.sidebar_color, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        self.room_label = ctk.CTkLabel(
            header,
            text=f"💬 {self.current_room}",
            font=("Arial", 18, "bold"),
            text_color=self.accent_color
        )
        self.room_label.pack(side="left", padx=20, pady=15)
        
        # Messages area
        self.messages_frame = ctk.CTkScrollableFrame(
            chat_container,
            fg_color=self.bg_color,
            corner_radius=0
        )
        self.messages_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Input area
        input_container = ctk.CTkFrame(chat_container, fg_color=self.sidebar_color, height=80, corner_radius=0)
        input_container.pack(fill="x", padx=0, pady=0, side="bottom")
        input_container.pack_propagate(False)
        
        input_frame = ctk.CTkFrame(input_container, fg_color=self.sidebar_color)
        input_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.message_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a message...",
            height=40,
            font=("Arial", 13)
        )
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        self.image_btn = ctk.CTkButton(
            input_frame,
            text="📷",
            width=50,
            height=40,
            command=self.send_image,
            fg_color=self.message_bg,
            hover_color="#45475a"
        )
        self.image_btn.pack(side="left", padx=(0,5))
        
        self.send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            width=80,
            height=40,
            command=self.send_message,
            fg_color=self.accent_color,
            hover_color="#74c7ec"
        )
        self.send_btn.pack(side="left")
    
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
            return "Unknown"
    
    def set_profile_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        
        if not file_path:
            return
        
        try:
            with Image.open(file_path) as img:
                img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                self.profile_image = base64.b64encode(buffer.getvalue()).decode()
                self.add_system_message("Profile picture set successfully")
        except Exception as e:
            self.add_system_message(f"Error setting profile picture: {str(e)}")
    
    def create_chat_room(self):
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
            
            if not room_name:
                return
            
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
                    'password': password
                }
                self.broadcast_message(sync_data)
                
            dialog.destroy()
        
        ctk.CTkButton(
            dialog,
            text="Create",
            command=create,
            fg_color=self.accent_color
        ).pack(pady=20)
    
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
            room_btn.pack(fill="x", pady=2)
    
    def join_room(self, room_name):
        room = self.chat_rooms.get(room_name)
        if not room:
            return
        
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
                    self.current_room = room_name
                    self.room_label.configure(text=f"💬 {self.current_room}")
                    self.update_rooms_list()
                    self.add_system_message(f"Joined room: {room_name}")
                    dialog.destroy()
                else:
                    self.add_system_message("Incorrect password")
                    dialog.destroy()
            
            ctk.CTkButton(
                dialog,
                text="Join",
                command=check_password,
                fg_color=self.accent_color
            ).pack(pady=10)
        else:
            self.current_room = room_name
            self.room_label.configure(text=f"💬 {self.current_room}")
            self.update_rooms_list()
            self.add_system_message(f"Joined room: {room_name}")
        
    def start_server(self):
        if self.connected:
            return
            
        self.username = self.username_entry.get() or "Host"
        port = int(self.port_entry.get() or 5555)
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)
            
            self.is_server = True
            self.status_label.configure(text="● Waiting for connection...", text_color="#f9e2af")
            self.add_system_message(f"Server started on {self.get_local_ip()}:{port}")
            
            threading.Thread(target=self.accept_connections, daemon=True).start()
            
        except Exception as e:
            self.add_system_message(f"Error: {str(e)}")
    
    def accept_connections(self):
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                self.clients.append(client_socket)
                self.connected = True
                self.status_label.configure(text=f"● Connected ({len(self.clients)} users)", text_color="#a6e3a1")
                self.add_system_message(f"User connected from {addr[0]}")
                
                # Send existing rooms to newly connected client
                for room_name, room_data in self.chat_rooms.items():
                    if room_name != "General":
                        sync_data = {
                            'type': 'room_sync',
                            'room_name': room_name,
                            'password': room_data['password']
                        }
                        try:
                            # رمزنگاری داده های ارسالی به کلاینت جدید
                            msg_json = json.dumps(sync_data)
                            enc_msg = self.cipher_suite.encrypt(msg_json.encode('utf-8'))
                            client_socket.send(enc_msg + b'\n')
                        except:
                            pass
                
                threading.Thread(target=self.receive_messages, args=(client_socket,), daemon=True).start()
                
            except Exception as e:
                break
    
    def connect_to_server(self):
        if self.connected:
            return
            
        self.username = self.username_entry.get() or "Guest"
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
            self.status_label.configure(text="● Connected", text_color="#a6e3a1")
            self.add_system_message(f"Connected to {host}")
            
            threading.Thread(target=self.receive_messages, args=(self.client_socket,), daemon=True).start()
            
        except Exception as e:
            self.add_system_message(f"Connection failed: {str(e)}")
    
    def send_message(self):
        if not self.connected:
            self.add_system_message("Not connected!")
            return
            
        message = self.message_entry.get().strip()
        if not message:
            return
            
        try:
            data = {
                'type': 'text',
                'username': self.username,
                'content': message,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'profile_image': self.profile_image,
                'room': self.current_room
            }
            
            self.broadcast_message(data)
            self.add_message(self.username, message, is_own=True, profile_img=self.profile_image)
            self.message_entry.delete(0, 'end')
            
        except Exception as e:
            self.add_system_message(f"Send error: {str(e)}")
    
    def send_image(self):
        if not self.connected:
            self.add_system_message("Not connected!")
            return
            
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        
        if not file_path:
            return
            
        try:
            with Image.open(file_path) as img:
                max_size = (400, 400)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue()).decode()
                
            data = {
                'type': 'image',
                'username': self.username,
                'content': img_str,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'profile_image': self.profile_image,
                'room': self.current_room
            }
            
            self.broadcast_message(data)
            self.add_image_message(self.username, img_str, is_own=True, profile_img=self.profile_image)
            
        except Exception as e:
            self.add_system_message(f"Image send error: {str(e)}")
    
    def broadcast_message(self, data):
        
        message_json = json.dumps(data)
        encrypted_data = self.cipher_suite.encrypt(message_json.encode('utf-8'))
        payload = encrypted_data + b'\n'
        
        if self.is_server:
            for client in self.clients:
                try:
                    client.send(payload)
                except:
                    self.clients.remove(client)
        else:
            self.client_socket.send(payload)
    
    def receive_messages(self, sock):
        buffer = ""
        while self.connected:
            try:
                data = sock.recv(4096).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    
                    try:

                      decrypted_data = self.cipher_suite.decrypt(line.encode('utf-8')).decode('utf-8')
                        message_data = json.loads(decrypted_data)
                    except Exception:
                        continue 
                    
                    msg_type = message_data.get('type')
                    
                    if msg_type == 'room_sync':
                        r_name = message_data.get('room_name')
                        r_pass = message_data.get('password')
                        if r_name and r_name not in self.chat_rooms:
                            self.chat_rooms[r_name] = {"password": r_pass, "clients": []}
                            self.window.after(0, self.update_rooms_list)
                            self.window.after(0, lambda name=r_name: self.add_system_message(f"New room synced: {name}"))
                    elif message_data.get('room') == self.current_room:
                        profile_img = message_data.get('profile_image')
                        timestamp = message_data.get('timestamp', '')
                        
                        if msg_type == 'text':
                            self.window.after(0, self.add_message, message_data['username'], message_data['content'], False, profile_img, timestamp)
                        elif msg_type == 'image':
                            self.window.after(0, self.add_image_message, message_data['username'], message_data['content'], False, profile_img, timestamp)
                    
                    # Relay to other clients if we are the server
                    if self.is_server:
                        for client in self.clients:
                            if client != sock:
                                try:

                                    client.send((line + '\n').encode('utf-8'))
                                except:
                                    self.clients.remove(client)
                        
            except Exception as e:
                break
                
        if sock in self.clients:
            self.clients.remove(sock)
        
        if not self.is_server or len(self.clients) == 0:
            self.connected = False
            self.status_label.configure(text="● Disconnected", text_color="#f38ba8")
            self.window.after(0, lambda: self.add_system_message("Connection lost"))
    
    def add_message(self, username, message, is_own=False, profile_img=None, timestamp=None):
        msg_container = ctk.CTkFrame(self.messages_frame, fg_color=self.bg_color)
        msg_container.pack(anchor="e" if is_own else "w", padx=10, pady=5, fill="x")
        
        msg_frame = ctk.CTkFrame(
            msg_container,
            fg_color=self.accent_color if is_own else self.message_bg,
            corner_radius=10
        )
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
            except:
                pass
        
        user_label = ctk.CTkLabel(
            header_frame,
            text=username,
            font=("Arial", 11, "bold"),
            text_color="#1e1e2e" if is_own else self.accent_color
        )
        user_label.pack(side="left")
        
        if timestamp:
            time_label = ctk.CTkLabel(
                header_frame,
                text=timestamp,
                font=("Arial", 9),
                text_color="#1e1e2e" if is_own else "#6c7086"
            )
            time_label.pack(side="right", padx=(10,0))
        
        text_label = ctk.CTkLabel(
            msg_frame,
            text=message,
            font=("Arial", 13),
            text_color="#1e1e2e" if is_own else "#cdd6f4",
            wraplength=500,
            justify="left"
        )
        text_label.pack(anchor="w", padx=10, pady=(0,8))
        
        self.messages_frame._parent_canvas.yview_moveto(1.0)
    
    def add_image_message(self, username, img_base64, is_own=False, profile_img=None, timestamp=None):
        msg_container = ctk.CTkFrame(self.messages_frame, fg_color=self.bg_color)
        msg_container.pack(anchor="e" if is_own else "w", padx=10, pady=5)
        
        msg_frame = ctk.CTkFrame(
            msg_container,
            fg_color=self.accent_color if is_own else self.message_bg,
            corner_radius=10
        )
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
            except:
                pass
        
        user_label = ctk.CTkLabel(
            header_frame,
            text=username,
            font=("Arial", 11, "bold"),
            text_color="#1e1e2e" if is_own else self.accent_color
        )
        user_label.pack(side="left")
        
        if timestamp:
            time_label = ctk.CTkLabel(
                header_frame,
                text=timestamp,
                font=("Arial", 9),
                text_color="#1e1e2e" if is_own else "#6c7086"
            )
            time_label.pack(side="right", padx=(10,0))
        
        try:
            content_img_data = base64.b64decode(img_base64)
            img = Image.open(io.BytesIO(content_img_data))
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

            img_label = ctk.CTkLabel(msg_frame, image=photo, text="")
            img_label.image = photo
            img_label.pack(padx=10, pady=(0,5))

            save_btn = ctk.CTkButton(
                msg_frame,
                text="Download",
                width=80,
                height=25,
                command=lambda d=content_img_data: self.save_image(d),
                fg_color="#6c7086"
            )
            save_btn.pack(pady=(0,8))

        except Exception:
            error_label = ctk.CTkLabel(
                msg_frame,
                text="[Image load error]",
                text_color="#f38ba8"
            )
            error_label.pack(padx=10, pady=(0,8))

        self.messages_frame._parent_canvas.yview_moveto(1.0)

    def save_image(self, img_data):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "wb") as f:
                f.write(img_data)
            self.add_system_message("Image saved successfully")
        except Exception as e:
            self.add_system_message(f"Save error: {str(e)}")

    def add_system_message(self, message):
        msg_label = ctk.CTkLabel(
            self.messages_frame,
            text=f"ℹ {message}",
            font=("Arial", 11, "italic"),
            text_color="#6c7086"
        )
        msg_label.pack(pady=5)
        self.messages_frame._parent_canvas.yview_moveto(1.0)

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = DarklineMessenger()
    app.run()
