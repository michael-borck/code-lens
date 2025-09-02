# CodeLens Deployment Scripts

This directory contains automated deployment scripts for CodeLens.

## 🚀 Quick Start

```bash
# Docker deployment (recommended)
./docker_deploy.sh dev     # Development
./docker_deploy.sh prod    # Production

# Server installation
sudo ./server_install.sh production

# Server updates
sudo ./server_update.sh
```

## 📁 Scripts Overview

### `docker_deploy.sh`
**Purpose**: Deploy CodeLens using Docker containers
**Usage**: `./docker_deploy.sh [dev|prod]`

**Features**:
- ✅ Automated Docker Compose deployment
- ✅ Environment-specific configurations
- ✅ Health checks and validation
- ✅ Database migration handling
- ✅ Production SSL support

**Requirements**:
- Docker and Docker Compose installed
- `.env.prod` file for production deployments

### `server_install.sh`
**Purpose**: Install CodeLens directly on Ubuntu/Debian servers
**Usage**: `sudo ./server_install.sh [environment]`

**Features**:
- ✅ Complete system setup (Python, PostgreSQL, Redis, Nginx)
- ✅ Service user creation and security hardening
- ✅ Systemd service configuration
- ✅ Nginx reverse proxy setup
- ✅ Database initialization
- ✅ Automatic startup configuration

**Requirements**:
- Ubuntu 20.04+ or Debian 11+
- Root access (sudo)
- Internet connection

### `server_update.sh`
**Purpose**: Update existing server installations
**Usage**: `sudo ./server_update.sh`

**Features**:
- ✅ Automatic backup creation
- ✅ Git pull and dependency updates
- ✅ Database migrations
- ✅ Service restart
- ✅ Rollback on failure

**Requirements**:
- Existing CodeLens server installation
- Root access (sudo)

## 🔧 Configuration

### Environment Files
Create appropriate environment files before deployment:

```bash
# Development
cp ../.env.example .env

# Production
cp ../.env.example .env.prod
# Edit .env.prod with production settings
```

### Key Settings for Production
```bash
# Security
CODELENS_SECRET_KEY=$(openssl rand -hex 32)
CODELENS_ENV=production
CODELENS_LOG_LEVEL=warning

# Database
CODELENS_DATABASE__URL=postgresql+asyncpg://codelens:secure_password@localhost:5432/codelens

# Performance
CODELENS_WORKERS=4
```

## 🐳 Docker Deployment Details

### Development Deployment
```bash
./docker_deploy.sh dev
```
- Uses `docker-compose.yml`
- SQLite database
- Direct port access (8000)
- Debug logging enabled

### Production Deployment
```bash
./docker_deploy.sh prod
```
- Uses `docker-compose.prod.yml`
- PostgreSQL database
- Redis caching
- Nginx reverse proxy
- SSL-ready configuration
- Resource limits applied

### Docker Services
- **codelens-app**: Main application container
- **codelens-db**: PostgreSQL database (production)
- **codelens-redis**: Redis cache (production)
- **nginx**: Reverse proxy (production)

## 🖥️ Server Installation Details

### System Dependencies
The installation script installs:
- Python 3.11 and development tools
- PostgreSQL database server
- Redis server
- Nginx web server
- Docker for code execution
- Build tools and utilities

### Directory Structure
```
/opt/codelens/              # Application directory
├── .venv/                  # Python virtual environment
├── codelens/               # Application code
├── logs/                   # Log files
├── data/                   # Application data
├── uploads/                # File uploads
└── .env                    # Environment configuration
```

### Services Created
- **codelens.service**: Main application service
- **nginx**: Reverse proxy
- **postgresql**: Database service
- **redis**: Cache service (optional)

## 🔍 Verification Steps

### Docker Deployment Verification
```bash
# Check container status
docker-compose ps

# Test health endpoint
curl http://localhost:8000/health  # Dev
curl http://localhost/health       # Prod

# View logs
docker-compose logs -f codelens-app
```

### Server Installation Verification
```bash
# Check service status
systemctl status codelens

# Test health endpoint
curl http://localhost/health

# View logs
journalctl -u codelens -f
```

## 🛠️ Maintenance Commands

### Docker Maintenance
```bash
# Update containers
docker-compose pull && docker-compose up -d

# Restart services
docker-compose restart

# View resource usage
docker stats

# Backup data
docker run --rm -v codelens_postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/db_backup.tar.gz /data
```

### Server Maintenance
```bash
# Update application
sudo ./server_update.sh

# Restart services
sudo systemctl restart codelens nginx

# Monitor resources
htop

# Backup database
pg_dump codelens > backup_$(date +%Y%m%d).sql
```

## 🔒 Security Considerations

### Docker Security
- Containers run as non-root users
- Docker socket access is controlled
- Network isolation between services
- Resource limits prevent abuse

### Server Security
- Dedicated service user (`codelens`)
- Nginx reverse proxy with rate limiting
- Firewall configuration recommendations
- SSL/TLS encryption support

### Production Hardening
```bash
# Generate secure secrets
CODELENS_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# Configure SSL certificates
# Place certificates in ./ssl/ directory
# Update nginx.conf with your domain
```

## 📊 Monitoring

### Health Checks
All deployment methods include health check endpoints:
- `/health` - Application health
- `/health/db` - Database connectivity
- `/health/docker` - Docker daemon status

### Log Locations
- **Docker**: `docker-compose logs`
- **Server**: `/var/log/codelens/` and `journalctl -u codelens`
- **Nginx**: `/var/log/nginx/`

## 🆘 Troubleshooting

### Common Issues
1. **Permission Denied**: Ensure scripts are executable (`chmod +x *.sh`)
2. **Docker Not Found**: Install Docker and Docker Compose
3. **Port Already In Use**: Stop conflicting services
4. **Database Connection**: Check credentials and service status

### Debug Mode
```bash
# Enable verbose output
set -x

# Check specific service
docker-compose logs codelens-app
systemctl status codelens -l
```

### Rollback Procedures
- **Docker**: `docker-compose down && git checkout previous-version && ./docker_deploy.sh`
- **Server**: Automatic backup restoration in `server_update.sh`

For more detailed troubleshooting, see [DEPLOYMENT.md](../DEPLOYMENT.md).