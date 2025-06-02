# app/__init__.py - Updated with optimized configuration
from flask import Flask
from .routes import main
from back_end_process.voice_api import voice_bp
import os
import gc
import threading
import time

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config

def create_app(config_name='development'):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Validate configuration
    config_issues = config.validate_config()
    if config_issues:
        print("⚠️ Configuration issues found:")
        for issue in config_issues:
            print(f"   - {issue}")
    
    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(voice_bp)
    
    # Add configuration to app context
    app.config['AI_VISION_CONFIG'] = config
    
    # Setup performance monitoring if enabled
    if config.LOG_PERFORMANCE:
        setup_performance_monitoring(app, config)
    
    # Setup memory cleanup if enabled
    if config.ENABLE_GARBAGE_COLLECTION:
        setup_memory_cleanup(config.MEMORY_CLEANUP_INTERVAL)
    
    # Add health check route
    @app.route('/health')
    def health_check():
        from back_end_process.detector import get_detection_stats
        from back_end_process.voice_api import voice_bp
        
        stats = get_detection_stats()
        
        return {
            'status': 'healthy',
            'detection_stats': stats,
            'config': {
                'detection_confidence': config.DETECTION_CONFIDENCE,
                'max_image_width': config.MAX_IMAGE_WIDTH,
                'voice_queue_size': config.VOICE_QUEUE_SIZE
            }
        }
    
    print("✅ Flask app created with optimized configuration")
    return app

def setup_performance_monitoring(app, config):
    """Setup performance monitoring"""
    @app.before_request
    def before_request():
        from flask import g
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        from flask import g, request
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            if duration > 1.0:  # Log slow requests
                print(f"⏱️ Slow request: {request.endpoint} took {duration:.2f}s")
        return response

def setup_memory_cleanup(interval_seconds):
    """Setup automatic memory cleanup"""
    def memory_cleanup_worker():
        while True:
            time.sleep(interval_seconds)
            try:
                collected = gc.collect()
                if collected > 0:
                    print(f"🧹 Garbage collected {collected} objects")
            except Exception as e:
                print(f"❌ Memory cleanup error: {str(e)}")
    
    cleanup_thread = threading.Thread(target=memory_cleanup_worker, daemon=True)
    cleanup_thread.start()
    print(f"🧹 Memory cleanup scheduled every {interval_seconds} seconds")