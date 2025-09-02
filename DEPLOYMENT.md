# CodeLens Deployment Guide

This guide covers multiple deployment options for the CodeLens automated code analysis and grading system.

## 🚀 Quick Start

### Docker Deployment (Recommended)
```bash
# Development
./scripts/deploy/docker_deploy.sh dev

# Production
./scripts/deploy/docker_deploy.sh prod
```

### Server Installation
```bash
# Install on Ubuntu/Debian server
sudo ./scripts/deploy/server_install.sh production
```

## 📋 Prerequisites

### System Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB+ available space
- **OS**: Ubuntu 20.04+, Debian 11+, or Docker-compatible system

### Required Software
- Python 3.10+ (server deployment)
- Docker & Docker Compose (container deployment)
- PostgreSQL 13+ (production)
- Redis 6+ (optional, for caching)

## 🐳 Docker Deployment

### Development Setup
```bash
# Clone repository
git clone https://github.com/michael-borck/code-lens.git
cd code-lens

# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f
```

**Access**: http://localhost:8000

### Production Setup
```bash
# Configure environment
cp .env.example .env.prod
# Edit .env.prod with your settings

# Deploy with production configuration
./scripts/deploy/docker_deploy.sh prod
```

**Features**:
- PostgreSQL database
- Redis caching
- Nginx reverse proxy
- SSL support (configure certificates)
- Resource limits
- Health checks

### Docker Commands
```bash
# View status
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Update application
docker-compose pull && docker-compose up -d

# Stop services
docker-compose down

# Reset everything (⚠️ destroys data)
docker-compose down -v
```

## 🖥️ Server Deployment

### Automated Installation
```bash
# Download and run installation script
curl -sSL https://raw.githubusercontent.com/michael-borck/code-lens/main/scripts/deploy/server_install.sh | sudo bash -s production
```

### Manual Installation Steps

1. **System Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv postgresql redis-server nginx supervisor docker.io
```

2. **Create Service User**
```bash
sudo useradd -r -m -s /bin/bash codelens
sudo usermod -aG docker codelens
```

3. **Application Setup**
```bash
# Switch to service user
sudo -u codelens -i

# Install in /opt/codelens
cd /opt/codelens
git clone https://github.com/michael-borck/code-lens.git .

# Setup Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install uv
uv sync
```

4. **Database Setup**
```bash
# Create PostgreSQL database
sudo -u postgres createuser codelens
sudo -u postgres createdb -O codelens codelens
sudo -u postgres psql -c "ALTER USER codelens WITH PASSWORD 'secure_password';"
```

5. **Configure Environment**
```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your settings
```

6. **System Service**
```bash
# Create systemd service (see server_install.sh for full configuration)
sudo systemctl enable codelens
sudo systemctl start codelens
```

### Server Management
```bash
# Service control
sudo systemctl start codelens
sudo systemctl stop codelens
sudo systemctl restart codelens
sudo systemctl status codelens

# View logs
sudo journalctl -u codelens -f

# Update application
sudo ./scripts/deploy/server_update.sh
```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Basic settings
CODELENS_ENV=production
CODELENS_LOG_LEVEL=info
CODELENS_HOST=0.0.0.0
CODELENS_PORT=8000

# Database
CODELENS_DATABASE__URL=postgresql+asyncpg://user:pass@localhost/codelens

# Security
CODELENS_SECRET_KEY=your-secret-key
CODELENS_DOCKER_ENABLED=true

# Analysis
CODELENS_ANALYZER__RUFF_ENABLED=true
CODELENS_ANALYZER__MYPY_ENABLED=true
CODELENS_SIMILARITY__ENABLED=true
```

### Production Recommendations

**Security**:
- Generate strong `SECRET_KEY`: `openssl rand -hex 32`
- Use PostgreSQL for production database
- Enable HTTPS with SSL certificates
- Configure firewall rules
- Regular security updates

**Performance**:
- Use multiple workers: `CODELENS_WORKERS=4`
- Enable Redis caching
- Configure resource limits
- Monitor system resources

**Monitoring**:
- Set up log rotation
- Configure health checks
- Monitor database performance
- Track analysis metrics

## 🔒 Security Configuration

### SSL/TLS Setup
```bash
# Generate self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem

# Production: Use Let's Encrypt or your CA certificates
```

### Firewall Configuration
```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (be careful!)
sudo ufw allow 22/tcp

sudo ufw enable
```

### Docker Security
- Container runs as non-root user
- Limited resource allocation
- Docker socket access controlled
- Network isolation

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Application health
curl http://localhost/health

# Database connectivity
curl http://localhost/api/health/db

# System resources
docker stats  # for Docker deployment
htop         # for server deployment
```

### Log Management
```bash
# Application logs (Docker)
docker-compose logs -f codelens-app

# Application logs (Server)
sudo journalctl -u codelens -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Backup Procedures
```bash
# Database backup
pg_dump codelens > backup_$(date +%Y%m%d).sql

# Application data backup
tar -czf codelens_data_$(date +%Y%m%d).tar.gz /opt/codelens/data

# Docker volumes backup
docker run --rm -v codelens_postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

### Updates
```bash
# Docker deployment
docker-compose pull && docker-compose up -d

# Server deployment
sudo ./scripts/deploy/server_update.sh
```

## 🔧 Troubleshooting

### Common Issues

**Database Connection Errors**:
- Check database credentials in `.env`
- Verify database service is running
- Check network connectivity

**Docker Permission Errors**:
- Add user to docker group: `sudo usermod -aG docker $USER`
- Restart session or reboot

**High Memory Usage**:
- Reduce concurrent workers
- Configure resource limits
- Check for memory leaks in logs

**Analysis Timeouts**:
- Increase timeout values in configuration
- Check Docker daemon status
- Monitor system resources

### Debug Mode
```bash
# Enable debug logging
CODELENS_LOG_LEVEL=debug
CODELENS_DEBUG=true

# Docker debug
docker-compose logs -f codelens-app
```

### Performance Tuning
```bash
# Monitor resource usage
docker stats
htop

# Database optimization
# - Configure PostgreSQL shared_buffers
# - Enable query logging
# - Regular VACUUM and ANALYZE

# Application tuning
# - Adjust worker count based on CPU cores
# - Configure connection pooling
# - Enable Redis caching
```

## 📚 Additional Resources

- [API Documentation](http://localhost:8000/docs)
- [Configuration Reference](.env.example)
- [Development Guide](README.md)
- [Issue Tracker](https://github.com/michael-borck/code-lens/issues)

## 🆘 Support

For deployment issues:
1. Check this troubleshooting guide
2. Review application logs
3. Open an issue on GitHub with:
   - Deployment method used
   - Error messages
   - System information
   - Configuration (sanitized)