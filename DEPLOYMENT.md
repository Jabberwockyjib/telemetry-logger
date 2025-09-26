# Cartelem Deployment Guide

## Overview

This guide covers deploying Cartelem in various environments, from development to production. The system is designed to be scalable and can run on single machines or distributed across multiple servers.

## Prerequisites

### System Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 10GB+ for database and logs
- **Network**: Stable internet connection for WebSocket streaming

### Software Requirements
- Python 3.9+
- PostgreSQL 12+ (production) or SQLite (development)
- Nginx (recommended for production)
- Systemd (Linux) or equivalent process manager

## Environment Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Application Settings
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cartelem

# GPS Configuration
GPS_PORT=/dev/ttyUSB0
GPS_BAUDRATE=9600
GPS_RATE_HZ=10

# OBD Configuration
OBD_PORT=/dev/ttyUSB1
OBD_BAUDRATE=38400
OBD_RATE_HZ=5

# Meshtastic Configuration
MESHTASTIC_RATE_HZ=1
MESHTASTIC_DEVICE_PATH=/dev/ttyACM0

# Security (Production)
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Performance Tuning
WORKER_PROCESSES=4
MAX_CONNECTIONS=1000
```

### Database Configuration

#### PostgreSQL (Production)
```sql
-- Create database and user
CREATE DATABASE cartelem;
CREATE USER cartelem_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE cartelem TO cartelem_user;

-- Configure connection limits
ALTER USER cartelem_user CONNECTION LIMIT 100;
```

#### SQLite (Development)
```env
DATABASE_URL=sqlite+aiosqlite:///./cartelem.db
```

## Deployment Methods

### 1. Direct Python Deployment

#### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/cartelem.git
cd cartelem

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[prod]"

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head
```

#### Process Management with Systemd

Create `/etc/systemd/system/cartelem.service`:

```ini
[Unit]
Description=Cartelem Telemetry Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=cartelem
Group=cartelem
WorkingDirectory=/opt/cartelem
Environment=PATH=/opt/cartelem/venv/bin
ExecStart=/opt/cartelem/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/cartelem

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cartelem
sudo systemctl start cartelem
sudo systemctl status cartelem
```

### 2. Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash cartelem

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN pip install -e .

# Change ownership
RUN chown -R cartelem:cartelem /app
USER cartelem

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  cartelem:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://cartelem:password@db:5432/cartelem
      - DEBUG=false
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
      - /dev/ttyUSB0:/dev/ttyUSB0  # GPS device
      - /dev/ttyUSB1:/dev/ttyUSB1  # OBD device
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
      - /dev/ttyUSB1:/dev/ttyUSB1
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=cartelem
      - POSTGRES_USER=cartelem
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - cartelem
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### Build and Run
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f cartelem

# Scale application
docker-compose up -d --scale cartelem=3
```

### 3. Kubernetes Deployment

#### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cartelem
```

#### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cartelem-config
  namespace: cartelem
data:
  DATABASE_URL: "postgresql+asyncpg://cartelem:password@postgres:5432/cartelem"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
```

#### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cartelem
  namespace: cartelem
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cartelem
  template:
    metadata:
      labels:
        app: cartelem
    spec:
      containers:
      - name: cartelem
        image: cartelem:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: cartelem-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: cartelem-service
  namespace: cartelem
spec:
  selector:
    app: cartelem
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cartelem-ingress
  namespace: cartelem
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - yourdomain.com
    secretName: cartelem-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: cartelem-service
            port:
              number: 80
```

## Reverse Proxy Configuration

### Nginx Configuration

#### Basic HTTP
```nginx
upstream cartelem {
    server 127.0.0.1:8000;
    # Add more servers for load balancing
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cartelem.crt;
    ssl_certificate_key /etc/nginx/ssl/cartelem.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Static files
    location /static/ {
        alias /opt/cartelem/frontend/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location /api/ {
        proxy_pass http://cartelem;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support
    location /api/v1/ws {
        proxy_pass http://cartelem;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket timeouts
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Frontend
    location / {
        proxy_pass http://cartelem;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Database Setup

### PostgreSQL Production Setup

#### Installation
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
```

#### Configuration
```bash
# Initialize database
sudo postgresql-setup initdb

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create user and database
sudo -u postgres psql
```

```sql
-- Create database and user
CREATE DATABASE cartelem;
CREATE USER cartelem_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE cartelem TO cartelem_user;

-- Configure for performance
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

#### Migration
```bash
# Set database URL
export DATABASE_URL=postgresql+asyncpg://cartelem_user:secure_password@localhost:5432/cartelem

# Run migrations
alembic upgrade head
```

## Monitoring and Logging

### Log Configuration

#### Application Logs
```python
# logging.conf
[loggers]
keys=root,cartelem

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_cartelem]
level=INFO
handlers=fileHandler
qualname=cartelem
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=simpleFormatter
args=('/var/log/cartelem/app.log',)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
```

#### Log Rotation
```bash
# /etc/logrotate.d/cartelem
/var/log/cartelem/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 cartelem cartelem
    postrotate
        systemctl reload cartelem
    endscript
}
```

### Health Checks

#### Application Health
```bash
# Health check endpoint
curl -f http://localhost:8000/api/v1/health

# Database connectivity
curl -f http://localhost:8000/api/v1/health/db

# WebSocket connectivity
curl -f http://localhost:8000/api/v1/health/ws
```

#### System Monitoring
```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Network connections
netstat -tulpn | grep :8000

# Process status
systemctl status cartelem
```

## Security Considerations

### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SSL/TLS Configuration
```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -keyout cartelem.key -out cartelem.crt -days 365 -nodes

# Let's Encrypt (production)
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### User Permissions
```bash
# Create dedicated user
sudo useradd -r -s /bin/false cartelem
sudo mkdir -p /opt/cartelem
sudo chown cartelem:cartelem /opt/cartelem

# Set up log directory
sudo mkdir -p /var/log/cartelem
sudo chown cartelem:cartelem /var/log/cartelem
```

## Performance Tuning

### Application Tuning
```env
# Worker processes
WORKER_PROCESSES=4

# Connection limits
MAX_CONNECTIONS=1000

# Database connection pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Cache settings
CACHE_TTL=300
```

### Database Tuning
```sql
-- PostgreSQL performance settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
```

### System Tuning
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Kernel parameters
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" >> /etc/sysctl.conf
sysctl -p
```

## Backup and Recovery

### Database Backup
```bash
# PostgreSQL backup
pg_dump -h localhost -U cartelem_user -d cartelem > cartelem_backup.sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/opt/backups/cartelem"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U cartelem_user -d cartelem | gzip > "$BACKUP_DIR/cartelem_$DATE.sql.gz"
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### Application Backup
```bash
# Backup application data
tar -czf cartelem_data_$(date +%Y%m%d).tar.gz /opt/cartelem/data/

# Backup configuration
cp /opt/cartelem/.env /opt/backups/cartelem/
cp /etc/nginx/sites-available/cartelem /opt/backups/cartelem/
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U cartelem_user -d cartelem

# Check logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### WebSocket Connection Issues
```bash
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://localhost:8000/api/v1/ws?session_id=1

# Check Nginx WebSocket configuration
sudo nginx -t
```

#### Performance Issues
```bash
# Monitor system resources
htop
iotop
nethogs

# Check application logs
sudo tail -f /var/log/cartelem/app.log

# Database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### Log Analysis
```bash
# Application errors
grep "ERROR" /var/log/cartelem/app.log

# Slow queries
grep "slow query" /var/log/postgresql/postgresql-*.log

# Connection issues
grep "connection" /var/log/cartelem/app.log
```

## Scaling

### Horizontal Scaling
```yaml
# Docker Compose scaling
docker-compose up -d --scale cartelem=3

# Kubernetes scaling
kubectl scale deployment cartelem --replicas=5
```

### Load Balancing
```nginx
upstream cartelem {
    least_conn;
    server 127.0.0.1:8000 weight=3;
    server 127.0.0.1:8001 weight=2;
    server 127.0.0.1:8002 weight=1;
}
```

### Database Scaling
```sql
-- Read replicas
-- Master-slave replication
-- Connection pooling with PgBouncer
```

## Maintenance

### Regular Maintenance Tasks
```bash
# Database maintenance
sudo -u postgres psql -d cartelem -c "VACUUM ANALYZE;"

# Log rotation
sudo logrotate -f /etc/logrotate.d/cartelem

# Security updates
sudo apt update && sudo apt upgrade

# Application updates
git pull origin main
pip install -e .
alembic upgrade head
sudo systemctl restart cartelem
```

### Monitoring Scripts
```bash
#!/bin/bash
# health_check.sh
if ! curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "Cartelem is down!" | mail -s "Alert: Cartelem Down" admin@yourdomain.com
    sudo systemctl restart cartelem
fi
```

This deployment guide provides comprehensive instructions for deploying Cartelem in various environments. Choose the method that best fits your infrastructure and requirements.
