# back_end_process/voice_api.py

from flask import Blueprint, request, jsonify
import pyttsx3
import threading
import time

voice_bp = Blueprint('voice', __name__)

# Initialize text-to-speech engine once
engine = None
engine_lock = threading.Lock()

def init_engine():
    global engine
    if engine is None:
        try:
            engine = pyttsx3.init()
            # Configure engine settings
            engine.setProperty('rate', 150)  # Speed of speech
            engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
            print("✅ pyttsx3 engine initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize pyttsx3: {str(e)}")
            engine = None

# Initialize engine when module loads
init_engine()

def speak_detection(object_name, location):
    """Internal function to speak detection without HTTP overhead"""
    if not object_name or not location:
        print("❌ Missing object name or location")
        return False
        
    message = f"{object_name.replace('_', ' ').title()} detected in {location.replace('_', ' ')}"
    
    try:
        with engine_lock:
            if engine is not None:
                print(f"🔊 Speaking: {message}")
                engine.say(message)
                engine.runAndWait()
                print("✅ Speech completed")
                return True
            else:
                print("❌ TTS engine not available")
                return False
    except Exception as e:
        print(f"❌ Speech error: {str(e)}")
        return False

@voice_bp.route('/api/speak', methods=['POST'])
def speak():
    """HTTP endpoint for voice API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    object_name = data.get('object')
    location = data.get('location')

    if not object_name or not location:
        return jsonify({'error': 'Both "object" and "location" are required.'}), 400

    # Use the internal function
    success = speak_detection(object_name, location)
    
    if success:
        return jsonify({'message': f'Speaking: {object_name} in {location}'}), 200
    else:
        return jsonify({'error': 'Speech synthesis failed'}), 500