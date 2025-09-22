#!/usr/bin/env python3
"""
Cloud-based Medical Waste Classification Backend
FastAPI server for production-ready medical waste sorting system
Handles: Object Detection, LLM Classification, QR Generation, ESP32 Communication
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
import cv2
import numpy as np
from ultralytics import YOLO
import google.generativeai as genai
from PIL import Image
import qrcode

# Firebase for real-time database
import firebase_admin
from firebase_admin import credentials, db

# Environment and Configuration
from dotenv import load_dotenv
import uvicorn
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Sortyx Medical Waste Classification API",
    description="Cloud-based medical waste classification and management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Pydantic models for API requests/responses
class ClassificationRequest(BaseModel):
    image_base64: str
    bin_id: Optional[str] = None
    location: Optional[str] = "default"

class ClassificationResponse(BaseModel):
    classification: str
    confidence: float
    item_name: str
    bin_color: str
    qr_code: Optional[str] = None
    explanation: str
    timestamp: str
    processing_time: float

class SensorData(BaseModel):
    sensor_id: str
    distance: float
    bin_level: float
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    location: str
    timestamp: str

class BinStatus(BaseModel):
    bin_id: str
    level: float
    status: str  # "normal", "warning", "full"
    last_updated: str

# Global variables for AI models
yolo_detection_model = None
yolo_classification_model = None
connected_websockets: List[WebSocket] = []

# Medical waste categories configuration
MEDICAL_WASTE_CATEGORIES = {
    "General-Biomedical": {
        "color": "Yellow",
        "description": "Non-hazardous medical items like containers, packaging, non-contaminated materials",
        "disposal_code": "MW-GB"
    },
    "Infectious": {
        "color": "Red", 
        "description": "Items contaminated with bodily fluids, blood, pathological waste",
        "disposal_code": "MW-INF"
    },
    "Sharp": {
        "color": "Blue",
        "description": "Needles, syringes, scalpels, broken glass, sharp objects",
        "disposal_code": "MW-SH"
    },
    "Pharmaceutical": {
        "color": "Black",
        "description": "Expired medicines, drug containers, pharmaceutical waste",
        "disposal_code": "MW-PH"
    }
}

class MedicalWasteClassifier:
    """Enhanced medical waste classification system"""
    
    def __init__(self):
        self.load_models()
        self.configure_gemini()
        self.stats = {
            'total_classifications': 0,
            'category_counts': {category: 0 for category in MEDICAL_WASTE_CATEGORIES.keys()},
            'daily_stats': {}
        }
    
    def load_models(self):
        """Load YOLO models for detection and classification"""
        try:
            model_dir = Path("models")
            
            # Load detection model
            detection_model_path = model_dir / "yolov8n.pt"
            if detection_model_path.exists():
                global yolo_detection_model
                yolo_detection_model = YOLO(str(detection_model_path))
                logger.info("YOLO detection model loaded successfully")
            else:
                logger.warning(f"Detection model not found at {detection_model_path}")
            
            # Load classification model  
            classification_model_path = model_dir / "best.pt"
            if classification_model_path.exists():
                global yolo_classification_model
                yolo_classification_model = YOLO(str(classification_model_path))
                logger.info("YOLO classification model loaded successfully")
            else:
                logger.warning(f"Classification model not found at {classification_model_path}")
                
        except Exception as e:
            logger.error(f"Error loading YOLO models: {e}")
    
    def configure_gemini(self):
        """Configure Google Gemini API"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                logger.info("Gemini API configured successfully")
            else:
                logger.warning("GEMINI_API_KEY not found in environment variables")
        except Exception as e:
            logger.error(f"Error configuring Gemini API: {e}")
    
    def detect_objects(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect objects in image using YOLO"""
        if yolo_detection_model is None:
            return {"error": "Detection model not loaded"}
        
        try:
            results = yolo_detection_model.predict(image, conf=0.25, iou=0.45)
            
            detections = []
            for r in results:
                if hasattr(r, 'boxes') and r.boxes is not None:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        class_id = int(box.cls[0])
                        class_name = r.names[class_id]
                        confidence = box.conf[0].item()
                        
                        detections.append({
                            "bbox": [x1, y1, x2, y2],
                            "class_name": class_name,
                            "class_id": class_id,
                            "confidence": confidence,
                            "area": (x2 - x1) * (y2 - y1)
                        })
            
            return {"detections": detections, "count": len(detections)}
            
        except Exception as e:
            logger.error(f"Error in object detection: {e}")
            return {"error": str(e)}
    
    def classify_with_gemini(self, image: np.ndarray) -> Dict[str, Any]:
        """Classify medical waste using Gemini AI"""
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # Gemini prompt for medical waste classification
            prompt = """
            You are an expert medical waste classifier. Analyze the image and classify ANY visible item into one of these 4 medical waste categories:

            **CLASSIFICATION CATEGORIES:**
            1. **General-Biomedical**: Non-hazardous medical items (plastic containers, non-contaminated gloves, packaging, medical devices, bottles, tubes, masks, general medical supplies)
            2. **Infectious**: Items contaminated with bodily fluids (blood-soaked items, used bandages, contaminated PPE, specimen containers, culture dishes, pathological waste)  
            3. **Sharp**: Items that can cut or puncture (needles, syringes, scalpels, broken glass, lancets, surgical blades)
            4. **Pharmaceutical**: Medicine-related items (pill bottles, drug vials, expired medications, vaccine containers, IV drug bags)

            **INSTRUCTIONS:**
            - You MUST choose one of the 4 categories above
            - If the item doesn't clearly fit a specific category, classify it as "General-Biomedical"
            - Do NOT respond with "unknown" or "not medical waste"
            - Focus on any medical or healthcare-related item in the image

            **RESPONSE FORMAT:**
            Category: [Item Name]. [Brief explanation why it belongs in this category.]

            **EXAMPLES:**
            - "General-Biomedical: Plastic Medical Container. Non-contaminated plastic medical supplies go in the yellow bin."
            - "Infectious: Blood-Soaked Gauze. Contains bodily fluids requiring infectious waste protocols."
            - "Sharp: Syringe with Needle. Sharp objects must go in puncture-resistant containers."
            - "Pharmaceutical: Medicine Bottle. Pharmaceutical waste requires specialized disposal."

            Analyze the image now and provide your classification:
            """
            
            # Generate content using Gemini
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, pil_image])
            
            if response and response.text:
                return self.parse_gemini_response(response.text)
            else:
                return self.get_fallback_classification()
                
        except Exception as e:
            logger.error(f"Error in Gemini classification: {e}")
            return self.get_fallback_classification()
    
    def parse_gemini_response(self, text: str) -> Dict[str, Any]:
        """Parse Gemini response and extract classification details"""
        text_lower = text.lower()
        
        # Default classification
        classification = "General-Biomedical"
        explanation = text
        item_name = "Medical Item"
        
        # Enhanced classification detection
        if any(word in text_lower for word in ["pharmaceutical", "medicine", "drug", "medication", "pill", "vaccine"]):
            classification = "Pharmaceutical"
        elif any(word in text_lower for word in ["infectious", "blood", "bodily fluid", "pathological", "culture", "contaminated"]):
            classification = "Infectious"
        elif any(word in text_lower for word in ["sharp", "needle", "syringe", "scalpel", "blade", "lancet", "glass"]):
            classification = "Sharp"
        elif any(word in text_lower for word in ["general", "biomedical", "plastic", "container", "bag", "tube", "mask"]):
            classification = "General-Biomedical"
        
        # Extract item name
        if ":" in text:
            try:
                parts = text.split(":", 1)
                if len(parts) > 1:
                    item_and_explanation = parts[1].strip()
                    first_sentence_end = item_and_explanation.find(".")
                    if first_sentence_end != -1:
                        item_name = item_and_explanation[:first_sentence_end].strip()
                    else:
                        item_name = item_and_explanation[:50].strip()
            except:
                pass
        
        # Get category details
        category_info = MEDICAL_WASTE_CATEGORIES.get(classification, MEDICAL_WASTE_CATEGORIES["General-Biomedical"])
        
        return {
            "classification": classification,
            "item_name": item_name,
            "explanation": explanation,
            "bin_color": category_info["color"],
            "disposal_code": category_info["disposal_code"],
            "confidence": 0.85  # High confidence for Gemini classifications
        }
    
    def get_fallback_classification(self) -> Dict[str, Any]:
        """Fallback classification when AI fails"""
        category_info = MEDICAL_WASTE_CATEGORIES["General-Biomedical"]
        return {
            "classification": "General-Biomedical",
            "item_name": "Medical Item",
            "explanation": "Classified as general biomedical waste for safety",
            "bin_color": category_info["color"],
            "disposal_code": category_info["disposal_code"],
            "confidence": 0.50
        }
    
    def generate_qr_code(self, classification_data: Dict[str, Any]) -> str:
        """Generate QR code for disposal tracking"""
        try:
            qr_data = {
                "id": str(uuid.uuid4()),
                "classification": classification_data["classification"],
                "item": classification_data["item_name"],
                "bin_color": classification_data["bin_color"],
                "disposal_code": classification_data["disposal_code"],
                "timestamp": datetime.now().isoformat(),
                "facility": "Sortyx Medical Facility"
            }
            
            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)
            
            # Generate QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            qr_image.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{qr_base64}"
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None

# Initialize the classifier
classifier = MedicalWasteClassifier()

# API Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": {
            "yolo_detection": yolo_detection_model is not None,
            "yolo_classification": yolo_classification_model is not None,
            "gemini_configured": bool(os.getenv('GEMINI_API_KEY'))
        }
    }

@app.post("/classify", response_model=ClassificationResponse)
async def classify_medical_waste(request: ClassificationRequest, background_tasks: BackgroundTasks):
    """Main classification endpoint"""
    start_time = time.time()
    
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_base64.split(',')[1] if ',' in request.image_base64 else request.image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Classify using Gemini AI
        classification_result = classifier.classify_with_gemini(image)
        
        # Generate QR code
        qr_code = classifier.generate_qr_code(classification_result)
        
        # Update statistics
        classifier.stats['total_classifications'] += 1
        classifier.stats['category_counts'][classification_result['classification']] += 1
        
        processing_time = time.time() - start_time
        
        # Notify connected WebSocket clients
        background_tasks.add_task(notify_websocket_clients, {
            "type": "classification_complete",
            "data": classification_result
        })
        
        return ClassificationResponse(
            classification=classification_result["classification"],
            confidence=classification_result["confidence"],
            item_name=classification_result["item_name"],
            bin_color=classification_result["bin_color"],
            qr_code=qr_code,
            explanation=classification_result["explanation"],
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

@app.post("/sensor/update")
async def update_sensor_data(sensor_data: SensorData):
    """Receive sensor data from ESP32"""
    try:
        # Process sensor data
        bin_status = process_sensor_data(sensor_data)
        
        # Notify WebSocket clients of sensor updates
        await notify_websocket_clients({
            "type": "sensor_update",
            "data": {
                "sensor_id": sensor_data.sensor_id,
                "bin_level": sensor_data.bin_level,
                "status": bin_status["status"]
            }
        })
        
        return {"status": "success", "bin_status": bin_status}
        
    except Exception as e:
        logger.error(f"Sensor update error: {e}")
        raise HTTPException(status_code=500, detail=f"Sensor update failed: {str(e)}")

@app.get("/bins/status")
async def get_bin_status():
    """Get current status of all bins"""
    try:
        # Mock bin status - replace with real database queries
        bins = [
            {"bin_id": "yellow_bin", "level": 45, "status": "normal", "last_updated": datetime.now().isoformat()},
            {"bin_id": "red_bin", "level": 78, "status": "warning", "last_updated": datetime.now().isoformat()},
            {"bin_id": "blue_bin", "level": 23, "status": "normal", "last_updated": datetime.now().isoformat()},
            {"bin_id": "black_bin", "level": 91, "status": "full", "last_updated": datetime.now().isoformat()}
        ]
        return {"bins": bins, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Get bin status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_statistics():
    """Get system statistics"""
    return {
        "total_classifications": classifier.stats['total_classifications'],
        "category_breakdown": classifier.stats['category_counts'],
        "daily_stats": classifier.stats['daily_stats'],
        "timestamp": datetime.now().isoformat()
    }

# WebSocket for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    connected_websockets.append(websocket)
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
        logger.info("WebSocket client disconnected")

async def notify_websocket_clients(message: Dict[str, Any]):
    """Send message to all connected WebSocket clients"""
    if not connected_websockets:
        return
        
    for websocket in connected_websockets.copy():
        try:
            await websocket.send_json(message)
        except:
            connected_websockets.remove(websocket)

def process_sensor_data(sensor_data: SensorData) -> Dict[str, Any]:
    """Process sensor data and determine bin status"""
    level = sensor_data.bin_level
    
    if level >= 90:
        status = "full"
    elif level >= 75:
        status = "warning"  
    else:
        status = "normal"
    
    return {
        "bin_id": sensor_data.sensor_id,
        "level": level,
        "status": status,
        "last_updated": sensor_data.timestamp
    }

if __name__ == "__main__":
    # Create necessary directories
    Path("models").mkdir(exist_ok=True)
    Path("static").mkdir(exist_ok=True) 
    Path("templates").mkdir(exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )