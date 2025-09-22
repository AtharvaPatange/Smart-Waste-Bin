#!/bin/bash

# Railway Deployment Script for Sortyx Medical Waste System
echo "🚄 Deploying Sortyx Medical Waste System to Railway..."

# Set environment variables
echo "Setting environment variables..."
railway variables --set "GEMINI_API_KEY=AIzaSyCE9DNXLCebiANMcQE9mktuK9nm6bxECjk"
railway variables --set "DEBUG=False"
railway variables --set "HOST=0.0.0.0"
railway variables --set "PORT=8000"
railway variables --set "SECRET_KEY=sk-prod-8f3e9d2c1b4a7e6f5d8c9b2a1e4f7d6c3b8e1a4f7d2c5b8e1a4f7d3c6b9e2a5f8d1c4b"
railway variables --set "MAX_FILE_SIZE=10485760"

echo "🚀 Starting deployment..."
railway up

echo "✅ Deployment complete!"
echo "🌐 Your app will be available at the Railway-provided URL"