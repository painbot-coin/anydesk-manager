# Global Server Deployment Guide

This guide helps you deploy the AnyDesk Global Server to control clients worldwide.

## Server Deployment Options

### Option 1: Cloud Server (Recommended)

#### AWS EC2
1. Launch an EC2 instance (Ubuntu/Windows Server)
2. Configure security group to allow TCP port 8888
3. Install Python 3.7+
4. Upload server files
5. Run: `python server.py --host 0.0.0.0 --port 8888 --auth-key "your-key"`

#### Azure VM
1. Create a Virtual Machine
2. Configure Network Security Group (allow port 8888)
3. Install Python
4. Run server with public IP

#### Google Cloud Platform
1. Create Compute Engine instance
2. Configure firewall rules (allow port 8888)
3. Install Python
4. Run server

### Option 2: VPS/Dedicated Server

1. Rent a VPS with public IP
2. Install Python 3.7+
3. Configure firewall
4. Run server

### Option 3: Home/Office Server (Not Recommended for Production)

1. Configure router port forwarding (port 8888 → server IP)
2. Use dynamic DNS service (e.g., No-IP, DuckDNS)
3. Configure firewall
4. Run server

## Server Setup Steps

### 1. Install Python
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# Windows
# Download from python.org
```

### 2. Upload Server Files
Upload `server.py` to your server

### 3. Configure Firewall

**Ubuntu/Debian (UFW):**
```bash
sudo ufw allow 8888/tcp
sudo ufw enable
```

**Windows Firewall:**
```powershell
New-NetFirewallRule -DisplayName "AnyDesk Server" -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow
```

**Cloud Providers:**
- AWS: Security Groups
- Azure: Network Security Groups
- GCP: Firewall Rules

### 4. Start Server

**With authentication (recommended):**
```bash
python3 server.py --host 0.0.0.0 --port 8888 --auth-key "your-secure-key-here" --max-clients 10000
```

**Without authentication (testing only):**
```bash
python3 server.py --host 0.0.0.0 --port 8888
```

### 5. Run as Service (Linux)

Create systemd service file `/etc/systemd/system/anydesk-server.service`:

```ini
[Unit]
Description=AnyDesk Global Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/server
ExecStart=/usr/bin/python3 /path/to/server/server.py --host 0.0.0.0 --port 8888 --auth-key "your-key" --no-interactive
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable anydesk-server
sudo systemctl start anydesk-server
sudo systemctl status anydesk-server
```

### 6. Run as Windows Service

Use NSSM (Non-Sucking Service Manager) or Task Scheduler to run as service.

## Client Deployment

### Deploy to Multiple Machines

1. **Create deployment package:**
   - `client.py`
   - Installation script

2. **For each client, run:**
```bash
python client.py --add-startup --server-host your-server.com --server-port 8888 --auth-key "your-key"
```

3. **Verify connection:**
   - Check server logs
   - Run `list` command on server

### Bulk Deployment Script

Create a script to deploy to multiple machines via network:

```bash
# deploy_clients.sh
for host in client1 client2 client3; do
    scp client.py user@$host:/path/
    ssh user@$host "python /path/client.py --add-startup --server-host your-server.com --auth-key 'your-key'"
done
```

## Monitoring

### Server Logs
Logs are saved to `logs/server_YYYYMMDD.log`

### Check Server Status
```bash
# On server
python server.py
Server> stats
```

### Monitor Connections
```bash
# Linux
netstat -an | grep 8888
ss -tuln | grep 8888

# Windows
netstat -an | findstr 8888
```

## Security Best Practices

1. **Use strong authentication key**
   - Minimum 32 characters
   - Mix of letters, numbers, symbols
   - Store securely

2. **Firewall Rules**
   - Only allow port 8888 from trusted IPs (if possible)
   - Or use VPN for server access

3. **Regular Updates**
   - Keep server software updated
   - Monitor logs for suspicious activity

4. **Backup**
   - Regularly export client data: `export clients_backup.json`
   - Backup server configuration

5. **Monitoring**
   - Set up alerts for server downtime
   - Monitor connection counts
   - Check for failed authentication attempts

## Troubleshooting

### Clients Can't Connect

1. **Check server is running:**
   ```bash
   netstat -an | grep 8888
   ```

2. **Check firewall:**
   ```bash
   # Test from client
   telnet server-ip 8888
   ```

3. **Check server logs:**
   ```bash
   tail -f logs/server_*.log
   ```

4. **Verify server host/port:**
   - Server must use `--host 0.0.0.0` (not localhost)
   - Port must match client configuration

### High Connection Count

- Monitor with `stats` command
- Check for connection leaks
- Adjust `--max-clients` if needed

### Authentication Failures

- Verify auth key matches on server and clients
- Check logs for failed attempts
- Ensure key is properly quoted in commands

## Performance Tuning

- **Increase max clients:** `--max-clients 20000`
- **Adjust socket timeouts** in code for your network
- **Use load balancer** for very high scale (requires code changes)
- **Monitor system resources** (CPU, memory, network)

## Backup and Recovery

### Regular Backups
```bash
# Export client data daily
python server.py
Server> export clients_$(date +%Y%m%d).json
```

### Recovery
1. Restore server
2. Import client data (if needed)
3. Clients will automatically reconnect

