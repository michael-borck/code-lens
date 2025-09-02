#!/bin/bash
# CodeLens Server Installation Script
# Usage: ./server_install.sh [environment]

set -e

ENVIRONMENT=${1:-production}
INSTALL_DIR="/opt/codelens"
SERVICE_USER="codelens"
PYTHON_VERSION="3.11"

echo "🚀 Installing CodeLens Server (Environment: $ENVIRONMENT)"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
apt-get install -y \
    python$PYTHON_VERSION \
    python$PYTHON_VERSION-dev \
    python$PYTHON_VERSION-venv \
    python3-pip \
    git \
    curl \
    nginx \
    supervisor \
    postgresql \
    postgresql-contrib \
    redis-server \
    build-essential \
    pkg-config \
    docker.io \
    docker-compose

# Create service user
echo "👤 Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash -d $INSTALL_DIR $SERVICE_USER
    usermod -aG docker $SERVICE_USER
fi

# Create installation directory
echo "📁 Setting up installation directory..."
mkdir -p $INSTALL_DIR
chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# Switch to service user for application setup
echo "⬇️  Downloading and installing CodeLens..."
sudo -u $SERVICE_USER bash << EOF
cd $INSTALL_DIR

# Clone or update repository
if [ -d ".git" ]; then
    echo "📥 Updating existing installation..."
    git pull
else
    echo "📥 Cloning CodeLens repository..."
    git clone https://github.com/michael-borck/code-lens.git .
fi

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# Create virtual environment and install dependencies
echo "🐍 Setting up Python environment..."
~/.local/bin/uv venv --python=$PYTHON_VERSION .venv
source .venv/bin/activate
~/.local/bin/uv sync

# Create necessary directories
mkdir -p logs data uploads temp backups
chmod 755 logs data uploads temp backups

# Create environment configuration
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment configuration..."
    cat > .env << EOL
CODELENS_ENV=$ENVIRONMENT
CODELENS_LOG_LEVEL=info
CODELENS_HOST=0.0.0.0
CODELENS_PORT=8000
CODELENS_DATABASE__URL=postgresql+asyncpg://codelens:codelens_secure_password@localhost:5432/codelens
CODELENS_REDIS_URL=redis://localhost:6379/0
CODELENS_SECRET_KEY=\$(openssl rand -hex 32)
CODELENS_DOCKER_ENABLED=true
CODELENS_SIMILARITY__ENABLED=true
EOL
fi
EOF

# Setup PostgreSQL database
echo "🗄️  Setting up PostgreSQL database..."
sudo -u postgres bash << EOF
if ! psql -lqt | cut -d \| -f 1 | grep -qw codelens; then
    createuser codelens
    createdb -O codelens codelens
    psql -c "ALTER USER codelens WITH PASSWORD 'codelens_secure_password';"
    echo "Database 'codelens' created successfully."
else
    echo "Database 'codelens' already exists."
fi
EOF

# Setup systemd service
echo "🔄 Creating systemd service..."
cat > /etc/systemd/system/codelens.service << EOF
[Unit]
Description=CodeLens Automated Code Analysis Service
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn codelens.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Setup Nginx reverse proxy
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/codelens << EOF
server {
    listen 80;
    server_name localhost;  # Replace with your domain
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/codelens /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# Start services
echo "🚀 Starting services..."
systemctl daemon-reload
systemctl enable postgresql redis-server nginx codelens
systemctl start postgresql redis-server

# Run database migrations
echo "🔄 Running database migrations..."
sudo -u $SERVICE_USER bash << EOF
cd $INSTALL_DIR
source .venv/bin/activate
python -m codelens.db.migrations
EOF

# Start application services
systemctl start nginx codelens

echo "✅ CodeLens installation completed!"
echo ""
echo "📋 Service Status:"
systemctl status codelens --no-pager -l
echo ""
echo "🌐 Access CodeLens at: http://localhost"
echo "📊 Health Check: http://localhost/health"
echo ""
echo "🔧 Management Commands:"
echo "  - Start:   systemctl start codelens"
echo "  - Stop:    systemctl stop codelens"
echo "  - Restart: systemctl restart codelens"
echo "  - Status:  systemctl status codelens"
echo "  - Logs:    journalctl -u codelens -f"
echo ""
echo "📁 Installation Directory: $INSTALL_DIR"
echo "👤 Service User: $SERVICE_USER"