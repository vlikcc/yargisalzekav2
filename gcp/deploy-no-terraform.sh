#!/bin/bash

# Google Cloud Serverless Deployment Script (Terraform'sız)
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Load environment variables from .env file
if [ -f ".env" ]; then
    log "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}[ERROR] .env file not found! Please create .env file first.${NC}"
    exit 1
fi

# Configuration  
PROJECT_ID="$GCP_PROJECT_ID"
REGION="europe-west1"
DOMAIN_NAME="yargisalzeka.com"

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed. Please install it first."
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
    fi
    
    # Get project ID if not set
    if [[ -z "$PROJECT_ID" ]]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [[ -z "$PROJECT_ID" ]]; then
            error "GCP Project ID not set. Run: gcloud config set project YOUR_PROJECT_ID"
        fi
    fi
    
    log "Using GCP Project: $PROJECT_ID"
    success "Prerequisites check completed (Terraform not required)"
}

# Setup environment
setup_environment() {
    log "Setting up environment..."
    
    # Authenticate with gcloud
    gcloud auth configure-docker gcr.io --quiet
    
    # Set default region
    gcloud config set run/region $REGION
    
    # Enable required APIs
    log "Enabling required APIs..."
    gcloud services enable run.googleapis.com --quiet
    gcloud services enable cloudbuild.googleapis.com --quiet
    gcloud services enable cloudfunctions.googleapis.com --quiet
    gcloud services enable firestore.googleapis.com --quiet
    gcloud services enable secretmanager.googleapis.com --quiet
    gcloud services enable storage.googleapis.com --quiet
    gcloud services enable monitoring.googleapis.com --quiet
    gcloud services enable logging.googleapis.com --quiet
    gcloud services enable compute.googleapis.com --quiet
    
    success "Environment setup completed"
}

# Create secrets
create_secrets() {
    log "Creating secrets in Secret Manager..."
    
    # Create Gemini API Key secret
    if ! gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
        echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
        log "Created gemini-api-key secret"
    else
        echo -n "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
        log "Updated gemini-api-key secret"
    fi
    
    # Create JWT Secret Key secret
    if ! gcloud secrets describe jwt-secret-key >/dev/null 2>&1; then
        echo -n "$JWT_SECRET_KEY" | gcloud secrets create jwt-secret-key --data-file=-
        log "Created jwt-secret-key secret"
    else
        echo -n "$JWT_SECRET_KEY" | gcloud secrets versions add jwt-secret-key --data-file=-
        log "Updated jwt-secret-key secret"
    fi
    
    # Grant Secret Manager access to Compute Engine default service account
    log "Setting up Secret Manager permissions..."
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor"
    
    success "Secrets created/updated"
}

# Create Firestore database
create_firestore() {
    log "Setting up Firestore database..."
    
    if ! gcloud firestore databases describe --database="(default)" >/dev/null 2>&1; then
        gcloud firestore databases create --database="(default)" --location=$REGION --type=firestore-native
        log "Created Firestore database"
    else
        log "Firestore database already exists"
    fi
    
    success "Firestore setup completed"
}

# Build and push Docker images
build_and_push_images() {
    log "Building and pushing Docker images..."
    
    # Build Main API image for AMD64 (Cloud Run requirement)
    log "Building Main API image..."
    docker build --platform linux/amd64 -t gcr.io/$PROJECT_ID/yargisalzeka-main-api:latest \
        -f gcp/main-api/Dockerfile ./hukuk-asistan-main
    
    # Build Frontend image for AMD64 (Cloud Run requirement)
    log "Building Frontend image..."
    docker build --platform linux/amd64 -t gcr.io/$PROJECT_ID/yargisalzeka-frontend:latest \
        -f gcp/frontend/Dockerfile .
    
    # Push images
    log "Pushing images to Container Registry..."
    docker push gcr.io/$PROJECT_ID/yargisalzeka-main-api:latest
    docker push gcr.io/$PROJECT_ID/yargisalzeka-frontend:latest
    
    success "Docker images built and pushed"
}

# Deploy Cloud Run services
deploy_cloud_run() {
    log "Deploying Cloud Run services..."
    
    # Deploy Main API
    log "Deploying Main API to Cloud Run..."
    gcloud run deploy yargisalzeka-api \
        --image=gcr.io/$PROJECT_ID/yargisalzeka-main-api:latest \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --memory=2Gi \
        --cpu=2 \
        --max-instances=100 \
        --min-instances=1 \
        --concurrency=80 \
        --timeout=300 \
        --port=8000 \
        --set-env-vars="ENVIRONMENT=production,GCP_PROJECT=$PROJECT_ID" \
        --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,JWT_SECRET_KEY=jwt-secret-key:latest" \
        --quiet
    
    # Deploy Frontend
    log "Deploying Frontend to Cloud Run..."
    
    # Get API URL for frontend environment
    API_URL=$(gcloud run services describe yargisalzeka-api --region=$REGION --format='value(status.url)')
    
    gcloud run deploy yargisalzeka-frontend \
        --image=gcr.io/$PROJECT_ID/yargisalzeka-frontend:latest \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --memory=512Mi \
        --cpu=1 \
        --max-instances=50 \
        --min-instances=0 \
        --concurrency=1000 \
        --timeout=60 \
        --port=8080 \
        --set-env-vars="API_URL=$API_URL" \
        --quiet
    
    success "Cloud Run services deployed"
}

# Deploy Cloud Functions
deploy_cloud_functions() {
    log "Deploying Cloud Functions..."
    
    # Deploy scraper function
    gcloud functions deploy yargitay-scraper \
        --source=gcp/functions/scraper \
        --entry-point=scrape_yargitay \
        --runtime=python311 \
        --trigger=http \
        --allow-unauthenticated \
        --region=$REGION \
        --memory=2GB \
        --timeout=540s \
        --max-instances=10 \
        --set-env-vars="GCP_PROJECT=$PROJECT_ID,ENVIRONMENT=production" \
        --quiet
    
    success "Cloud Functions deployed"
}

# Setup monitoring and logging
setup_monitoring() {
    log "Setting up monitoring and logging..."
    
    # Create log-based metrics
    gcloud logging metrics create api_errors \
        --description="API Error Count" \
        --log-filter='resource.type="cloud_run_revision" AND severity>=ERROR' \
        --quiet 2>/dev/null || true
    
    gcloud logging metrics create api_latency \
        --description="API Response Latency" \
        --log-filter='resource.type="cloud_run_revision" AND httpRequest.latency>0' \
        --quiet 2>/dev/null || true
    
    success "Monitoring and logging configured"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Get service URLs
    API_URL=$(gcloud run services describe yargisalzeka-api --region=$REGION --format='value(status.url)')
    FRONTEND_URL=$(gcloud run services describe yargisalzeka-frontend --region=$REGION --format='value(status.url)')
    FUNCTION_URL=$(gcloud functions describe yargitay-scraper --region=$REGION --format='value(httpsTrigger.url)')
    
    log "API URL: $API_URL"
    log "Frontend URL: $FRONTEND_URL"
    log "Scraper Function URL: $FUNCTION_URL"
    
    # Test API health
    sleep 10  # Wait for services to be ready
    if curl -f -s "$API_URL/health" > /dev/null; then
        success "API health check passed"
    else
        warning "API health check failed - service might still be starting"
    fi
    
    # Test frontend
    if curl -f -s -o /dev/null "$FRONTEND_URL"; then
        success "Frontend health check passed"
    else
        warning "Frontend health check failed - service might still be starting"
    fi
    
    success "Deployment verification completed"
}

# Show deployment summary
show_summary() {
    log "Deployment Summary"
    echo "=================="
    
    API_URL=$(gcloud run services describe yargisalzeka-api --region=$REGION --format='value(status.url)')
    FRONTEND_URL=$(gcloud run services describe yargisalzeka-frontend --region=$REGION --format='value(status.url)')
    FUNCTION_URL=$(gcloud functions describe yargitay-scraper --region=$REGION --format='value(httpsTrigger.url)')
    
    echo ""
    echo -e "${GREEN}🎉 Deployment Successful!${NC}"
    echo ""
    echo -e "${BLUE}Service URLs:${NC}"
    echo "  🚀 API Service: $API_URL"
    echo "  🌐 Frontend: $FRONTEND_URL"  
    echo "  🔍 Scraper Function: $FUNCTION_URL"
    echo ""
    echo -e "${YELLOW}📝 Next Steps:${NC}"
    echo "1. Test your API: curl $API_URL/health"
    echo "2. Visit your frontend: open $FRONTEND_URL"
    echo "3. Set up custom domain (optional)"
    echo "4. Configure monitoring alerts"
    echo ""
    echo -e "${BLUE}💡 Useful Commands:${NC}"
    echo "  View logs: gcloud logs read 'resource.type=cloud_run_revision'"
    echo "  Update service: gcloud run deploy SERVICE_NAME --image=NEW_IMAGE"
    echo "  Scale service: gcloud run services update SERVICE_NAME --min-instances=N"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    # No temporary files to clean in this version
}

# Main deployment function
main() {
    log "Starting Google Cloud Serverless Deployment (No Terraform)..."
    
    # Check for required environment variables
    if [[ -z "$GEMINI_API_KEY" ]]; then
        error "GEMINI_API_KEY environment variable is required"
    fi
    
    if [[ -z "$JWT_SECRET_KEY" ]]; then
        error "JWT_SECRET_KEY environment variable is required"
    fi
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    setup_environment
    create_secrets
    create_firestore
    build_and_push_images
    deploy_cloud_run
    deploy_cloud_functions
    setup_monitoring
    verify_deployment
    show_summary
    
    success "Deployment completed successfully!"
}

# Script options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "build")
        check_prerequisites
        build_and_push_images
        ;;
    "services")
        check_prerequisites
        setup_environment
        create_secrets
        create_firestore
        deploy_cloud_run
        ;;
    "functions")
        check_prerequisites
        deploy_cloud_functions
        ;;
    "verify")
        verify_deployment
        ;;
    *)
        echo "Usage: $0 {deploy|build|services|functions|verify}"
        echo ""
        echo "Commands:"
        echo "  deploy    - Full deployment (default)"
        echo "  build     - Build and push Docker images only"
        echo "  services  - Deploy Cloud Run services only"
        echo "  functions - Deploy Cloud Functions only"
        echo "  verify    - Verify deployment"
        echo ""
        echo "Environment variables required:"
        echo "  GEMINI_API_KEY - Google Gemini API key"
        echo "  JWT_SECRET_KEY - JWT secret key"
        echo ""
        exit 1
        ;;
esac

