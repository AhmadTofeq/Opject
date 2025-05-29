# app/routes.py
from flask import Blueprint, render_template, request, jsonify, current_app
import base64
import numpy as np
import cv2
import requests
import sys
import os

# Add the project root to sys.path to import back_end_process
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from back_end_process.detector import detect_objects

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/detect', methods=['POST'])
def detect():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400

    try:
        # Decode base64 image
        header, encoded = data['image'].split(",", 1)
        image_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Failed to decode image'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Image decoding failed: {str(e)}'}), 400

    # Get detections from YOLO model
    try:
        detections = detect_objects(frame)
        print(f"🔍 Detected {len(detections)} objects: {detections}")
    except Exception as e:
        print(f"❌ Detection error: {str(e)}")
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

    # Send each detection to voice API
    for obj in detections:
        try:
            # Use internal function call instead of HTTP request for better performance
            from back_end_process.voice_api import speak_detection
            speak_detection(obj["object"], obj["location"])
        except Exception as e:
            print(f"❌ Voice API failed: {str(e)}")

    return jsonify(detections)