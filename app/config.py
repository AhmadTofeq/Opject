# app/config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # YOLO Model Configuration
    MODEL_PATH = os.path.join('models', 'best.pt')
    CONFIDENCE_THRESHOLD = 0.5
    
    # Voice Configuration
    VOICE_ENABLED = True
    VOICE_SPEED = 150
    VOICE_VOLUME = 0.9
    
    # Detection Configuration
    DETECTION_INTERVAL = 2000  # milliseconds
    MAX_DETECTIONS_PER_FRAME = 10
    
    # Grid Configuration
    GRID_SIZE = 3  # 3x3 grid
    
    # Flask Configuration
    DEBUG = True
    THREADED = True