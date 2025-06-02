# config.py - System Configuration
import os

class OptimizedConfig:
    """Configuration class for optimized AI Vision System"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ai-vision-system-key-2025'
    DEBUG = True
    THREADED = True
    
    # Detection Configuration
    DETECTION_CONFIDENCE = 0.6      # YOLO confidence threshold
    DETECTION_IOU = 0.45           # IoU threshold for Non-Maximum Suppression
    MAX_DETECTIONS = 20            # Maximum detections per frame
    DETECTION_COOLDOWN = 1.5       # Minimum seconds between detections
    
    # Image Processing Configuration
    MAX_IMAGE_WIDTH = 640          # Maximum image width for processing
    IMAGE_QUALITY = 0.6            # JPEG quality for transmission
    ENABLE_IMAGE_RESIZE = True     # Enable automatic image resizing
    
    # Voice Configuration
    VOICE_RATE = 160              # Speech rate (words per minute)
    VOICE_VOLUME = 0.8            # Voice volume (0.0 to 1.0)
    VOICE_QUEUE_SIZE = 10         # Maximum voice announcements in queue
    VOICE_TIMEOUT = 0.5           # Timeout for adding to voice queue
    
    # Performance Configuration
    ENABLE_GARBAGE_COLLECTION = True  # Enable automatic garbage collection
    MEMORY_CLEANUP_INTERVAL = 30      # Seconds between memory cleanup
    LOG_PERFORMANCE = True            # Enable performance logging
    
    # Object Detection Labels (reduced for performance)
    IMPORTANT_LABELS = {
        "person", "car", "bus", "bicycle", "motorcycle",
        "dog", "cat", "bird", "horse",
        "chair", "couch", "bed", "dining table", "toilet",
        "bottle", "cup", "wine glass", "bowl",
        "book", "laptop", "cell phone", "tv", "remote",
        "door", "stairs", "traffic light", "stop sign"
    }
    
    # Grid Positions
    GRID_POSITIONS = [
        ["top left", "top center", "top right"],
        ["middle left", "center", "middle right"],
        ["bottom left", "bottom center", "bottom right"]
    ]
    
    @classmethod
    def get_model_path(cls):
        """Get the path to the YOLO model"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "models", "best.pt")
    
    @classmethod
    def get_fallback_model(cls):
        """Get fallback model if custom model not found"""
        return "yolov8n.pt"
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        issues = []
        
        if cls.DETECTION_CONFIDENCE < 0.1 or cls.DETECTION_CONFIDENCE > 1.0:
            issues.append("Detection confidence should be between 0.1 and 1.0")
            
        if cls.MAX_IMAGE_WIDTH < 320 or cls.MAX_IMAGE_WIDTH > 1920:
            issues.append("Max image width should be between 320 and 1920")
            
        if cls.VOICE_RATE < 50 or cls.VOICE_RATE > 300:
            issues.append("Voice rate should be between 50 and 300")
            
        return issues

# Development Configuration (inherits from OptimizedConfig)
class DevelopmentConfig(OptimizedConfig):
    DEBUG = True
    LOG_PERFORMANCE = True
    DETECTION_CONFIDENCE = 0.5  # Lower confidence for testing

# Production Configuration (inherits from OptimizedConfig) 
class ProductionConfig(OptimizedConfig):
    DEBUG = False
    LOG_PERFORMANCE = False
    DETECTION_CONFIDENCE = 0.7  # Higher confidence for production

# Configuration factory
def get_config(env='development'):
    """Get configuration based on environment"""
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'default': OptimizedConfig
    }
    
    return configs.get(env, OptimizedConfig)