#!/usr/bin/env python3
"""
Simple Medical Waste Classification Server (No Docker Required)
Run directly with Python for testing
"""

import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
from PIL import Image
import io
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Sortyx Medical Waste Classifier")

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Mount static files and templates
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except:
    print("Warning: Static/templates directories not found. Web interface will be limited.")
    templates = None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with web interface"""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("""
        <h1>Sortyx Medical Waste Classifier</h1>
        <h2>API is running!</h2>
        <p>Upload an image to classify medical waste:</p>
        <form action="/classify" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept="image/*" required>
            <button type="submit">Classify Waste</button>
        </form>
        """)

@app.post("/classify")
async def classify_waste(file: UploadFile = File(...)):
    """Classify medical waste using Gemini AI"""
    try:
        # Read and process image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Classify with Gemini
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = """
        You are a medical waste classification expert. Analyze this image and classify the waste item.
        
        Medical Waste Categories:
        1. **General Biomedical Waste (Yellow Bin)**: Non-infectious items like gloves, gowns, packaging
        2. **Infectious Waste (Red Bin)**: Blood-soaked items, cultures, pathological waste  
        3. **Sharp Waste (Blue Bin)**: Needles, syringes, scalpels, broken glass
        4. **Pharmaceutical Waste (Black Bin)**: Expired medicines, chemotherapy drugs, antibiotics
        
        Respond with:
        - Classification: [Yellow Bin/Red Bin/Blue Bin/Black Bin]
        - Item: [Item name]
        - Reason: [Brief explanation]
        
        Example: "Classification: Blue Bin, Item: Syringe with needle, Reason: Sharp medical instrument"
        """
        
        response = model.generate_content([prompt, image])
        result = response.text
        
        # Parse result
        lines = result.split('\n')
        classification = "Unknown"
        item_name = "Unknown Item"
        reason = "Unable to classify"
        
        for line in lines:
            if 'Classification:' in line:
                classification = line.split('Classification:')[1].strip()
            elif 'Item:' in line:
                item_name = line.split('Item:')[1].strip()
            elif 'Reason:' in line:
                reason = line.split('Reason:')[1].strip()
        
        return JSONResponse({
            "status": "success",
            "classification": classification,
            "item_name": item_name,
            "reason": reason,
            "full_response": result
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Sortyx Medical Waste Classifier"}

if __name__ == "__main__":
    print("🚀 Starting Sortyx Medical Waste Classification Server...")
    print("📱 Web Interface: http://localhost:8000")
    print("🔬 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True
    )