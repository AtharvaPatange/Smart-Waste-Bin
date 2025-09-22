#!/bin/bash
# Google Cloud Platform Production Deployment Script
# Sortyx Medical Waste Classification System

echo "🚀 Deploying Sortyx Medical Waste System to Google Cloud..."

# Configuration
PROJECT_ID="sortyx-medical-waste-prod"
REGION="us-central1"
SERVICE_NAME="sortyx-backend"
DATABASE_INSTANCE="sortyx-postgres-prod"

# 1. Authenticate and set project
echo "📋 Setting up Google Cloud project..."
gcloud auth login
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com
gcloud services enable sql.googleapis.com
gcloud services enable redis.googleapis.com

# 2. Create Cloud SQL PostgreSQL instance
echo "🗄️ Creating PostgreSQL database..."
gcloud sql instances create $DATABASE_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=20GB \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04

# Create database and user
gcloud sql databases create sortyx_db --instance=$DATABASE_INSTANCE
gcloud sql users create sortyx_user --instance=$DATABASE_INSTANCE --password=SECURE_PASSWORD_HERE

# 3. Create Redis instance
echo "⚡ Creating Redis cache..."
gcloud redis instances create sortyx-redis \
    --size=1 \
    --region=$REGION \
    --redis-version=redis_7_0

# 4. Build and deploy to Cloud Run
echo "🐳 Building and deploying container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME .

# 5. Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --region $REGION \
    --platform managed \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --set-env-vars ENVIRONMENT=production \
    --set-env-vars DEBUG=False \
    --allow-unauthenticated

# 6. Set up custom domain (optional)
echo "🌐 Custom domain setup available at:"
echo "https://console.cloud.google.com/run/domains"

# 7. Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "✅ Deployment complete!"
echo "🔗 Your medical waste system is live at: $SERVICE_URL"
echo "📊 Monitor at: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"

# 8. Set up monitoring
echo "📈 Setting up monitoring..."
gcloud alpha monitoring policies create \
    --policy-from-file=monitoring-policy.yaml

echo "🎉 Production deployment successful!"
echo "💡 Next steps:"
echo "  1. Configure your domain: https://console.cloud.google.com/run/domains"  
echo "  2. Set up SSL certificate for HTTPS"
echo "  3. Configure firewall rules if needed"
echo "  4. Set up backup schedules"
echo "  5. Configure alerting policies"