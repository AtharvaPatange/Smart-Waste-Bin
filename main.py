#!/usr/bin/env python3
"""
Railway-Optimized Medical Waste Classification Backend
Root level deployment for Railway
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

# Web Framework
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

# AI/ML Libraries
import numpy as np
from PIL import Image
import google.generativeai as genai

# Utilities
import qrcode
from dotenv import load_dotenv

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates (create inline since Railway has directory issues)
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main web interface"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sortyx Medical Waste Classification</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Arial', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
            .container { background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.1); max-width: 600px; width: 90%; }
            .logo { text-align: center; margin-bottom: 30px; }
            .logo h1 { color: #4a5568; font-size: 2.5rem; margin-bottom: 10px; }
            .logo p { color: #718096; font-size: 1.1rem; }
            .upload-area { border: 3px dashed #cbd5e0; border-radius: 12px; padding: 40px; text-align: center; margin: 30px 0; transition: all 0.3s ease; cursor: pointer; }
            .upload-area:hover { border-color: #667eea; background-color: #f7fafc; }
            .upload-icon { font-size: 4rem; color: #cbd5e0; margin-bottom: 20px; }
            .file-input { display: none; }
            .upload-text { color: #4a5568; font-size: 1.1rem; margin-bottom: 10px; }
            .upload-subtext { color: #a0aec0; font-size: 0.9rem; }
            .classify-btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 15px 30px; border-radius: 8px; font-size: 1.1rem; cursor: pointer; width: 100%; margin-top: 20px; transition: all 0.3s ease; }
            .classify-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4); }
            .classify-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
            .result { margin-top: 30px; padding: 25px; border-radius: 12px; display: none; }
            .result.success { background: #f0fff4; border: 2px solid #68d391; }
            .result.error { background: #fed7d7; border: 2px solid #fc8181; }
            .category { display: flex; align-items: center; margin: 15px 0; }
            .category-color { width: 30px; height: 30px; border-radius: 50%; margin-right: 15px; }
            .qr-code { text-align: center; margin-top: 20px; }
            .qr-code img { max-width: 150px; border-radius: 8px; }
            .loading { display: none; text-align: center; margin: 20px 0; }
            .loading-spinner { border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <h1>🗂️ Sortyx</h1>
                <p>Medical Waste Classification System</p>
            </div>

            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📸</div>
                <div class="upload-text">Click to upload medical waste image</div>
                <div class="upload-subtext">Supports JPG, PNG, WebP formats</div>
                <input type="file" id="fileInput" class="file-input" accept="image/*">
            </div>

            <button class="classify-btn" onclick="classifyWaste()" id="classifyBtn" disabled>
                Classify Medical Waste
            </button>

            <div class="loading" id="loading">
                <div class="loading-spinner"></div>
                <div>Analyzing with AI...</div>
            </div>

            <div class="result" id="result">
                <div id="resultContent"></div>
            </div>
        </div>

        <script>
            let selectedFile = null;

            document.getElementById('fileInput').addEventListener('change', function(e) {
                selectedFile = e.target.files[0];
                if (selectedFile) {
                    document.getElementById('classifyBtn').disabled = false;
                    document.querySelector('.upload-text').textContent = selectedFile.name;
                }
            });

            async function classifyWaste() {
                if (!selectedFile) return;

                const formData = new FormData();
                formData.append('file', selectedFile);

                document.getElementById('loading').style.display = 'block';
                document.getElementById('result').style.display = 'none';

                try {
                    const response = await fetch('/classify', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();
                    displayResult(data);
                } catch (error) {
                    displayError('Classification failed: ' + error.message);
                }

                document.getElementById('loading').style.display = 'none';
            }

            function displayResult(data) {
                const result = document.getElementById('result');
                const classification = data.classification;
                const category = classification.bin_recommendation;

                result.className = 'result success';
                result.innerHTML = `
                    <h3>Classification Result</h3>
                    <div class="category">
                        <div class="category-color" style="background-color: ${category.color}"></div>
                        <div>
                            <strong>${category.name}</strong><br>
                            <small>${category.description}</small>
                        </div>
                    </div>
                    <p><strong>Confidence:</strong> ${Math.round(classification.confidence * 100)}%</p>
                    <p><strong>Reasoning:</strong> ${classification.reasoning}</p>
                    <div class="qr-code">
                        <p><strong>QR Code for Tracking:</strong></p>
                        <img src="${data.qr_code}" alt="QR Code">
                    </div>
                `;
                result.style.display = 'block';
            }

            function displayError(message) {
                const result = document.getElementById('result');
                result.className = 'result error';
                result.innerHTML = `<h3>Error</h3><p>${message}</p>`;
                result.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Create necessary directories
os.makedirs("static", exist_ok=True)

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
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        result = await classifier.classify_with_gemini(image)
        
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)