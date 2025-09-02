#!/bin/bash
# CodeLens Server Update Script
# Usage: ./server_update.sh

set -e

INSTALL_DIR="/opt/codelens"
SERVICE_USER="codelens"

echo "🔄 Updating CodeLens Server..."

# Check if installation exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ CodeLens installation not found at $INSTALL_DIR"
    echo "Please run server_install.sh first"
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Stop the service
echo "⏹️  Stopping CodeLens service..."
systemctl stop codelens

# Create backup
BACKUP_DIR="/opt/codelens-backup-$(date +%Y%m%d-%H%M%S)"
echo "💾 Creating backup at $BACKUP_DIR..."
cp -r $INSTALL_DIR $BACKUP_DIR
echo "Backup created: $BACKUP_DIR"

# Update application
echo "📥 Updating application code..."
sudo -u $SERVICE_USER bash << EOF
cd $INSTALL_DIR

# Pull latest changes
git fetch origin
git pull origin main

# Update dependencies
source .venv/bin/activate
~/.local/bin/uv sync

# Run any database migrations
echo "🔄 Running database migrations..."
python -m alembic upgrade head || echo "No migrations to run"
EOF

# Reload systemd and restart service
echo "🚀 Restarting services..."
systemctl daemon-reload
systemctl start codelens
systemctl reload nginx

# Verify service is running
sleep 5
if systemctl is-active --quiet codelens; then
    echo "✅ CodeLens update completed successfully!"
    echo ""
    echo "📋 Service Status:"
    systemctl status codelens --no-pager -l | head -10
    echo ""
    echo "🔍 Testing health endpoint..."
    curl -f http://localhost/health && echo "" || echo "❌ Health check failed"
else
    echo "❌ Service failed to start after update!"
    echo "📋 Service Status:"
    systemctl status codelens --no-pager -l
    echo ""
    echo "🔄 Rolling back from backup..."
    systemctl stop codelens
    rm -rf $INSTALL_DIR
    mv $BACKUP_DIR $INSTALL_DIR
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    systemctl start codelens
    echo "Rolled back to backup: $BACKUP_DIR"
    exit 1
fi

echo ""
echo "🧹 Cleanup: Remove backup with 'rm -rf $BACKUP_DIR' if everything works correctly"