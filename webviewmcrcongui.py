import webview
import subprocess
import sys
import os
import json

class RCONApi:
    def __init__(self):
        self.config_loaded = False
        self.connection_status = False
        self.config_file = "config.json"
        self.load_config()
    
    def _subprocess_no_window(self):
        """Return kwargs to prevent console window on Windows"""
        if sys.platform.startswith("win"):
            return {"creationflags": subprocess.CREATE_NO_WINDOW}
        return {}
    
    def load_config(self):
        """Load configuration from config.json"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                self.server_host = config_data.get('server_ip', '')
                self.server_port = config_data.get('port', '')
                self.rcon_password = config_data.get('password', '')
                self.config_loaded = True
                return True
            else:
                self.server_host = ""
                self.server_port = ""
                self.rcon_password = ""
                self.config_loaded = False
                return False
        except Exception as e:
            print(f"Error loading config: {e}")
            return False
    
    def get_config(self):
        """Get current configuration"""
        return {
            'server_ip': self.server_host,
            'port': self.server_port,
            'password': self.rcon_password,
            'config_loaded': self.config_loaded
        }
    
    def save_config(self, server_ip, port, password):
        """Save configuration to config.json"""
        try:
            config_content = {
                "server_ip": server_ip,
                "port": port,
                "password": password
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_content, f, indent=4)
            
            self.server_host = server_ip
            self.server_port = port
            self.rcon_password = password
            self.config_loaded = True
            
            return {"success": True, "message": "Configuration saved successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to save configuration: {str(e)}"}
    
    def test_connection(self):
        """Test connection to RCON server"""
        if not self.config_loaded:
            return {"success": False, "message": "Configuration not set"}
        
        try:
            mcrcon_path = "./mcrcon.exe"
            
            if not os.path.exists(mcrcon_path):
                return {
                    "success": False,
                    "message": "mcrcon.exe not found in application directory"
                }
            
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
                self.connection_status = True
                return {"success": True, "message": "Connected to server successfully"}
            else:
                self.connection_status = False
                error_msg = result.stderr.strip() if result.stderr.strip() else "Connection failed"
                return {"success": False, "message": error_msg}
        
        except subprocess.TimeoutExpired:
            self.connection_status = False
            return {"success": False, "message": "Connection timeout"}
        except Exception as e:
            self.connection_status = False
            return {"success": False, "message": f"Connection error: {str(e)}"}
    
    def send_message(self, message):
        """Send broadcast message to server"""
        if not message.strip():
            return {"success": False, "message": "Please enter a message"}
        
        command = f"say {message}"
        return self.execute_command(command)
    
    def execute_command(self, command):
        """Execute RCON command"""
        if not self.config_loaded:
            return {"success": False, "message": "Please configure RCON settings first"}
        
        try:
            mcrcon_path = "./mcrcon.exe"
            
            if not os.path.exists(mcrcon_path):
                return {
                    "success": False,
                    "message": "mcrcon.exe not found in application directory"
                }
            
            full_command = [
                mcrcon_path,
                "-H", self.server_host,
                "-P", self.server_port,
                "-p", self.rcon_password,
                command
            ]
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=5,
                **self._subprocess_no_window()
            )
            
            if result.returncode == 0:
                self.connection_status = True
                output = result.stdout.strip() if result.stdout.strip() else "Command executed"
                return {"success": True, "message": output}
            else:
                self.connection_status = False
                error = result.stderr.strip() if result.stderr else "Unknown error"
                return {"success": False, "message": error}
        
        except subprocess.TimeoutExpired:
            self.connection_status = False
            return {"success": False, "message": "Connection timeout"}
        except Exception as e:
            self.connection_status = False
            return {"success": False, "message": f"Error: {str(e)}"}

def get_html():
    """Return the HTML interface"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minecraft RCON Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-title h1 {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 4px;
            color: white;
        }
        
        .header-title p {
            font-size: 16px;
            color: #93c5fd;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(255, 255, 255, 0.1);
            padding: 12px 24px;
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #6b7280;
            animation: pulse 2s infinite;
        }
        
        .status-dot.connected {
            background: #10b981;
        }
        
        .status-dot.disconnected {
            background: #ef4444;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-text {
            font-weight: 600;
            color: white;
        }
        
        .server-info {
            font-size: 14px;
            color: #93c5fd;
            margin-left: 12px;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }
        
        .card {
            background: rgba(30, 41, 59, 0.5);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(51, 65, 85, 0.5);
            backdrop-filter: blur(10px);
        }
        
        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .input-group {
            display: flex;
            gap: 12px;
            margin-bottom: 0;
        }
        
        .input-field {
            flex: 1;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px 16px;
            color: #e2e8f0;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .input-field:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        .input-field::placeholder {
            color: #64748b;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            white-space: nowrap;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: white;
        }
        
        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        }
        
        .quick-commands {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
            margin-top: 16px;
        }
        
        .quick-btn {
            padding: 16px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s;
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }
        
        .quick-btn:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        }
        
        .quick-btn.day {
            background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
        }
        
        .quick-btn.night {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        }
        
        .quick-btn.clear {
            background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
        }
        
        .quick-btn.rain {
            background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
        }
        
        .quick-btn.list {
            background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%);
        }
        
        .quick-icon {
            font-size: 24px;
        }
        
        .console {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 12px;
            padding: 16px;
            max-height: 600px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        
        .console-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .btn-danger {
            background: #dc2626;
            color: white;
            padding: 8px 16px;
            font-size: 12px;
        }
        
        .btn-danger:hover {
            background: #ef4444;
        }
        
        .console-line {
            display: flex;
            gap: 12px;
            margin-bottom: 8px;
            padding: 8px;
            border-radius: 6px;
            background: rgba(15, 23, 42, 0.3);
        }
        
        .console-time {
            color: #64748b;
            font-size: 11px;
        }
        
        .console-icon {
            width: 16px;
        }
        
        .console-text {
            flex: 1;
            word-wrap: break-word;
        }
        
        .console-text.success {
            color: #10b981;
        }
        
        .console-text.error {
            color: #ef4444;
        }
        
        .console-text.info {
            color: #3b82f6;
        }
        
        .console-text.command {
            color: #60a5fa;
        }
        
        .console-text.warning {
            color: #f59e0b;
        }
        
        .footer {
            text-align: center;
            margin-top: 24px;
            color: #64748b;
            font-size: 14px;
        }
        
        .footer a {
            color: #3b82f6;
            text-decoration: none;
            font-weight: 600;
        }
        
        .footer a:hover {
            color: #60a5fa;
        }
        
        .console::-webkit-scrollbar {
            width: 8px;
        }
        
        .console::-webkit-scrollbar-track {
            background: rgba(15, 23, 42, 0.5);
            border-radius: 4px;
        }
        
        .console::-webkit-scrollbar-thumb {
            background: #334155;
            border-radius: 4px;
        }
        
        .console::-webkit-scrollbar-thumb:hover {
            background: #475569;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: #1e293b;
            border-radius: 16px;
            padding: 32px;
            max-width: 500px;
            width: 90%;
            border: 1px solid #334155;
        }
        
        .modal-title {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 24px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #cbd5e1;
        }
        
        .modal-buttons {
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }
        
        .btn-secondary {
            background: #334155;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #475569;
        }
        
        .config-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            z-index: 100;
        }
        
        .config-btn:hover {
            background: #2563eb;
        }
        
        @media (max-width: 1200px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .quick-commands {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column;
                gap: 16px;
            }
            
            .quick-commands {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <button class="config-btn" onclick="openConfigModal()">⚙️ Configuration</button>
    
    <div class="container">
        <div class="header">
            <div class="header-content">
                <div class="header-title">
                    <h1>🎮 Minecraft RCON</h1>
                    <p>Control Panel</p>
                </div>
                <div class="status-badge">
                    <div class="status-dot" id="statusDot"></div>
                    <div>
                        <div class="status-text" id="statusText">Checking...</div>
                        <div class="server-info" id="serverInfo"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="main-grid">
            <div>
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-title">📤 Send Message to Server</div>
                    <div class="input-group">
                        <input 
                            type="text" 
                            class="input-field" 
                            id="messageInput" 
                            placeholder="Type your broadcast message..."
                            onkeypress="if(event.key==='Enter') sendMessage()"
                        >
                        <button class="btn btn-primary" onclick="sendMessage()">Send Message</button>
                    </div>
                </div>
                
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-title">💻 Execute Server Command</div>
                    <div class="input-group">
                        <input 
                            type="text" 
                            class="input-field" 
                            id="commandInput" 
                            placeholder="e.g., time set day, weather clear, gamemode creative"
                            onkeypress="if(event.key==='Enter') executeCommand()"
                        >
                        <button class="btn btn-success" onclick="executeCommand()">Execute Command</button>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">⚡ Quick Commands</div>
                    <div class="quick-commands">
                        <button class="quick-btn day" onclick="quickCommand('time set day', 'Day')">
                            <span class="quick-icon">☀️</span>
                            <span>Day</span>
                        </button>
                        <button class="quick-btn night" onclick="quickCommand('time set night', 'Night')">
                            <span class="quick-icon">🌙</span>
                            <span>Night</span>
                        </button>
                        <button class="quick-btn clear" onclick="quickCommand('weather clear', 'Clear')">
                            <span class="quick-icon">☁️</span>
                            <span>Clear</span>
                        </button>
                        <button class="quick-btn rain" onclick="quickCommand('weather rain', 'Rain')">
                            <span class="quick-icon">🌧️</span>
                            <span>Rain</span>
                        </button>
                        <button class="quick-btn list" onclick="quickCommand('list', 'List')">
                            <span class="quick-icon">📋</span>
                            <span>List</span>
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="console-header">
                    <div class="card-title">💻 Console Output</div>
                    <button class="btn btn-danger" onclick="clearConsole()">🗑️ Clear</button>
                </div>
                <div class="console" id="console"></div>
            </div>
        </div>
        

    </div>
    
    <div class="modal" id="configModal">
        <div class="modal-content">
            <div class="modal-title">⚙️ RCON Configuration</div>
            <div class="form-group">
                <label class="form-label">Server IP/Domain</label>
                <input type="text" class="input-field" id="configServerIp" placeholder="e.g., localhost or 192.168.1.100">
            </div>
            <div class="form-group">
                <label class="form-label">RCON Port</label>
                <input type="text" class="input-field" id="configPort" placeholder="e.g., 25575">
            </div>
            <div class="form-group">
                <label class="form-label">RCON Password</label>
                <input type="password" class="input-field" id="configPassword" placeholder="Enter RCON password">
            </div>
            <div class="modal-buttons">
                <button class="btn btn-primary" onclick="saveConfig()" style="flex: 1;">💾 Save Configuration</button>
                <button class="btn btn-secondary" onclick="closeConfigModal()">Cancel</button>
            </div>
        </div>
    </div>
    
    <script>
        let consoleMessages = [];
        
        function addConsoleMessage(text, type = 'info') {
            const now = new Date();
            const time = now.toTimeString().split(' ')[0];
            
            const icons = {
                success: '✓',
                error: '✗',
                command: '>',
                info: '•',
                warning: '⚠'
            };
            
            const message = {
                time: time,
                type: type,
                text: text,
                icon: icons[type] || icons.info
            };
            
            consoleMessages.push(message);
            renderConsole();
        }
        
        function renderConsole() {
            const consoleEl = document.getElementById('console');
            consoleEl.innerHTML = consoleMessages.map(msg => `
                <div class="console-line">
                    <span class="console-time">[${msg.time}]</span>
                    <span class="console-icon">${msg.icon}</span>
                    <span class="console-text ${msg.type}">${msg.text}</span>
                </div>
            `).join('');
            consoleEl.scrollTop = consoleEl.scrollHeight;
        }
        
        function clearConsole() {
            consoleMessages = [];
            renderConsole();
            addConsoleMessage('Console cleared', 'info');
        }
        
        function updateStatus(connected) {
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            
            if (connected) {
                statusDot.className = 'status-dot connected';
                statusText.textContent = 'Connected';
            } else {
                statusDot.className = 'status-dot disconnected';
                statusText.textContent = 'Disconnected';
            }
        }
        
        async function loadConfig() {
            try {
                const config = await pywebview.api.get_config();
                document.getElementById('serverInfo').textContent = 
                    config.server_ip && config.port ? `${config.server_ip}:${config.port}` : 'Not configured';
                
                if (config.config_loaded) {
                    addConsoleMessage('✓ RCON GUI initialized successfully', 'success');
                    addConsoleMessage('✓ Configuration loaded from config.json', 'success');
                    testConnection();
                } else {
                    addConsoleMessage('⚠ Configuration not found', 'warning');
                    addConsoleMessage('⚠ Please set up your RCON configuration', 'warning');
                    setTimeout(() => openConfigModal(), 500);
                }
            } catch (error) {
                addConsoleMessage(`✗ Error loading config: ${error}`, 'error');
            }
        }
        
        async function testConnection() {
            addConsoleMessage('🔄 Testing connection...', 'info');
            try {
                const result = await pywebview.api.test_connection();
                if (result.success) {
                    updateStatus(true);
                    addConsoleMessage(`✓ ${result.message}`, 'success');
                } else {
                    updateStatus(false);
                    addConsoleMessage(`✗ ${result.message}`, 'error');
                }
            } catch (error) {
                updateStatus(false);
                addConsoleMessage(`✗ Connection error: ${error}`, 'error');
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) {
                addConsoleMessage('⚠ Please enter a message', 'warning');
                return;
            }
            
            addConsoleMessage(`→ Broadcasting: "${message}"`, 'command');
            
            try {
                const result = await pywebview.api.send_message(message);
                if (result.success) {
                    updateStatus(true);
                    addConsoleMessage(`✓ ${result.message}`, 'success');
                    input.value = '';
                } else {
                    updateStatus(false);
                    addConsoleMessage(`✗ ${result.message}`, 'error');
                }
            } catch (error) {
                addConsoleMessage(`✗ Error: ${error}`, 'error');
            }
        }
        
        async function executeCommand() {
            const input = document.getElementById('commandInput');
            const command = input.value.trim();
            
            if (!command) {
                addConsoleMessage('⚠ Please enter a command', 'warning');
                return;
            }
            
            addConsoleMessage(`→ Command: ${command}`, 'command');
            
            try {
                const result = await pywebview.api.execute_command(command);
                if (result.success) {
                    updateStatus(true);
                    addConsoleMessage(`✓ ${result.message}`, 'success');
                    input.value = '';
                } else {
                    updateStatus(false);
                    addConsoleMessage(`✗ ${result.message}`, 'error');
                }
            } catch (error) {
                addConsoleMessage(`✗ Error: ${error}`, 'error');
            }
        }
        
        async function quickCommand(command, label) {
            addConsoleMessage(`→ ${label}: ${command}`, 'command');
            
            try {
                const result = await pywebview.api.execute_command(command);
                if (result.success) {
                    updateStatus(true);
                    addConsoleMessage(`✓ ${result.message}`, 'success');
                } else {
                    updateStatus(false);
                    addConsoleMessage(`✗ ${result.message}`, 'error');
                }
            } catch (error) {
                addConsoleMessage(`✗ Error: ${error}`, 'error');
            }
        }
        
        function openConfigModal() {
            pywebview.api.get_config().then(config => {
                document.getElementById('configServerIp').value = config.server_ip || '';
                document.getElementById('configPort').value = config.port || '';
                document.getElementById('configPassword').value = config.password || '';
                document.getElementById('configModal').classList.add('active');
            });
        }
        
        function closeConfigModal() {
            document.getElementById('configModal').classList.remove('active');
        }
        
        async function saveConfig() {
            const serverIp = document.getElementById('configServerIp').value.trim();
            const port = document.getElementById('configPort').value.trim();
            const password = document.getElementById('configPassword').value.trim();
            
            if (!serverIp || !port || !password) {
                addConsoleMessage('⚠ Please fill in all fields', 'warning');
                return;
            }
            
            try {
                const result = await pywebview.api.save_config(serverIp, port, password);
                if (result.success) {
                    addConsoleMessage(`✓ ${result.message}`, 'success');
                    closeConfigModal();
                    loadConfig();
                } else {
                    addConsoleMessage(`✗ ${result.message}`, 'error');
                }
            } catch (error) {
                addConsoleMessage(`✗ Error saving config: ${error}`, 'error');
            }
        }
        
        window.addEventListener('pywebviewready', function() {
            loadConfig();
        });
    </script>
</body>
</html>
"""

def main():
    api = RCONApi()
    html_content = get_html()
    
    window = webview.create_window(
        'Minecraft RCON Control Panel',
        html=html_content,
        js_api=api,
        width=1400,
        height=900,
        resizable=True,
        background_color='#0f172a'
    )

    # Add footer with clickable author credit
    def add_footer():
        import webview
        footer_html = '<div style="position:fixed;bottom:0;width:100%;background:#222;color:#fff;text-align:center;padding:8px 0;font-size:14px;z-index:9999;">Design by <a href="https://h190k.com" target="_blank" style="color:#4fc3f7;text-decoration:underline;">h190k</a></div>'
        window.evaluate_js(f"document.body.insertAdjacentHTML('beforeend', `{footer_html}`);")
    window.events.loaded += add_footer

    webview.start(gui='edgechromium',debug=False)

if __name__ == "__main__":
    main()
