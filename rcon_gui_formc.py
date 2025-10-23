import tkinter as tk
from tkinter import scrolledtext, messagebox, Menu
import subprocess
import sys
import threading
from datetime import datetime
import os
import webbrowser
import json

class ConfigDialog(tk.Toplevel):
    """Configuration dialog window"""
    def __init__(self, parent, config_data=None):
        super().__init__(parent)
        self.parent = parent
        self.config_data = config_data or {}
        self.result = None
        
        self.title("RCON Configuration")
        self.geometry("500x350")  # Smaller since we removed mcrcon path
        self.configure(bg="#0d1117")
        self.resizable(False, False)
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        # Center the dialog
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        # Title
        title_frame = tk.Frame(self, bg="#0969da", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="⚙️ RCON Configuration",
            font=("Segoe UI", 16, "bold"),
            bg="#0969da",
            fg="white"
        )
        title_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Main content
        content_frame = tk.Frame(self, bg="#0d1117")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Server IP
        self.create_field(content_frame, "Server IP/Domain:", 
                         self.config_data.get('server_ip', ''), 0)
        
        # Port
        self.create_field(content_frame, "RCON Port:", 
                         self.config_data.get('port', ''), 1)
        
        # Password
        self.create_field(content_frame, "RCON Password:", 
                         self.config_data.get('password', ''), 2, show="*")
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg="#0d1117")
        button_frame.grid(row=3, column=0, columnspan=2, pady=(30, 0))
        
        save_btn = tk.Button(
            button_frame,
            text="💾 Save Configuration",
            command=self.save_config,
            bg="#238636",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            bd=0
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            bg="#21262d",
            fg="#c9d1d9",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            bd=0
        )
        cancel_btn.pack(side=tk.LEFT)
    
    def create_field(self, parent, label_text, default_value, row, show=None):
        label = tk.Label(
            parent,
            text=label_text,
            font=("Segoe UI", 10, "bold"),
            bg="#0d1117",
            fg="#c9d1d9",
            anchor="w"
        )
        label.grid(row=row, column=0, sticky="w", pady=(0, 5))
        
        entry_frame = tk.Frame(parent, bg="#30363d", relief=tk.FLAT, bd=1)
        entry_frame.grid(row=row, column=1, sticky="ew", pady=(0, 15), padx=(15, 0))
        
        entry_inner = tk.Frame(entry_frame, bg="#010409")
        entry_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        entry = tk.Entry(
            entry_inner,
            font=("Segoe UI", 10),
            bg="#010409",
            fg="#c9d1d9",
            relief=tk.FLAT,
            insertbackground="#58a6ff",
            bd=0,
            show=show
        )
        entry.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        entry.insert(0, default_value)
        
        # Store entry reference with simple mapping
        if "Server IP" in label_text:
            self.entry_server_ip = entry
        elif "Port" in label_text:
            self.entry_port = entry
        elif "Password" in label_text:
            self.entry_password = entry
        
        parent.grid_columnconfigure(1, weight=1)
    
    def save_config(self):
        # Get values
        server_ip = self.entry_server_ip.get().strip()
        port = self.entry_port.get().strip()
        password = self.entry_password.get().strip()
        
        # Validate
        if not server_ip or not port or not password:
            messagebox.showerror("Error", "Please fill in all required fields!")
            return
        
        # Save to config.json
        config_content = {
            "server_ip": server_ip,
            "port": port,
            "password": password
        }
        
        try:
            with open("config.json", 'w') as f:
                json.dump(config_content, f, indent=4)
            
            messagebox.showinfo("Success", "Configuration saved successfully!\nRestart the application to apply changes.")
            self.result = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")

class RCONGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft RCON Control Panel")
        self.root.geometry("900x750")
        self.root.configure(bg="#0d1117")
        self.root.resizable(True, True)
        
        # Set window icon
        try:
            if os.path.exists("icon.png"):
                icon_image = tk.PhotoImage(file="icon.png")
                self.root.iconphoto(True, icon_image)
        except Exception as e:
            print(f"Could not load icon: {e}")
        
        # Set minimum window size
        self.root.minsize(700, 600)
        
        # Load configuration
        self.config_loaded = self.load_config()
        self.connection_status = False
        
        # Auto-prompt for config if not loaded
        if not self.config_loaded:
            self.root.after(100, self.auto_prompt_config)
        
        # Create menu bar
        self.create_menu()
        
        # Create main container with grid for dynamic resizing
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Header Section
        self.create_header()
        
        # Main container (scrollable and dynamic)
        main_container = tk.Frame(self.root, bg="#0d1117")
        main_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 0))
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Canvas for scrollable content (scrollbar removed for cleaner UI)
        canvas = tk.Canvas(main_container, bg="#0d1117", highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        
        # Configure canvas scrolling (no scrollbar needed for main screen)
        canvas.configure(yscrollcommand=None)
        
        # Inner frame for content
        inner_container = tk.Frame(canvas, bg="#0d1117")
        canvas_window = canvas.create_window((0, 0), window=inner_container, anchor="nw")
        
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        inner_container.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        # Main frame with rounded edges
        main_frame = tk.Frame(inner_container, bg="#161b22", relief=tk.FLAT, bd=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        content_frame = tk.Frame(main_frame, bg="#161b22")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Configure grid for dynamic resizing
        content_frame.grid_rowconfigure(6, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Message Section
        self.create_modern_section(
            content_frame,
            "💬 Send Message to Server",
            "Type your broadcast message...",
            self.send_message,
            "Send Message",
            0,
            "#0969da"
        )
        
        # Command Section
        self.create_modern_section(
            content_frame,
            "⚙️ Execute Server Command",
            "e.g., time set day, weather clear, gamemode creative",
            self.send_command,
            "Execute Command",
            1,
            "#1f6feb"
        )
        
        # Quick Commands Section
        self.create_quick_commands(content_frame)
        
        # Output Section (expandable)
        self.create_output_section(content_frame)
        
        # Footer (always visible at bottom)
        self.create_footer()
        
        # Initial message
        if self.config_loaded:
            self.add_output("✓ RCON GUI initialized successfully", "success")
            self.add_output(f"✓ Configuration loaded from config.json", "success")
            self.test_connection()
            # Start monitoring for config changes
            self.start_config_monitor()
        else:
            self.add_output("⚠ Configuration not found", "warning")
            self.add_output("⚠ Please set up your RCON configuration", "warning")
    
    def auto_prompt_config(self):
        """Automatically prompt for configuration if not exists"""
        response = messagebox.askyesno(
            "Configuration Required", 
            "No RCON configuration found.\n\nWould you like to set it up now?"
        )
        if response:
            self.open_config_dialog()
    
    def create_tooltip(self, widget, text):
        """Create a modern tooltip for a widget"""
        def show_tooltip(event):
            x = widget.winfo_rootx() + 25
            y = widget.winfo_rooty() + 30
            
            # Create tooltip window with modern styling
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            self.tooltip.configure(bg="#161b22")
            
            # Modern tooltip frame
            tooltip_frame = tk.Frame(
                self.tooltip,
                bg="#161b22",
                highlightthickness=1,
                highlightbackground="#30363d"
            )
            tooltip_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
            
            label = tk.Label(
                tooltip_frame,
                text=text,
                justify='left',
                background="#161b22",
                foreground="#c9d1d9",
                font=("Segoe UI", 9),
                padx=8,
                pady=4
            )
            label.pack()
        
        def hide_tooltip(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                delattr(self, 'tooltip')
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def create_menu(self):
        """Create menu bar"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0, bg="#161b22", fg="#c9d1d9", 
                        activebackground="#0969da", activeforeground="white")
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Configuration", command=self.open_config_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0, bg="#161b22", fg="#c9d1d9",
                        activebackground="#0969da", activeforeground="white")
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def open_config_dialog(self):
        """Open configuration dialog"""
        config_data = {
            'server_ip': getattr(self, 'server_host', ''),
            'port': getattr(self, 'server_port', ''),
            'password': getattr(self, 'rcon_password', '')
        }
        
        dialog = ConfigDialog(self.root, config_data)
        self.root.wait_window(dialog)
        
        if dialog.result:
            # Reload configuration
            self.load_config()
            self.update_server_info()
            self.test_connection()
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Minecraft RCON Control Panel
Version 1.0

A modern GUI for managing Minecraft servers via RCON protocol.

Designed by h190k
https://h190k.com"""
        
        messagebox.showinfo("About", about_text)
    
    def update_server_info(self):
        """Update server info in header after config change"""
        if hasattr(self, 'server_info_label'):
            self.server_info_label.config(text=f"{self.server_host}:{self.server_port}")
        else:
            # Fallback: search for the label
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and "📡" in child.cget("text"):
                            child.config(text=f"📡 {self.server_host}:{self.server_port}")
    
    def create_header(self):
        """Create modern header with gradient effect"""
        header_frame = tk.Frame(self.root, bg="#0969da", height=110)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title container
        title_container = tk.Frame(header_frame, bg="#0969da")
        title_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Main title
        title_label = tk.Label(
            title_container,
            text="🎮 Minecraft RCON",
            font=("Segoe UI", 26, "bold"),
            bg="#0969da",
            fg="#ffffff"
        )
        title_label.pack(pady=(0, 2))
        
        subtitle_label = tk.Label(
            title_container,
            text="Control Panel",
            font=("Segoe UI", 13),
            bg="#0969da",
            fg="#c9d1d9"
        )
        subtitle_label.pack()
        
        # Status indicator in top right
        status_frame = tk.Frame(header_frame, bg="#0969da")
        status_frame.place(relx=0.96, rely=0.5, anchor=tk.E)
        
        # Refresh button with modern design and subtle padding
        refresh_outer = tk.Frame(status_frame, bg="#238636", relief=tk.FLAT, bd=0)
        refresh_outer.pack(side=tk.LEFT, padx=(0, 8))
        
        refresh_inner = tk.Frame(refresh_outer, bg="#161b22")
        refresh_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        refresh_btn = tk.Button(
            refresh_inner,
            text="↻",
            command=self.refresh_connection,
            bg="#238636",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=10,
            pady=6,
            bd=0,
            activebackground="#2ea043",
            activeforeground="white",
            highlightthickness=0,
            borderwidth=0
        )
        refresh_btn.pack()
        
        # Modern hover effects with smooth transitions
        def on_enter(e):
            refresh_outer.config(bg="#2ea043")
            refresh_btn.config(bg="#2ea043")
        
        def on_leave(e):
            refresh_outer.config(bg="#238636")
            refresh_btn.config(bg="#238636")
        
        refresh_btn.bind("<Enter>", on_enter)
        refresh_btn.bind("<Leave>", on_leave)
        
        # Create tooltip for refresh button
        self.create_tooltip(refresh_btn, "Refresh Connection (Check/Reconnect)")
        
        self.status_canvas = tk.Canvas(
            status_frame,
            width=14,
            height=14,
            bg="#0969da",
            highlightthickness=0
        )
        self.status_canvas.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_dot = self.status_canvas.create_oval(
            2, 2, 12, 12,
            fill="#6e7681",
            outline=""
        )
        
        self.status_label = tk.Label(
            status_frame,
            text="Disconnected",
            font=("Segoe UI", 10, "bold"),
            bg="#0969da",
            fg="#c9d1d9"
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Server info container placed just below status frame to avoid overlap
        if hasattr(self, 'server_host') and hasattr(self, 'server_port'):
            server_info_frame = tk.Frame(header_frame, bg="#161b22", relief=tk.FLAT, bd=0)
            # Position under status frame with 24px downward offset to avoid overlap
            server_info_frame.place(relx=0.96, rely=0.5, anchor=tk.NE, y=24)
            
            # Server icon with modern styling
            server_icon = tk.Label(
                server_info_frame,
                text="🖧",
                font=("Segoe UI", 10),
                bg="#161b22",
                fg="#58a6ff"
            )
            server_icon.pack(side=tk.LEFT, padx=(0, 4))
            
            # Server address with monospace font for better readability
            self.server_info_label = tk.Label(
                server_info_frame,
                text=f"{self.server_host}:{self.server_port}",
                font=("Consolas", 9, "bold"),
                bg="#161b22",
                fg="#c9d1d9"
            )
            self.server_info_label.pack(side=tk.LEFT)
            
            # Add subtle hover effect
            def on_server_hover(e):
                server_icon.config(fg="#79c0ff")
                self.server_info_label.config(fg="#ffffff")
            
            def on_server_leave(e):
                server_icon.config(fg="#58a6ff")
                self.server_info_label.config(fg="#c9d1d9")
            
            server_info_frame.bind("<Enter>", on_server_hover)
            server_info_frame.bind("<Leave>", on_server_leave)
            server_icon.bind("<Enter>", on_server_hover)
            server_icon.bind("<Leave>", on_server_leave)
            self.server_info_label.bind("<Enter>", on_server_hover)
            self.server_info_label.bind("<Leave>", on_server_leave)
        
        # Animated pulse effect
        self.animate_status()
    
    def _subprocess_no_window(self):
        """Return kwargs to prevent console window on Windows when using subprocess"""
        if sys.platform.startswith("win"):
            return {"creationflags": subprocess.CREATE_NO_WINDOW}
        return {}

    def create_footer(self):
        """Create footer with designer credit - always visible"""
        footer_frame = tk.Frame(self.root, bg="#0d1117", height=45)
        footer_frame.grid(row=2, column=0, sticky="ew")
        footer_frame.grid_propagate(False)
        
        footer_content = tk.Frame(footer_frame, bg="#0d1117")
        footer_content.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        designed_label = tk.Label(
            footer_content,
            text="Designed by ",
            font=("Segoe UI", 10),
            bg="#0d1117",
            fg="#8b949e"
        )
        designed_label.pack(side=tk.LEFT)
        
        # Clickable h190k link
        link_label = tk.Label(
            footer_content,
            text="h190k",
            font=("Segoe UI", 10, "bold"),
            bg="#0d1117",
            fg="#58a6ff",
            cursor="hand2"
        )
        link_label.pack(side=tk.LEFT)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://h190k.com"))
        link_label.bind("<Enter>", lambda e: link_label.config(fg="#79c0ff"))
        link_label.bind("<Leave>", lambda e: link_label.config(fg="#58a6ff"))
    
    def animate_status(self):
        """Animate status indicator with pulse effect"""
        if not self.connection_status:
            current_color = self.status_canvas.itemcget(self.status_dot, "fill")
            if current_color == "#6e7681":
                self.status_canvas.itemconfig(self.status_dot, fill="#484f58")
            else:
                self.status_canvas.itemconfig(self.status_dot, fill="#6e7681")
        self.root.after(1000, self.animate_status)
    
    def update_status(self, connected):
        """Update connection status indicator"""
        self.connection_status = connected
        if connected:
            self.status_canvas.itemconfig(self.status_dot, fill="#3fb950")
            self.status_label.config(text="Connected", fg="#c9d1d9")
        else:
            self.status_canvas.itemconfig(self.status_dot, fill="#f85149")
            self.status_label.config(text="Disconnected", fg="#c9d1d9")
    
    def refresh_connection(self):
        """Refresh connection - check current status and reconnect if needed"""
        if not hasattr(self, 'server_host') or not self.server_host:
            self.add_output("⚠ Please configure RCON settings first", "warning")
            return
            
        self.add_output("🔄 Refreshing connection...", "info")
        
        # Add visual feedback for button click with rotation animation
        refresh_btn = None
        # Find the refresh button in the status frame
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):
                        for subchild in child.winfo_children():
                            if isinstance(subchild, tk.Button) and subchild.cget("text") == "↻":
                                refresh_btn = subchild
                                break
        
        if refresh_btn:
            # Animate button click with rotation
            def animate_rotation(degrees=0):
                if degrees <= 360:
                    refresh_btn.config(text=f"↻", font=("Segoe UI", 12, "bold"))
                    # Simulate rotation by changing the text slightly
                    if degrees < 90:
                        refresh_btn.config(text="↻")
                    elif degrees < 180:
                        refresh_btn.config(text="↺")
                    elif degrees < 270:
                        refresh_btn.config(text="↻")
                    else:
                        refresh_btn.config(text="↺")
                    
                    self.root.after(50, lambda: animate_rotation(degrees + 45))
                else:
                    # Reset button appearance
                    refresh_btn.config(text="↻", bg="#238636", fg="#ffffff")
            
            # Start animation and color change
            refresh_btn.config(bg="#1a7a2e", fg="#ffffff")
            animate_rotation()
        
        thread = threading.Thread(target=self._test_connection_thread)
        thread.daemon = True
        thread.start()
    
    def test_connection(self):
        """Test connection to RCON server"""
        if not hasattr(self, 'server_host'):
            self.add_output("⚠ Configuration not set", "warning")
            return
            
        self.add_output("🔄 Testing connection...", "info")
        thread = threading.Thread(target=self._test_connection_thread)
        thread.daemon = True
        thread.start()
    
    def _test_connection_thread(self):
        """Test connection in background thread with reconnection logic"""
        try:
            # mcrcon is always in same directory
            mcrcon_path = "./mcrcon.exe"
            
            if not os.path.exists(mcrcon_path):
                self.root.after(0, lambda: self.update_status(False))
                self.root.after(0, lambda: self.add_output(
                    f"✗ mcrcon.exe not found in application directory", "error"
                ))
                return
            
            full_command = [
                mcrcon_path,
                "-H", self.server_host,
                "-P", self.server_port,
                "-p", self.rcon_password,
                "list"
            ]
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=5,
                **self._subprocess_no_window()
            )
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.update_status(True))
                self.root.after(0, lambda: self.add_output("✓ Connected to server successfully", "success"))
            else:
                self.root.after(0, lambda: self.update_status(False))
                error_msg = result.stderr.strip() if result.stderr.strip() else "Connection failed"
                self.root.after(0, lambda: self.add_output(f"✗ {error_msg}", "error"))
                
                # If connection failed, provide helpful suggestions
                if "connection refused" in error_msg.lower():
                    self.root.after(0, lambda: self.add_output("💡 Tip: Check if RCON is enabled in server.properties", "info"))
                elif "timeout" in error_msg.lower():
                    self.root.after(0, lambda: self.add_output("💡 Tip: Check server IP and port settings", "info"))
                elif "authentication" in error_msg.lower() or "password" in error_msg.lower():
                    self.root.after(0, lambda: self.add_output("💡 Tip: Verify RCON password is correct", "info"))
        
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.update_status(False))
            self.root.after(0, lambda: self.add_output("✗ Connection timeout", "error"))
            self.root.after(0, lambda: self.add_output("💡 Tip: Check if server is online and RCON port is open", "info"))
        except Exception as e:
            self.root.after(0, lambda: self.update_status(False))
            self.root.after(0, lambda: self.add_output(f"✗ Connection error: {str(e)}", "error"))
            self.root.after(0, lambda: self.add_output("💡 Tip: Check server configuration and network connectivity", "info"))
    
    def load_config(self):
        """Load configuration from config.json file"""
        config_file = "config.json"
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                self.server_host = config_data.get('server_ip', '')
                self.server_port = config_data.get('port', '')
                self.rcon_password = config_data.get('password', '')
                return True
            else:
                # No config file found
                self.server_host = ""
                self.server_port = ""
                self.rcon_password = ""
                return False
        
        except Exception as e:
            print(f"Error loading config: {e}")
            self.server_host = ""
            self.server_port = ""
            self.rcon_password = ""
            return False
    
    def start_config_monitor(self):
        """Start monitoring config.json for changes"""
        self.config_last_modified = os.path.getmtime("config.json") if os.path.exists("config.json") else 0
        self.check_config_changes()
    
    def check_config_changes(self):
        """Check if config.json has been modified and reload if needed"""
        try:
            if os.path.exists("config.json"):
                current_modified = os.path.getmtime("config.json")
                if current_modified > self.config_last_modified:
                    self.config_last_modified = current_modified
                    old_host = getattr(self, 'server_host', '')
                    old_port = getattr(self, 'server_port', '')
                    old_password = getattr(self, 'rcon_password', '')
                    
                    if self.load_config():
                        self.update_server_info()
                        self.add_output("🔄 Configuration updated from config.json", "success")
                        
                        # Test connection if server details changed
                        if (old_host != self.server_host or 
                            old_port != self.server_port or 
                            old_password != self.rcon_password):
                            self.test_connection()
        except Exception as e:
            print(f"Error checking config changes: {e}")
        
        # Schedule next check in 2 seconds
        self.root.after(2000, self.check_config_changes)
    
    def create_modern_section(self, parent, title, placeholder, command, button_text, row, button_color):
        """Create a modern styled input section with rounded corners"""
        # Section container with rounded appearance
        section_outer = tk.Frame(parent, bg="#161b22", highlightthickness=1, 
                                highlightbackground="#30363d", relief=tk.FLAT)
        section_outer.grid(row=row*2, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        section_outer.grid_columnconfigure(0, weight=1)
        
        section_frame = tk.Frame(section_outer, bg="#0d1117", relief=tk.FLAT)
        section_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Title with better padding
        title_label = tk.Label(
            section_frame,
            text=title,
            font=("Segoe UI", 12, "bold"),
            bg="#0d1117",
            fg="#c9d1d9",
            anchor="w"
        )
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 12))
        
        # Input container with better padding
        input_container = tk.Frame(section_frame, bg="#0d1117")
        input_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))
        input_container.grid_columnconfigure(0, weight=1)
        
        # Entry field with rounded style
        entry_outer = tk.Frame(input_container, bg="#30363d", relief=tk.FLAT, bd=1)
        entry_outer.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        
        entry_frame = tk.Frame(entry_outer, bg="#010409")
        entry_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        entry = tk.Entry(
            entry_frame,
            font=("Segoe UI", 11),
            bg="#010409",
            fg="#c9d1d9",
            relief=tk.FLAT,
            insertbackground="#58a6ff",
            bd=0
        )
        entry.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        entry.insert(0, placeholder)
        entry.config(fg="#6e7681")
        
        # Placeholder behavior
        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(fg="#c9d1d9")
            entry_outer.config(bg="#58a6ff")
        
        def on_focus_out(event):
            if entry.get() == "":
                entry.insert(0, placeholder)
                entry.config(fg="#6e7681")
            entry_outer.config(bg="#30363d")
        
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        entry.bind("<Return>", lambda e: command(entry, placeholder, button))
        
        # Rounded button
        button = tk.Button(
            input_container,
            text=button_text,
            command=lambda: command(entry, placeholder, button),
            bg=button_color,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=28,
            pady=12,
            bd=0,
            activebackground=self.lighten_color(button_color),
            activeforeground="white"
        )
        button.grid(row=0, column=1)
        
        # Store references
        if "Message" in button_text:
            self.message_entry = entry
            self.message_button = button
            self.message_placeholder = placeholder
        else:
            self.command_entry = entry
            self.command_button = button
            self.command_placeholder = placeholder
    
    def create_quick_commands(self, parent):
        """Create quick command buttons with rounded style"""
        quick_outer = tk.Frame(parent, bg="#161b22", highlightthickness=1,
                              highlightbackground="#30363d", relief=tk.FLAT)
        quick_outer.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        
        quick_frame = tk.Frame(quick_outer, bg="#0d1117", relief=tk.FLAT)
        quick_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        title_label = tk.Label(
            quick_frame,
            text="⚡ Quick Commands",
            font=("Segoe UI", 12, "bold"),
            bg="#0d1117",
            fg="#c9d1d9",
            anchor="w"
        )
        title_label.pack(anchor="w", padx=20, pady=(18, 12))
        
        button_container = tk.Frame(quick_frame, bg="#0d1117")
        button_container.pack(fill=tk.X, padx=20, pady=(0, 18))
        
        quick_commands = [
            ("☀️ Day", "time set day"),
            ("🌙 Night", "time set night"),
            ("☁️ Clear", "weather clear"),
            ("🌧️ Rain", "weather rain"),
            ("👥 List", "list")
        ]
        
        for i, (label, cmd) in enumerate(quick_commands):
            btn = tk.Button(
                button_container,
                text=label,
                command=lambda c=cmd: self.quick_command(c),
                bg="#21262d",
                fg="#c9d1d9",
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                relief=tk.FLAT,
                padx=18,
                pady=10,
                bd=0,
                activebackground="#30363d",
                activeforeground="#c9d1d9"
            )
            btn.pack(side=tk.LEFT, padx=(0, 10))
    
    def create_output_section(self, parent):
        """Create output section with rounded corners"""
        output_outer = tk.Frame(parent, bg="#161b22", highlightthickness=1,
                               highlightbackground="#30363d", relief=tk.FLAT)
        output_outer.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(0, 0))
        output_outer.grid_columnconfigure(0, weight=1)
        output_outer.grid_rowconfigure(1, weight=1)
        
        output_frame = tk.Frame(output_outer, bg="#0d1117")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        output_header = tk.Frame(output_frame, bg="#0d1117")
        output_header.grid(row=0, column=0, sticky="ew")
        
        output_label = tk.Label(
            output_header,
            text="📋 Console Output",
            font=("Segoe UI", 12, "bold"),
            bg="#0d1117",
            fg="#c9d1d9",
            anchor="w"
        )
        output_label.pack(side=tk.LEFT, padx=20, pady=(18, 12))
        
        clear_btn = tk.Button(
            output_header,
            text="🗑️ Clear",
            command=self.clear_output,
            bg="#da3633",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=18,
            pady=8,
            bd=0,
            activebackground="#f85149",
            activeforeground="white"
        )
        clear_btn.pack(side=tk.RIGHT, padx=20, pady=(18, 12))
        
        # Text area with padding
        text_container = tk.Frame(output_frame, bg="#0d1117")
        text_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 18))
        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(
            text_container,
            height=12,
            font=("Consolas", 10),
            bg="#010409",
            fg="#c9d1d9",
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            borderwidth=1,
            insertbackground="#58a6ff",
            selectbackground="#1f6feb",
            padx=12,
            pady=10
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")
    
    def quick_command(self, command):
        """Execute a quick command"""
        self.execute_rcon(command, f"Quick: {command}")
    
    def lighten_color(self, color):
        """Lighten a hex color"""
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * 1.3))
        g = min(255, int(g * 1.3))
        b = min(255, int(b * 1.3))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def send_message(self, entry, placeholder, button):
        message = entry.get().strip()
        
        if not message or message == placeholder:
            self.add_output("⚠ Please enter a message", "error")
            return
        
        full_command = f"say {message}"
        self.execute_rcon(full_command, f"Broadcast: {message}", button, "Send Message")
        
        entry.delete(0, tk.END)
    
    def send_command(self, entry, placeholder, button):
        command = entry.get().strip()
        
        if not command or command == placeholder:
            self.add_output("⚠ Please enter a command", "error")
            return
        
        self.execute_rcon(command, f"Command: {command}", button, "Execute Command")
        
        entry.delete(0, tk.END)
    
    def execute_rcon(self, command, description, button=None, button_text=None):
        """Execute RCON command"""
        if not hasattr(self, 'server_host') or not self.server_host:
            self.add_output("⚠ Please configure RCON settings first", "error")
            return
            
        if button:
            button.config(state=tk.DISABLED, text="⏳ Sending...")
        
        self.add_output(f"→ {description}", "info")
        
        thread = threading.Thread(
            target=self._execute_rcon_thread,
            args=(command, button, button_text)
        )
        thread.daemon = True
        thread.start()
    
    def _execute_rcon_thread(self, command, button=None, button_text=None):
        try:
            # mcrcon is always in same directory
            mcrcon_path = "./mcrcon.exe"
            
            if not os.path.exists(mcrcon_path):
                self.root.after(0, lambda: self.add_output(
                    f"✗ mcrcon.exe not found in application directory", "error"
                ))
                if button:
                    self.root.after(0, lambda: button.config(state=tk.NORMAL, text=button_text))
                return
            
            full_command = [
                mcrcon_path,
                "-H", self.server_host,
                "-P", self.server_port,
                "-p", self.rcon_password,
                command
            ]
            
            result = subprocess.run(full_command, capture_output=True, text=True, check=False, **self._subprocess_no_window())
            
            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout else "Command executed"
                self.root.after(0, lambda: self.add_output(f"✓ {output}", "success"))
                self.root.after(0, lambda: self.update_status(True))
            else:
                error = result.stderr.strip() if result.stderr else "Unknown error"
                self.root.after(0, lambda: self.add_output(f"✗ {error}", "error"))
                self.root.after(0, lambda: self.update_status(False))
        
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.add_output("✗ Connection timeout", "error"))
            self.root.after(0, lambda: self.update_status(False))
        except Exception as e:
            self.root.after(0, lambda: self.add_output(f"✗ Error: {str(e)}", "error"))
            self.root.after(0, lambda: self.update_status(False))
        finally:
            if button:
                self.root.after(0, lambda: button.config(state=tk.NORMAL, text=button_text))
    
    def add_output(self, text, msg_type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.output_text.config(state=tk.NORMAL)
        
        self.output_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.output_text.insert(tk.END, f"{text}\n", msg_type)
        
        self.output_text.tag_config("timestamp", foreground="#6e7681")
        self.output_text.tag_config("info", foreground="#58a6ff")
        self.output_text.tag_config("success", foreground="#3fb950")
        self.output_text.tag_config("error", foreground="#f85149")
        self.output_text.tag_config("warning", foreground="#d29922")
        
        self.output_text.config(state=tk.DISABLED)
        self.output_text.see(tk.END)
    
    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.add_output("Console cleared", "info")

def main():
    root = tk.Tk()
    app = RCONGui(root)
    root.mainloop()

if __name__ == "__main__":
    main()