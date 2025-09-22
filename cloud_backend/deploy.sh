#!/bin/bash

# Sortyx Medical Waste Cloud Deployment Script
# This script automates the deployment process for various cloud providers

set -e  # Exit on any error

echo "🚀 Sortyx Medical Waste Classification - Cloud Deployment"
echo "======================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if required files exist
check_requirements() {
    echo "🔍 Checking deployment requirements..."
    
    required_files=(
        "app.py"
        "requirements.txt" 
        "Dockerfile"
        "docker-compose.yml"
        ".env.example"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Required file $file not found!"
            exit 1
        else
            print_status "Found $file"
        fi
    done
}

# Create environment file if it doesn't exist
setup_environment() {
    echo "🔧 Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_warning "Created .env file from template. Please configure your environment variables!"
        echo "Edit .env file with your actual API keys and configuration."
        read -p "Press Enter to continue after configuring .env file..."
    else
        print_status "Environment file exists"
    fi
}

# Deploy to Heroku
deploy_heroku() {
    echo "🌐 Deploying to Heroku..."
    
    # Check if Heroku CLI is installed
    if ! command -v heroku &> /dev/null; then
        print_error "Heroku CLI not found. Please install it first:"
        echo "https://devcenter.heroku.com/articles/heroku-cli"
        exit 1
    fi
    
    # Login to Heroku
    echo "Please login to Heroku:"
    heroku login
    
    # Create Heroku app
    read -p "Enter your Heroku app name (e.g., sortyx-medical-waste): " app_name
    
    # Check if app exists
    if heroku apps:info $app_name &> /dev/null; then
        print_status "Using existing Heroku app: $app_name"
    else
        heroku create $app_name
        print_status "Created new Heroku app: $app_name"
    fi
    
    # Set environment variables
    echo "Setting up environment variables..."
    read -p "Enter your Gemini API key: " gemini_key
    heroku config:set GEMINI_API_KEY=$gemini_key --app $app_name
    
    # Deploy
    git add .
    git commit -m "Deploy Sortyx Medical Waste Classification to Heroku" || true
    git push heroku main
    
    print_status "Deployment to Heroku complete!"
    echo "Your app is available at: https://$app_name.herokuapp.com"
}

# Deploy using Docker
deploy_docker() {
    echo "🐳 Deploying with Docker..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker first:"
        echo "https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Build and run with docker-compose
    docker-compose down
    docker-compose build
    docker-compose up -d
    
    print_status "Docker deployment complete!"
    echo "Application is running at: http://localhost:8000"
}

# Deploy to AWS using Docker
deploy_aws() {
    echo "☁️ Deploying to AWS..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first:"
        echo "https://aws.amazon.com/cli/"
        exit 1
    fi
    
    # Build Docker image
    docker build -t sortyx-medical-waste .
    
    # Tag for ECR (replace with your ECR repository URI)
    read -p "Enter your ECR repository URI: " ecr_uri
    docker tag sortyx-medical-waste:latest $ecr_uri:latest
    
    # Push to ECR
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ecr_uri
    docker push $ecr_uri:latest
    
    print_status "Docker image pushed to ECR"
    print_warning "Please complete ECS/Fargate setup in AWS console"
}

# Deploy to Google Cloud Platform
deploy_gcp() {
    echo "🌐 Deploying to Google Cloud Platform..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud CLI not found. Please install it first:"
        echo "https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Authenticate
    gcloud auth login
    
    # Set project
    read -p "Enter your GCP project ID: " project_id
    gcloud config set project $project_id
    
    # Enable required APIs
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    
    # Deploy to Cloud Run
    gcloud builds submit --tag gcr.io/$project_id/sortyx-medical-waste
    gcloud run deploy sortyx-medical-waste \
        --image gcr.io/$project_id/sortyx-medical-waste \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated
    
    print_status "Deployment to Google Cloud Run complete!"
}

# Deploy to Azure
deploy_azure() {
    echo "🔷 Deploying to Microsoft Azure..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI not found. Please install it first:"
        echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Login to Azure
    az login
    
    # Create resource group
    read -p "Enter resource group name: " resource_group
    read -p "Enter Azure region (e.g., eastus): " region
    
    az group create --name $resource_group --location $region
    
    # Create container registry
    read -p "Enter container registry name: " registry_name
    az acr create --resource-group $resource_group --name $registry_name --sku Basic
    
    # Build and push image
    az acr build --registry $registry_name --image sortyx-medical-waste .
    
    # Create container instance
    az container create \
        --resource-group $resource_group \
        --name sortyx-medical-waste-container \
        --image $registry_name.azurecr.io/sortyx-medical-waste:latest \
        --cpu 2 --memory 4 \
        --registry-login-server $registry_name.azurecr.io \
        --ports 8000 \
        --ip-address public
    
    print_status "Deployment to Azure complete!"
}

# Main menu
show_menu() {
    echo ""
    echo "Select deployment option:"
    echo "1) Heroku (easiest, free tier available)"
    echo "2) Docker (local/self-hosted)"
    echo "3) AWS (using ECR + ECS/Fargate)"
    echo "4) Google Cloud Platform (Cloud Run)"
    echo "5) Microsoft Azure (Container Instances)"
    echo "6) Exit"
    echo ""
}

# Main deployment logic
main() {
    check_requirements
    setup_environment
    
    while true; do
        show_menu
        read -p "Enter your choice (1-6): " choice
        
        case $choice in
            1)
                deploy_heroku
                break
                ;;
            2)
                deploy_docker
                break
                ;;
            3)
                deploy_aws
                break
                ;;
            4)
                deploy_gcp
                break
                ;;
            5)
                deploy_azure
                break
                ;;
            6)
                echo "Deployment cancelled."
                exit 0
                ;;
            *)
                print_error "Invalid option. Please select 1-6."
                ;;
        esac
    done
    
    echo ""
    print_status "Deployment completed successfully! 🎉"
    echo ""
    echo "📝 Next steps:"
    echo "1. Configure your ESP32 with the deployed server URL"
    echo "2. Set up your YOLO models in the /models directory"
    echo "3. Configure monitoring and alerts"
    echo "4. Test the system with medical waste samples"
    echo ""
    echo "📚 Documentation: https://github.com/your-username/sortyx-medical-waste"
    echo "🐛 Issues: https://github.com/your-username/sortyx-medical-waste/issues"
}

# Run main function
main "$@"