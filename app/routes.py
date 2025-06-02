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
    """Process voice announcements with smart filtering"""
    try:
        if not detections:
            return
            
        # Only announce if we have significant detections
        high_confidence_detections = [d for d in detections if d.get('confidence', 0) > 0.7]
        
        if not high_confidence_detections:
            return
            
        # For single high-confidence detection
        if len(high_confidence_detections) == 1:
            detection = high_confidence_detections[0]
            smart_speak_detection(detection['object'], detection['location'])
            return
        
        # For multiple detections, create summary
        object_types = set()
        for detection in high_confidence_detections[:3]:  # Max 3 objects
            object_types.add(detection['object'])
        
        if len(object_types) == 1:
            obj_name = list(object_types)[0]
            count = len(high_confidence_detections)
            if count > 1:
                smart_speak_detection("object", f"{count} {obj_name}s detected")
            else:
                smart_speak_detection(obj_name, high_confidence_detections[0]['location'])
        else:
            # Multiple object types
            obj_list = list(object_types)[:2]  # Max 2 types
            if len(obj_list) == 2:
                smart_speak_detection("object", f"{obj_list[0]} and {obj_list[1]} detected")
            else:
                smart_speak_detection("object", f"Multiple objects detected")
                
    except Exception as e:
        print(f"❌ Voice processing error: {str(e)}")

# Import the new function
from back_end_process.voice_api import smart_speak_detection

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
    """Test voice system with better error reporting"""
    try:
        from back_end_process.voice_api import smart_speak_detection, voice_initialized
        
        if not voice_initialized:
            return jsonify({
                'status': 'error', 
                'message': 'Voice system not initialized'
            }), 500
        
        success = smart_speak_detection("system", "Voice test successful")
        
        return jsonify({
            'status': 'success' if success else 'warning',
            'message': 'Voice test queued' if success else 'Voice test skipped (cooldown or queue full)'
        }), 200
            
    except Exception as e:
        print(f"❌ Voice test error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Voice test failed: {str(e)}'
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