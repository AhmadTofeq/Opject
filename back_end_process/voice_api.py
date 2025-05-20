# back_end_process/voice_api.py

from flask import Blueprint, request, jsonify
import pyttsx3

voice_bp = Blueprint('voice', __name__)

# Initialize text-to-speech engine once
engine = pyttsx3.init()

@voice_bp.route('/api/speak', methods=['POST'])
def speak():
    data = request.get_json()
    object_name = data.get('object')
    location = data.get('location')

    if not object_name or not location:
        return jsonify({'error': 'Both "object" and "location" are required.'}), 400

    message = f"{object_name.capitalize()} on {location.lower()}"
    print(f"🔊 Speaking: {message}")

    try:
        engine.say(message)
        engine.runAndWait()
        print("✅ pyttsx3 finished speaking.")
        return jsonify({'message': f"Speaking: {message}"}), 200
    except Exception as e:
        print(f"❌ pyttsx3 error: {str(e)}")
        return jsonify({'error': str(e)}), 500
