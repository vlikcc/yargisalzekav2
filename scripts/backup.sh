#!/bin/bash

# Yargısal Zeka Backup Script
# MongoDB Atlas ve sistem backup'ları için

set -e

# Configuration
BACKUP_BASE_DIR="/backups"
RETENTION_DAYS=30
LOG_FILE="/var/log/yargisalzeka/backup.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

# Load environment variables
load_env() {
    if [[ -f ".env.prod" ]]; then
        source .env.prod
    elif [[ -f ".env" ]]; then
        source .env
    else
        error "No environment file found"
    fi
}

# MongoDB Atlas backup
backup_mongodb() {
    local backup_dir="$1/mongodb"
    mkdir -p "$backup_dir"
    
    log "Starting MongoDB Atlas backup..."
    
    if [[ -z "$MONGODB_CONNECTION_STRING" ]]; then
        error "MONGODB_CONNECTION_STRING not found in environment"
    fi
    
    # Use mongodump to create backup
    if command -v mongodump &> /dev/null; then
        mongodump --uri="$MONGODB_CONNECTION_STRING" --out="$backup_dir" --gzip
        success "MongoDB backup completed"
    else
        # Alternative: Use MongoDB Atlas API for backup
        log "mongodump not available, using MongoDB Atlas API..."
        
        # This would require MongoDB Atlas API implementation
        # For now, create a placeholder
        echo "MongoDB Atlas backup placeholder - implement API backup" > "$backup_dir/atlas_backup.txt"
        
        warning "MongoDB backup requires proper Atlas API implementation"
    fi
}

# Application data backup
backup_application_data() {
    local backup_dir="$1/application"
    mkdir -p "$backup_dir"
    
    log "Backing up application data..."
    
    # Backup configuration files
    if [[ -f ".env.prod" ]]; then
        cp .env.prod "$backup_dir/"
    fi
    
    if [[ -f "docker-compose.prod.yml" ]]; then
        cp docker-compose.prod.yml "$backup_dir/"
    fi
    
    # Backup SSL certificates
    if [[ -d "ssl" ]]; then
        cp -r ssl "$backup_dir/"
    fi
    
    # Backup logs (last 7 days)
    if [[ -d "logs" ]]; then
        find logs -name "*.log" -mtime -7 -exec cp {} "$backup_dir/" \;
    fi
    
    # Backup monitoring configurations
    if [[ -d "monitoring" ]]; then
        cp -r monitoring "$backup_dir/"
    fi
    
    success "Application data backup completed"
}

# Docker images backup
backup_docker_images() {
    local backup_dir="$1/docker"
    mkdir -p "$backup_dir"
    
    log "Backing up Docker images..."
    
    # Get list of custom images
    local images=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "(yargisalzeka|main-api|scraper-api|frontend)" | head -5)
    
    for image in $images; do
        if [[ "$image" != "<none>:<none>" ]]; then
            local filename=$(echo "$image" | sed 's/[\/:]/_/g')
            log "Backing up image: $image"
            docker save "$image" | gzip > "$backup_dir/${filename}.tar.gz"
        fi
    done
    
    success "Docker images backup completed"
}

# System configuration backup
backup_system_config() {
    local backup_dir="$1/system"
    mkdir -p "$backup_dir"
    
    log "Backing up system configuration..."
    
    # Backup crontab
    crontab -l > "$backup_dir/crontab.txt" 2>/dev/null || echo "No crontab found"
    
    # Backup nginx config (if exists)
    if [[ -f "/etc/nginx/nginx.conf" ]]; then
        cp /etc/nginx/nginx.conf "$backup_dir/" 2>/dev/null || true
    fi
    
    # System info
    uname -a > "$backup_dir/system_info.txt"
    df -h > "$backup_dir/disk_usage.txt"
    docker version > "$backup_dir/docker_version.txt" 2>/dev/null || true
    
    success "System configuration backup completed"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    find "$BACKUP_BASE_DIR" -type d -name "backup_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    
    local remaining=$(find "$BACKUP_BASE_DIR" -type d -name "backup_*" | wc -l)
    success "Cleanup completed. $remaining backup(s) remaining."
}

# Create backup archive
create_archive() {
    local backup_dir="$1"
    local archive_name="$backup_dir.tar.gz"
    
    log "Creating compressed archive..."
    
    tar -czf "$archive_name" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    
    # Remove uncompressed backup
    rm -rf "$backup_dir"
    
    local size=$(du -h "$archive_name" | cut -f1)
    success "Archive created: $archive_name ($size)"
}

# Send backup to remote storage (optional)
upload_to_remote() {
    local archive_file="$1"
    
    if [[ -n "$BACKUP_REMOTE_PATH" ]]; then
        log "Uploading backup to remote storage..."
        
        # Example implementations:
        # AWS S3: aws s3 cp "$archive_file" "$BACKUP_REMOTE_PATH"
        # SCP: scp "$archive_file" "$BACKUP_REMOTE_PATH"
        # rsync: rsync -av "$archive_file" "$BACKUP_REMOTE_PATH"
        
        log "Remote upload configured but not implemented. Add your preferred method."
    fi
}

# Verify backup integrity
verify_backup() {
    local archive_file="$1"
    
    log "Verifying backup integrity..."
    
    if tar -tzf "$archive_file" > /dev/null 2>&1; then
        success "Backup integrity verified"
    else
        error "Backup integrity check failed"
    fi
}

# Main backup function
main() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/backup_$timestamp"
    
    log "Starting backup process..."
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$backup_dir"
    
    # Load environment
    load_env
    
    # Perform backups
    backup_mongodb "$backup_dir"
    backup_application_data "$backup_dir"
    backup_docker_images "$backup_dir"
    backup_system_config "$backup_dir"
    
    # Create archive
    create_archive "$backup_dir"
    
    # Verify backup
    verify_backup "$backup_dir.tar.gz"
    
    # Upload to remote (if configured)
    upload_to_remote "$backup_dir.tar.gz"
    
    # Cleanup old backups
    cleanup_old_backups
    
    success "Backup process completed successfully!"
    log "Backup file: $backup_dir.tar.gz"
}

# Restore function
restore() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        error "Please specify backup file to restore"
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
    fi
    
    log "Starting restore process from: $backup_file"
    
    # Create temporary restore directory
    local restore_dir="/tmp/yargisalzeka_restore_$(date +%s)"
    mkdir -p "$restore_dir"
    
    # Extract backup
    log "Extracting backup..."
    tar -xzf "$backup_file" -C "$restore_dir"
    
    # Find the backup directory
    local backup_content_dir=$(find "$restore_dir" -name "backup_*" -type d | head -1)
    
    if [[ -z "$backup_content_dir" ]]; then
        error "Invalid backup file structure"
    fi
    
    # Restore MongoDB (manual process - requires confirmation)
    if [[ -d "$backup_content_dir/mongodb" ]]; then
        warning "MongoDB restore requires manual intervention."
        log "MongoDB backup location: $backup_content_dir/mongodb"
        log "Use mongorestore command to restore database"
    fi
    
    # Restore application data
    if [[ -d "$backup_content_dir/application" ]]; then
        log "Restoring application data..."
        
        if [[ -f "$backup_content_dir/application/.env.prod" ]]; then
            cp "$backup_content_dir/application/.env.prod" .
        fi
        
        if [[ -f "$backup_content_dir/application/docker-compose.prod.yml" ]]; then
            cp "$backup_content_dir/application/docker-compose.prod.yml" .
        fi
        
        if [[ -d "$backup_content_dir/application/ssl" ]]; then
            cp -r "$backup_content_dir/application/ssl" .
        fi
    fi
    
    # Restore Docker images
    if [[ -d "$backup_content_dir/docker" ]]; then
        log "Restoring Docker images..."
        
        for image_file in "$backup_content_dir/docker"/*.tar.gz; do
            if [[ -f "$image_file" ]]; then
                log "Loading image: $(basename "$image_file")"
                gunzip -c "$image_file" | docker load
            fi
        done
    fi
    
    # Cleanup
    rm -rf "$restore_dir"
    
    success "Restore process completed!"
    log "Please review restored files and restart services if needed."
}

# Script options
case "${1:-backup}" in
    "backup")
        main
        ;;
    "restore")
        restore "$2"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "verify")
        verify_backup "$2"
        ;;
    *)
        echo "Usage: $0 {backup|restore|cleanup|verify}"
        echo "  backup           - Create full backup (default)"
        echo "  restore <file>   - Restore from backup file"
        echo "  cleanup          - Remove old backups"
        echo "  verify <file>    - Verify backup integrity"
        exit 1
        ;;
esac