#!/usr/bin/env python3
"""
Railway-Optimized Medical Waste Classification Backend
Simplified version for initial deployment
"""

import os
import io
import base64
import json
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path

# Web Framework
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi import Request

# AI/ML Libraries
import numpy as np
from PIL import Image
import google.generativeai as genai

# Utilities
import qrcode
from dotenv import load_dotenv
import aiofiles

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sortyx Medical Waste Classification API",
    description="Cloud-based medical waste classification system",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Railway needs broad access initially
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Create necessary directories
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/qr_codes", exist_ok=True)

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("✅ Gemini AI configured successfully")
else:
    logger.warning("⚠️ GEMINI_API_KEY not found in environment variables")
    gemini_model = None

class MedicalWasteClassifier:
    def __init__(self):
        self.waste_categories = {
            "yellow": {
                "name": "General Biomedical Waste",
                "description": "Pathological waste, body parts, tissues",
                "color": "#FFD700",
                "bin_id": 1
            },
            "red": {
                "name": "Infectious/Pathological Waste", 
                "description": "Highly infectious materials, cultures",
                "color": "#DC143C",
                "bin_id": 2
            },
            "blue": {
                "name": "Sharp Objects",
                "description": "Needles, scalpels, broken glass",
                "color": "#1E90FF", 
                "bin_id": 3
            },
            "black": {
                "name": "Pharmaceutical Waste",
                "description": "Expired medicines, chemotherapy drugs",
                "color": "#2F4F4F",
                "bin_id": 4
            }
        }

    async def classify_with_gemini(self, image: Image.Image) -> Dict[str, Any]:
        """Classify medical waste using Google Gemini AI"""
        if not gemini_model:
            return {
                "category": "yellow",
                "confidence": 0.5,
                "reasoning": "Gemini AI not configured - defaulting to General Biomedical Waste",
                "bin_recommendation": self.waste_categories["yellow"]
            }

        try:
            # Convert PIL Image to bytes for Gemini
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            prompt = """
            Analyze this medical waste image and classify it into one of these categories:
            
            1. YELLOW (General Biomedical): Pathological waste, body parts, tissues, blood-soaked materials
            2. RED (Infectious): Highly infectious materials, microbiological cultures, lab waste
            3. BLUE (Sharp Objects): Needles, scalpels, broken glass, sharp instruments  
            4. BLACK (Pharmaceutical): Expired medicines, chemotherapy drugs, pharmaceutical waste
            
            Respond with JSON format:
            {
                "category": "yellow|red|blue|black",
                "confidence": 0.0-1.0,
                "reasoning": "Brief explanation of classification"
            }
            """

            response = gemini_model.generate_content([prompt, image])
            result_text = response.text.strip()
            
            # Parse JSON response
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(result_text)
            category = result.get("category", "yellow")
            
            return {
                "category": category,
                "confidence": result.get("confidence", 0.8),
                "reasoning": result.get("reasoning", "AI classification"),
                "bin_recommendation": self.waste_categories.get(category, self.waste_categories["yellow"])
            }
            
        except Exception as e:
            logger.error(f"Gemini classification error: {str(e)}")
            return {
                "category": "yellow",
                "confidence": 0.5,
                "reasoning": f"Classification failed: {str(e)} - Defaulting to General Biomedical",
                "bin_recommendation": self.waste_categories["yellow"]
            }

# Initialize classifier
classifier = MedicalWasteClassifier()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "gemini_configured": gemini_model is not None,
        "port": os.getenv("PORT", "8000")
    }

@app.post("/classify")
async def classify_waste(file: UploadFile = File(...)):
    """Classify uploaded medical waste image"""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and process image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Classify with Gemini AI
        result = await classifier.classify_with_gemini(image)
        
        # Generate QR code
        qr_data = {
            "waste_id": str(uuid.uuid4()),
            "category": result["category"],
            "timestamp": datetime.now().isoformat(),
            "confidence": result["confidence"]
        }
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
        
        return {
            "success": True,
            "classification": result,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "waste_data": qr_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Classification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

@app.get("/categories")
async def get_waste_categories():
    """Get all waste categories and their information"""
    return {"categories": classifier.waste_categories}

# ESP32 sensor endpoints
@app.post("/sensor/data")
async def receive_sensor_data(sensor_data: dict):
    """Receive data from ESP32 sensors"""
    logger.info(f"Received sensor data: {sensor_data}")
    return {"status": "received", "timestamp": datetime.now().isoformat()}

@app.get("/sensor/status/{bin_id}")
async def get_bin_status(bin_id: int):
    """Get the status of a specific waste bin"""
    return {
        "bin_id": bin_id,
        "status": "operational",
        "fill_level": 25,  # Placeholder
        "last_updated": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)