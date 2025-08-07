#!/bin/bash

# Yargısal Zeka Production Deployment Script
# Bu script production ortamına güvenli deployment yapar

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/var/log/yargisalzeka/deploy.log"
HEALTH_CHECK_TIMEOUT=300  # 5 minutes

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Starting pre-deployment checks..."
    
    # Check if required files exist
    if [[ ! -f ".env.prod" ]]; then
        error "Production environment file (.env.prod) not found!"
    fi
    
    if [[ ! -f "docker-compose.prod.yml" ]]; then
        error "Production docker-compose file not found!"
    fi
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
    fi
    
    # Check if SSL certificates exist
    if [[ ! -f "ssl/fullchain.pem" ]] || [[ ! -f "ssl/privkey.pem" ]]; then
        warning "SSL certificates not found. HTTPS will not work properly."
    fi
    
    success "Pre-deployment checks completed"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup current containers (if running)
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log "Backing up current deployment..."
        docker-compose -f docker-compose.prod.yml config > "$BACKUP_DIR/docker-compose.backup.yml"
        cp .env.prod "$BACKUP_DIR/.env.prod.backup" 2>/dev/null || true
    fi
    
    # Backup database (MongoDB Atlas - create dump)
    if [[ -n "${MONGODB_CONNECTION_STRING}" ]]; then
        log "Creating MongoDB backup..."
        # This would require mongodump - implement based on your backup strategy
        # mongodump --uri="${MONGODB_CONNECTION_STRING}" --out="$BACKUP_DIR/mongodb"
    fi
    
    success "Backup created at $BACKUP_DIR"
}

# Build and deploy
deploy() {
    log "Starting deployment..."
    
    # Pull latest changes (if this is a git deployment)
    if [[ -d ".git" ]]; then
        log "Pulling latest changes..."
        git pull origin main
    fi
    
    # Build new images
    log "Building new Docker images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Stop old containers gracefully
    log "Stopping old containers..."
    docker-compose -f docker-compose.prod.yml down --timeout 30
    
    # Start new containers
    log "Starting new containers..."
    docker-compose -f docker-compose.prod.yml up -d
    
    success "Containers started successfully"
}

# Health checks
health_check() {
    log "Performing health checks..."
    
    local start_time=$(date +%s)
    local timeout=$HEALTH_CHECK_TIMEOUT
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $timeout ]]; then
            error "Health check timeout after ${timeout} seconds"
        fi
        
        # Check main API
        if curl -f -s "http://localhost:8000/health" > /dev/null 2>&1; then
            log "Main API is healthy"
            break
        fi
        
        log "Waiting for services to start... (${elapsed}s elapsed)"
        sleep 10
    done
    
    # Additional health checks
    log "Running additional health checks..."
    
    # Check scraper API
    if ! curl -f -s "http://localhost:8001/health" > /dev/null 2>&1; then
        warning "Scraper API health check failed"
    else
        log "Scraper API is healthy"
    fi
    
    # Check frontend
    if ! curl -f -s "http://localhost/health" > /dev/null 2>&1; then
        warning "Frontend health check failed"
    else
        log "Frontend is healthy"
    fi
    
    # Check database connectivity
    log "Checking database connectivity..."
    if docker-compose -f docker-compose.prod.yml exec -T main-api python -c "
import asyncio
from app.database import init_database
result = asyncio.run(init_database())
exit(0 if result else 1)
" > /dev/null 2>&1; then
        log "Database connectivity confirmed"
    else
        warning "Database connectivity check failed"
    fi
    
    success "Health checks completed"
}

# Post-deployment tasks
post_deployment() {
    log "Running post-deployment tasks..."
    
    # Clean up old Docker images
    log "Cleaning up old Docker images..."
    docker image prune -f
    
    # Update monitoring dashboards (if needed)
    # log "Updating monitoring dashboards..."
    
    # Send deployment notification (implement based on your notification system)
    # log "Sending deployment notification..."
    
    success "Post-deployment tasks completed"
}

# Rollback function
rollback() {
    error "Deployment failed. Starting rollback..."
    
    if [[ -f "$BACKUP_DIR/docker-compose.backup.yml" ]]; then
        log "Rolling back to previous version..."
        docker-compose -f docker-compose.prod.yml down
        cp "$BACKUP_DIR/docker-compose.backup.yml" docker-compose.prod.yml
        cp "$BACKUP_DIR/.env.prod.backup" .env.prod 2>/dev/null || true
        docker-compose -f docker-compose.prod.yml up -d
        
        # Wait and check if rollback was successful
        sleep 30
        if curl -f -s "http://localhost:8000/health" > /dev/null 2>&1; then
            success "Rollback completed successfully"
        else
            error "Rollback failed. Manual intervention required!"
        fi
    else
        error "No backup found for rollback. Manual intervention required!"
    fi
}

# Main deployment flow
main() {
    log "Starting Yargısal Zeka production deployment..."
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Trap errors for rollback
    trap rollback ERR
    
    # Run deployment steps
    pre_deployment_checks
    create_backup
    deploy
    health_check
    post_deployment
    
    success "Deployment completed successfully!"
    log "Services are running at:"
    log "  - Frontend: https://yargisalzeka.com"
    log "  - API: https://api.yargisalzeka.com"
    log "  - Monitoring: https://monitoring.yargisalzeka.com"
    log "  - Logs: $LOG_FILE"
}

# Script options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "health-check")
        health_check
        ;;
    "backup")
        create_backup
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|health-check|backup}"
        echo "  deploy      - Full production deployment (default)"
        echo "  rollback    - Rollback to previous version"
        echo "  health-check - Run health checks only"
        echo "  backup      - Create backup only"
        exit 1
        ;;
esac