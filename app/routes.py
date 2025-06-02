# app/routes.py - Optimized version
from flask import Blueprint, render_template, request, jsonify, current_app
import base64
import numpy as np
import cv2
import sys
import os
import threading
import time
from queue import Queue
import gc

# Add the project root to sys.path to import back_end_process
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from back_end_process.detector import detect_objects
from back_end_process.voice_api import speak_detection

main = Blueprint('main', __name__)

# Global variables for performance optimization
detection_queue = Queue(maxsize=3)  # Limit queue size
last_detection_time = 0
detection_cooldown = 1.5  # Minimum seconds between detections
last_detections = []
processing_lock = threading.Lock()

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/detect', methods=['POST'])
def detect():
    global last_detection_time, last_detections
    
    # Check cooldown to prevent overload
    current_time = time.time()
    if current_time - last_detection_time < detection_cooldown:
        return jsonify(last_detections)
    
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400

    try:
        # Decode base64 image with error handling
        header, encoded = data['image'].split(",", 1)
        image_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Failed to decode image'}), 400
            
        # Resize frame for faster processing
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
            print(f"🔄 Resized frame from {width}x{height} to {new_width}x{new_height}")
            
    except Exception as e:
        print(f"❌ Image decoding failed: {str(e)}")
        return jsonify({'error': f'Image decoding failed: {str(e)}'}), 400

    # Process detection in background thread to avoid blocking
    try:
        with processing_lock:
            detections = detect_objects(frame)
            last_detections = detections
            last_detection_time = current_time
            
        print(f"🔍 Detected {len(detections)} objects: {[d['object'] for d in detections]}")
        
        # Send to voice processing asynchronously
        if detections:
            voice_thread = threading.Thread(
                target=process_voice_announcements, 
                args=(detections.copy(),),
                daemon=True
            )
            voice_thread.start()
        
        # Clean up memory
        del frame
        gc.collect()
        
        return jsonify(detections)
        
    except Exception as e:
        print(f"❌ Detection error: {str(e)}")
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

def process_voice_announcements(detections):
    """Process voice announcements with the new system"""
    try:
        if not detections:
            return
            
        # Only announce high-confidence detections
        good_detections = [d for d in detections if d.get('confidence', 0) > 0.65]
        
        if not good_detections:
            return
            
        # Simple announcement for single detection
        if len(good_detections) == 1:
            detection = good_detections[0]
            speak_detection(detection['object'], detection['location'])
            return
        
        # For multiple detections, just announce count and first object
        first_obj = good_detections[0]['object']
        count = len(good_detections)
        
        if count == 2:
            speak_detection("object", f"Two objects detected")
        elif count <= 5:
            speak_detection("object", f"{count} objects detected")
        else:
            speak_detection("object", "Multiple objects detected")
                
    except Exception as e:
        print(f"❌ Voice processing error: {str(e)}")

# Remove the old import
from back_end_process.voice_api import speak_detection

@main.route('/status', methods=['GET'])
def get_status():
    """Get system status information"""
    return jsonify({
        'detection_active': True,
        'last_detection_count': len(last_detections),
        'system_load': 'normal',
        'voice_system': 'active'
    })

@main.route('/test_voice', methods=['POST'])
def test_voice():
    """Test the new voice system"""
    try:
        from back_end_process.voice_api import speak_detection, current_voice_method
        
        success = speak_detection("system", "Voice system working correctly")
        
        return jsonify({
            'success': success,
            'method': current_voice_method.name if current_voice_method else 'None',
            'message': 'Voice test queued' if success else 'Voice test failed or on cooldown'
        })
            
    except Exception as e:
        print(f"❌ Voice test error: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@main.route('/voice_debug', methods=['GET'])
def voice_debug():
    """Debug endpoint to check voice system status"""
    try:
        from back_end_process.voice_api import voice_initialized, voice_queue, voice_thread, last_announcement_time
        import time
        
        return jsonify({
            'voice_initialized': voice_initialized,
            'queue_size': voice_queue.qsize(),
            'thread_alive': voice_thread.is_alive() if voice_thread else False,
            'last_announcement': time.time() - last_announcement_time,
            'queue_maxsize': voice_queue.maxsize,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500