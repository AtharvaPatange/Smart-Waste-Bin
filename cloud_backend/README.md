# Sortyx Medical Waste Classification - Cloud Edition

A complete cloud-based medical waste classification system that replaces Raspberry Pi hardware with scalable web infrastructure.

## 🎯 Features

- **AI-Powered Classification**: Google Gemini LLM for accurate medical waste categorization
- **Real-time Processing**: WebSocket-based real-time communication
- **ESP32 Integration**: Wireless sensor monitoring for bin levels
- **QR Code Tracking**: Disposal tracking and compliance
- **Cloud Scalable**: Deploy on AWS, GCP, Azure, or Heroku
- **Web Interface**: Modern responsive UI accessible from any device

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Web Browser   │───▶│  FastAPI Backend │───▶│   Google Gemini │
│   (Camera UI)   │    │  (Classification)│    │      (AI)       │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                          
                              ▼                          
                    ┌─────────────────┐    
                    │                 │    
                    │   PostgreSQL    │    
                    │   (Database)    │    
                    │                 │    
                    └─────────────────┘    
                              ▲                          
                              │                          
┌─────────────────┐    ┌─────────────────┐              
│                 │    │                 │              
│     ESP32       │───▶│  Sensor APIs    │              
│  (Bin Sensors)  │    │  (Data Upload)  │              
│                 │    │                 │              
└─────────────────┘    └─────────────────┘              
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd cloud_backend
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Add YOLO Models

Place your trained models in the `models/` directory:
- `yolov8n.pt` (detection model)
- `best.pt` (classification model)

### 5. Run Development Server

```bash
python app.py
```

Visit `http://localhost:8000` to access the web interface.

## 🌐 Cloud Deployment

### Automatic Deployment

Use the provided deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

### Manual Deployment Options

#### Heroku
```bash
heroku create your-app-name
git push heroku main
```

#### Docker
```bash
docker-compose up -d
```

#### AWS (ECS/Fargate)
```bash
docker build -t sortyx-medical-waste .
# Push to ECR and deploy via ECS
```

## 🔧 ESP32 Setup

### Hardware Requirements
- ESP32 DevKit
- 4x HC-SR04 Ultrasonic sensors
- DHT22 temperature/humidity sensor
- 4x WS2812B RGB LEDs
- Buzzer

### Arduino Code Setup
1. Install required libraries:
   - WiFi
   - HTTPClient
   - ArduinoJson
   - DHT sensor library
   - Adafruit NeoPixel

2. Configure WiFi and server URL in `esp32_sensor_controller.ino`
3. Upload to ESP32

### Sensor Wiring
```
ESP32 Pin  | Component
-----------|----------
12, 13     | Ultrasonic 1 (Yellow bin)
14, 27     | Ultrasonic 2 (Red bin)
26, 25     | Ultrasonic 3 (Blue bin)
33, 32     | Ultrasonic 4 (Black bin)
4          | DHT22
5          | NeoPixel LEDs
18         | Buzzer
```

## 📱 Web Interface

The web interface provides:
- **Live Camera Feed**: Real-time camera access via WebRTC
- **Classification Results**: Instant medical waste categorization
- **QR Code Generation**: Tracking codes for compliance
- **Bin Level Monitoring**: Real-time sensor data from ESP32
- **Statistics Dashboard**: Daily/weekly analytics

## 🏥 Medical Waste Categories

| Category | Color | Description |
|----------|--------|-------------|
| General-Biomedical | Yellow | Non-hazardous medical items |
| Infectious | Red | Blood/fluid contaminated items |
| Sharp | Blue | Needles, scalpels, sharp objects |
| Pharmaceutical | Black | Medicines, drug containers |

## 🔌 API Endpoints

### Classification
- `POST /classify` - Classify medical waste from image
- `GET /stats` - Get classification statistics

### Sensor Data
- `POST /sensor/update` - Receive ESP32 sensor data
- `GET /bins/status` - Get current bin levels

### System
- `GET /health` - Health check
- `WebSocket /ws` - Real-time updates

## 🛠️ Configuration

### Environment Variables
```bash
GEMINI_API_KEY=your_gemini_api_key
POSTGRES_PASSWORD=secure_password
ENVIRONMENT=production
ALLOWED_HOSTS=your-domain.com
```

### Camera Settings
- Resolution: 1280x720 (configurable)
- Format: WebRTC/getUserMedia
- Frame rate: 30fps

### Model Requirements
- YOLOv8n for object detection
- Custom trained model for medical waste classification
- Gemini 1.5 Flash for LLM classification

## 📊 Production Considerations

### Performance
- **Processing Time**: ~2-3 seconds per classification
- **Concurrent Users**: Scales with cloud resources
- **Storage**: PostgreSQL for data, cloud storage for images

### Security
- HTTPS/WSS encryption
- API rate limiting
- Input validation and sanitization
- CORS configuration

### Monitoring
- Health check endpoints
- Error tracking and logging
- Performance metrics
- Automated alerts for bin levels

## 🔧 Troubleshooting

### Common Issues

#### Camera Not Working
- Check browser permissions
- Ensure HTTPS for production
- Verify camera access in browser

#### Classification Errors
- Verify Gemini API key
- Check model files in `/models` directory
- Monitor server logs for errors

#### ESP32 Connection Issues
- Verify WiFi credentials
- Check server URL configuration
- Monitor serial output for debugging

#### Deployment Problems
- Check environment variables
- Verify cloud provider credentials
- Review deployment logs

### Debug Mode
```bash
export DEBUG=true
python app.py
```

## 📈 Scaling for Production

### High Availability
- Load balancer configuration
- Multiple server instances
- Database replication
- Redis for session management

### Performance Optimization
- CDN for static assets
- Image compression and caching
- Database query optimization
- Async processing for heavy tasks

### Cost Optimization
- Auto-scaling based on load
- Serverless functions for classification
- Efficient resource allocation
- Usage monitoring and alerts

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🆘 Support

- 📧 Email: support@sortyx.com
- 📱 Phone: +1-XXX-XXX-XXXX
- 💬 Discord: [Join our community](discord-link)
- 📚 Documentation: [Full docs](docs-link)

## 🎯 Roadmap

- [ ] Mobile app for iOS/Android
- [ ] Advanced analytics and reporting
- [ ] Integration with hospital management systems
- [ ] Multi-language support
- [ ] Voice-guided classification
- [ ] Automated compliance reporting