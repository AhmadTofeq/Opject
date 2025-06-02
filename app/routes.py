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
    """Process voice announcements in background thread"""
    try:
        # Group similar objects to avoid repetitive announcements
        object_counts = {}
        locations = {}
        
        for detection in detections:
            obj = detection['object']
            loc = detection['location']
            
            if obj not in object_counts:
                object_counts[obj] = 0
                locations[obj] = []
            
            object_counts[obj] += 1
            if loc not in locations[obj]:
                locations[obj].append(loc)
        
        # Create smart announcements
        announcements = []
        
        for obj, count in object_counts.items():
            if count == 1:
                announcements.append(f"{obj} in {locations[obj][0]}")
            else:
                loc_str = ", ".join(locations[obj][:2])  # Max 2 locations
                if len(locations[obj]) > 2:
                    loc_str += " and other areas"
                announcements.append(f"{count} {obj}s detected in {loc_str}")
        
        # Speak each announcement with small delay
        for announcement in announcements[:3]:  # Limit to 3 announcements
            try:
                speak_detection("object", announcement)
                time.sleep(0.3)  # Small delay between announcements
            except Exception as e:
                print(f"❌ Voice announcement failed: {str(e)}")
                
    except Exception as e:
        print(f"❌ Voice processing error: {str(e)}")

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
    """Test voice system"""
    try:
        speak_detection("system", "Voice system test successful")
        return jsonify({'status': 'success', 'message': 'Voice test completed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500