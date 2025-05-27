from flask import Blueprint, render_template, request, jsonify
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

    header, encoded = data['image'].split(",", 1)
    image_bytes = base64.b64decode(encoded)
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    detections = detect_objects(frame)

    for obj in detections:
        try:
            requests.post("http://localhost:5000/api/speak", json={
                "object": obj["object"],
                "location": obj["location"]
            })
        except Exception as e:
            print("❌ Voice API failed:", e)

    return jsonify(detections)
