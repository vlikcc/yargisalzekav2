#!/bin/bash

# Yargısal Zeka - Quick Deploy Script
# Bu script projeyi Google Cloud'a hızlıca deploy eder

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first:"
    echo "curl https://sdk.cloud.google.com | bash"
    exit 1
fi

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_error "You are not logged in to gcloud. Please run:"
    echo "gcloud auth login"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    print_error "No project is set. Please run:"
    echo "gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

print_status "Using project: $PROJECT_ID"

# Check if required APIs are enabled
print_status "Checking required APIs..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "firestore.googleapis.com"
    "secretmanager.googleapis.com"
    "containerregistry.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        print_warning "Enabling $api..."
        gcloud services enable "$api"
    else
        print_success "$api is already enabled"
    fi
done

# Check if secrets exist
print_status "Checking secrets..."
REQUIRED_SECRETS=(
    "gemini-api-key"
    "jwt-secret-key"
    "gcp-project-id"
    "mongodb-connection"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! gcloud secrets describe "$secret" &>/dev/null; then
        print_error "Secret '$secret' does not exist. Please create it first:"
        echo "echo -n 'YOUR_VALUE' | gcloud secrets create $secret --data-file=-"
        exit 1
    else
        print_success "Secret '$secret' exists"
    fi
done

# Create Firestore database if it doesn't exist
print_status "Checking Firestore database..."
if ! gcloud firestore databases describe --database="(default)" &>/dev/null; then
    print_warning "Creating Firestore database..."
    gcloud firestore databases create --region=europe-west1
    print_success "Firestore database created"
else
    print_success "Firestore database already exists"
fi

# Start deployment
print_status "Starting deployment with Cloud Build..."
echo "This will take approximately 15-20 minutes..."

# Submit build
BUILD_ID=$(gcloud builds submit --config=cloudbuild.yaml --format="value(id)")

if [ $? -eq 0 ]; then
    print_success "Build submitted successfully! Build ID: $BUILD_ID"
    
    # Follow build logs
    print_status "Following build logs..."
    gcloud builds log --stream "$BUILD_ID"
    
    # Check build status
    BUILD_STATUS=$(gcloud builds describe "$BUILD_ID" --format="value(status)")
    
    if [ "$BUILD_STATUS" = "SUCCESS" ]; then
        print_success "🎉 Deployment completed successfully!"
        
        # Get service URLs
        print_status "Getting service URLs..."
        FRONTEND_URL=$(gcloud run services describe yargisalzeka-frontend --region=europe-west1 --format='value(status.url)' 2>/dev/null || echo "Not deployed")
        BACKEND_URL=$(gcloud run services describe yargisalzeka-backend --region=europe-west1 --format='value(status.url)' 2>/dev/null || echo "Not deployed")
        SCRAPER_URL=$(gcloud run services describe yargisalzeka-scraper --region=europe-west1 --format='value(status.url)' 2>/dev/null || echo "Not deployed")
        
        echo ""
        echo "🌐 Your application is now live!"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Frontend:  $FRONTEND_URL"
        echo "Backend:   $BACKEND_URL"
        echo "Scraper:   $SCRAPER_URL"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        # Run health checks
        print_status "Running health checks..."
        if curl -f "$FRONTEND_URL/health" &>/dev/null; then
            print_success "Frontend health check passed"
        else
            print_warning "Frontend health check failed"
        fi
        
        if curl -f "$BACKEND_URL/health" &>/dev/null; then
            print_success "Backend health check passed"
        else
            print_warning "Backend health check failed"
        fi
        
        echo ""
        print_success "Deployment completed! Your Yargısal Zeka application is ready to use."
        
    else
        print_error "Build failed with status: $BUILD_STATUS"
        print_error "Check the build logs above for more details."
        exit 1
    fi
    
else
    print_error "Failed to submit build"
    exit 1
fi

