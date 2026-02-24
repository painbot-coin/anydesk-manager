# AnyDesk Global Client-Server System

A global client-server system for managing AnyDesk configuration files across machines worldwide. **Single server controls all clients globally.**

## Features

- **Global Server**: Single server instance manages all clients worldwide
- **Client**: Runs in background, automatically starts on Windows startup
- **Security**: Optional authentication key for secure connections
- **Scalability**: Supports up to 10,000+ concurrent clients
- **Real-time Status**: Check AnyDesk configuration files on all clients
- **Remote Control**: Send commands to move AnyDesk files remotely
- **Auto-reconnect**: Client automatically reconnects if connection is lost
- **Statistics**: Comprehensive server statistics and monitoring
- **Export**: Export all client data to JSON
- **Logging**: Detailed logging for troubleshooting

## Installation

### Global Server Setup

**IMPORTANT**: This is a **single global server** that controls all clients worldwide.

1. **Basic server (no authentication)**:
```bash
python server.py --host 0.0.0.0 --port 8888
```

2. **Secure server with authentication** (recommended):
```bash
python server.py --host 0.0.0.0 --port 8888 --auth-key "your-secret-key-here" --max-clients 10000
```

3. **For internet deployment**, ensure:
   - Firewall allows incoming connections on the server port
   - Router port forwarding is configured (if behind NAT)
   - Server has a static public IP or domain name
   - Consider using a cloud service (AWS, Azure, GCP) for reliability

**Server Configuration:**
- `--host 0.0.0.0` - Listen on all network interfaces (required for internet access)
- `--port 8888` - Server port (default: 8888)
- `--auth-key` - Authentication key (highly recommended for security)
- `--max-clients` - Maximum concurrent clients (default: 10000)

### Client Setup (Worldwide Deployment)

**All clients connect to the same global server. No parameters needed after initial setup!**

1. **First-time setup - Install client to startup**:
```bash
python client.py --add-startup
```

The client will prompt you for:
- Server host/IP (e.g., `anydesk-server.example.com` or `192.168.1.100`)
- Server port (default: `8888`)
- Authentication key (optional, but recommended)

Configuration is saved to `config.json` automatically.

2. **Run the client manually** (no parameters needed):
```bash
python client.py
```

The client automatically reads settings from `config.json`.

3. **To remove from startup**:
```bash
python client.py --remove-startup
```

**Client Features:**
- **No parameters needed** - reads from `config.json` automatically
- Automatically runs in background (no console window) using `pythonw.exe`
- Creates a log file (`client.log`) in the same directory
- Starts automatically on Windows boot
- Auto-reconnects if connection is lost
- Works from anywhere in the world (as long as server is accessible)

**Configuration File (`config.json`):**
The client stores its configuration in `config.json`. You can edit this file directly if needed:
```json
{
    "client": {
        "server_host": "your-server.com",
        "server_port": 8888,
        "auth_key": "your-secret-key"
    }
}
```

## Usage

### Server Commands

Once the global server is running, you can use these commands:

- `list` - List all registered clients (worldwide)
- `stats` - Show server statistics (total clients, connections, uptime, etc.)
- `show <client_id>` - Show detailed information about a specific client
- `status <client_id>` - Request status update from a client
- `move <client_id>` - Request file move operation on a client
- `ping <client_id>` - Ping a client to check if it's alive
- `broadcast <cmd>` - Broadcast command to ALL clients worldwide (status/move/ping)
- `export [filename]` - Export all client data to JSON file
- `quit` - Exit the server

### Example Server Session

```
Server> stats
====================================================================================================
Server Statistics
====================================================================================================
Total Connections: 1523
Active Connections: 847
Total Clients: 1200
Connected Clients: 847
Disconnected Clients: 353
Total Commands Sent: 5432
Failed Commands: 12
Uptime: 72.5 hours
Server Started: 2024-01-15T10:30:00
====================================================================================================

Server> list
====================================================================================================
Total Clients: 1200 | Connected: 847 | Disconnected: 353
====================================================================================================
Client ID                       IP Address        Hostname            Username        Status      
====================================================================================================
DESKTOP-ABC_John                192.168.1.100     DESKTOP-ABC         John            Connected   
LAPTOP-XYZ_Jane                 203.0.113.45      LAPTOP-XYZ          Jane            Connected   
OFFICE-PC_Mike                  198.51.100.12     OFFICE-PC           Mike            Connected   
...
====================================================================================================

Server> show DESKTOP-ABC_John
[Shows detailed client information including IP address, first seen, last seen, etc.]

Server> move DESKTOP-ABC_John
Move files command sent to DESKTOP-ABC_John

Server> broadcast move
Broadcast move to 847 clients

Server> export clients_backup.json
Exported 1200 clients to clients_backup.json
```

## Files

- `client.py` - Client application (runs in background)
- `server.py` - Server application (monitors clients)
- `anydesk.py` - Original standalone script (for reference)
- `config.json` - Configuration file (optional)
- `requirements.txt` - Python dependencies (none required)

## How It Works

1. **Client** connects to server and registers itself
2. **Client** sends periodic heartbeats with system and AnyDesk status
3. **Server** maintains a list of all connected clients
4. **Server** can send commands to clients:
   - `get_status` - Request current status
   - `move_files` - Move AnyDesk configuration files
   - `ping` - Check if client is alive
   - `shutdown` - Shutdown client

## Global Deployment Architecture

```
                    ┌─────────────────────┐
                    │  Global Server       │
                    │  (Single Instance)  │
                    │  IP: x.x.x.x:8888   │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
        ┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
        │ Client (USA) │ │ Client (EU)│ │ Client (Asia)│
        │ Auto-start   │ │ Auto-start │ │ Auto-start  │
        └──────────────┘ └────────────┘ └─────────────┘
```

**Key Points:**
- **One server** controls **all clients worldwide**
- Clients from any location connect to the same server
- Server tracks IP addresses and connection status
- All commands can be broadcast to all clients simultaneously

## Windows Startup Integration

The client automatically adds itself to Windows startup registry when you run:
```bash
python client.py --add-startup
```

This adds an entry to: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`

**No parameters needed** - the client reads from `config.json` automatically.

The client will:
- Run using `pythonw.exe` (no console window)
- Read configuration from `config.json` (no command-line parameters)
- Log all activity to `client.log` in the script directory
- Automatically reconnect if the server is unavailable
- Work from anywhere in the world

## Network Configuration for Global Deployment

### Server Requirements:
- **Public IP address** or **domain name** (e.g., `anydesk-server.example.com`)
- **Firewall**: Allow incoming TCP connections on port 8888 (or your chosen port)
- **Port forwarding**: If behind NAT/router, forward port 8888 to server
- **Cloud deployment recommended**: AWS EC2, Azure VM, Google Cloud, etc.
- **Static IP or dynamic DNS**: Clients need a stable address to connect

### Client Requirements:
- **Internet connection** to reach the global server
- **Firewall**: Allow outbound TCP connections to server port
- **No port forwarding needed** (clients initiate connections)

### Security Recommendations:
1. **Always use authentication** (`--auth-key`) for production
2. **Use firewall rules** to restrict server access if needed
3. **Monitor server logs** regularly (`logs/server_YYYYMMDD.log`)
4. **Keep server updated** and secure
5. **Use HTTPS/TLS** in production (requires additional setup)

## Troubleshooting

- **Client can't connect**: Check server IP/port and firewall settings
- **Client not starting on boot**: Run `python client.py --add-startup` again
- **Connection lost**: Client automatically reconnects every 5 seconds

