# app/routes.py
from flask import Blueprint, render_template, request, jsonify, url_for
import base64
import numpy as np
import cv2
import requests
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
        header, encoded = data['image'].split(",", 1)
        image_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'error': f'Image decoding failed: {e}'}), 400

    detections = detect_objects(frame)

    for obj in detections:
        try:
            # Safe and dynamic URL generation
            speak_url = url_for('voice.speak', _external=True)
            requests.post(speak_url, json={
                "object": obj["object"],
                "location": obj["location"]
            }, timeout=2)
        except Exception as e:
            print("❌ Voice API failed (will fallback in browser):", e)

    return jsonify(detections)
