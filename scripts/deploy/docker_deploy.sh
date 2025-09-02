#!/bin/bash
# CodeLens Docker Deployment Script
# Usage: ./docker_deploy.sh [dev|prod]

set -e

ENVIRONMENT=${1:-dev}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENVIRONMENT" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

echo "🐳 Deploying CodeLens with Docker (Environment: $ENVIRONMENT)"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Use docker compose or docker-compose based on what's available
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

# Create environment file for production
if [ "$ENVIRONMENT" = "prod" ]; then
    if [ ! -f ".env.prod" ]; then
        echo "⚙️  Creating production environment file..."
        cat > .env.prod << EOF
# Production Environment Variables
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)

# Optional: Override these defaults
# CODELENS_HOST=your-domain.com
# CODELENS_LOG_LEVEL=warning
EOF
        echo "📝 Please review and customize .env.prod before deploying to production"
        echo "   - Set your domain name"
        echo "   - Configure SSL certificates"
        echo "   - Review security settings"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    export $(cat .env.prod | grep -v '^#' | xargs)
fi

# Build and start services
echo "🏗️  Building CodeLens Docker image..."
$DOCKER_COMPOSE -f $COMPOSE_FILE build

echo "🚀 Starting CodeLens services..."
$DOCKER_COMPOSE -f $COMPOSE_FILE up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run database migrations
echo "🔄 Running database migrations..."
$DOCKER_COMPOSE -f $COMPOSE_FILE exec codelens-app uv run alembic upgrade head || echo "No migrations to run"

# Check service health
echo "🔍 Checking service health..."
if [ "$ENVIRONMENT" = "prod" ]; then
    # Production uses Nginx
    if curl -f http://localhost/health &> /dev/null; then
        echo "✅ CodeLens is running successfully!"
        echo "🌐 Access CodeLens at: http://localhost"
    else
        echo "❌ Health check failed!"
        $DOCKER_COMPOSE -f $COMPOSE_FILE logs codelens-app
        exit 1
    fi
else
    # Development direct access
    if curl -f http://localhost:8003/health &> /dev/null; then
        echo "✅ CodeLens is running successfully!"
        echo "🌐 Access CodeLens at: http://localhost:8003"
    else
        echo "❌ Health check failed!"
        $DOCKER_COMPOSE -f $COMPOSE_FILE logs codelens-app
        exit 1
    fi
fi

echo ""
echo "📋 Container Status:"
$DOCKER_COMPOSE -f $COMPOSE_FILE ps

echo ""
echo "🔧 Management Commands:"
echo "  - View logs:    $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f"
echo "  - Stop:         $DOCKER_COMPOSE -f $COMPOSE_FILE down"
echo "  - Restart:      $DOCKER_COMPOSE -f $COMPOSE_FILE restart"
echo "  - Shell access: $DOCKER_COMPOSE -f $COMPOSE_FILE exec codelens-app bash"

if [ "$ENVIRONMENT" = "prod" ]; then
    echo ""
    echo "🔒 Production Notes:"
    echo "  - Configure SSL certificates in ./ssl/ directory"
    echo "  - Review nginx.conf for your domain"
    echo "  - Set up backup procedures for data volumes"
    echo "  - Monitor logs: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f"
fi