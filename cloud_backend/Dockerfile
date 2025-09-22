# Use pre-built Ultralytics image with YOLO already installed
FROM ultralytics/ultralytics:latest-cpu

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install ALL required dependencies at once (YOLO/ultralytics already included in base image)
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    jinja2==3.1.2 \
    google-generativeai==0.3.2 \
    pillow==10.0.1 \
    numpy==1.24.3 \
    opencv-python-headless==4.8.1.78 \
    qrcode[pil]==7.4.2 \
    firebase-admin==6.2.0 \
    asyncpg==0.29.0 \
    redis==5.0.1 \
    python-dotenv==1.0.0 \
    aiofiles==23.2.1 \
    requests==2.31.0 \
    websockets==12.0 \
    pydantic==2.5.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/static/uploads /app/models /app/templates

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]