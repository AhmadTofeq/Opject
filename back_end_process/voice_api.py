# back_end_process/voice_api.py - Optimized version

from flask import Blueprint, request, jsonify
import pyttsx3
import threading
import time
import queue

voice_bp = Blueprint('voice', __name__)

# Thread-safe voice system
engine = None
engine_lock = threading.Lock()
voice_queue = queue.Queue(maxsize=10)  # Limit queue size
voice_thread = None
voice_active = True

def init_engine():
    """Initialize the TTS engine with optimized settings"""
    global engine
    if engine is None:
        try:
            engine = pyttsx3.init()
            
            # Optimize engine settings for performance
            voices = engine.getProperty('voices')
            if voices:
                engine.setProperty('voice', voices[0].id)  # Use first available voice
            
            engine.setProperty('rate', 160)    # Slightly faster speech
            engine.setProperty('volume', 0.8)  # Reduced volume to prevent distortion
            
            print("✅ pyttsx3 engine initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize pyttsx3: {str(e)}")
            engine = None
            return False
    return True

def voice_worker():
    """Background thread worker for processing voice queue"""
    global voice_active
    
    while voice_active:
        try:
            # Get message with timeout
            message = voice_queue.get(timeout=1.0)
            
            if message is None:  # Shutdown signal
                break
                
            # Process the message
            with engine_lock:
                if engine is not None:
                    try:
                        print(f"🔊 Speaking: {message}")
                        engine.say(message)
                        engine.runAndWait()
                        print("✅ Speech completed")
                    except Exception as e:
                        print(f"❌ Speech error: {str(e)}")
                        
            voice_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ Voice worker error: {str(e)}")

def start_voice_system():
    """Start the voice system background thread"""
    global voice_thread, voice_active
    
    if not init_engine():
        return False
        
    if voice_thread is None or not voice_thread.is_alive():
        voice_active = True
        voice_thread = threading.Thread(target=voice_worker, daemon=True)
        voice_thread.start()
        print("✅ Voice system thread started")
        
    return True

def stop_voice_system():
    """Stop the voice system gracefully"""
    global voice_active, voice_thread
    
    voice_active = False
    
    # Clear queue and add shutdown signal
    try:
        while not voice_queue.empty():
            voice_queue.get_nowait()
    except queue.Empty:
        pass
        
    voice_queue.put(None)  # Shutdown signal
    
    if voice_thread and voice_thread.is_alive():
        voice_thread.join(timeout=2.0)
        print("✅ Voice system stopped")

def speak_detection(object_name, location):
    """Add detection to voice queue for async processing"""
    if not object_name or not location:
        print("❌ Missing object name or location")
        return False
        
    # Smart message formatting
    if object_name.lower() == "object":
        message = location  # location contains the full message
    else:
        clean_object = object_name.replace('_', ' ').strip().title()
        clean_location = location.replace('_', ' ').strip()
        message = f"{clean_object} detected in {clean_location}"
    
    try:
        # Add to queue with timeout to prevent blocking
        voice_queue.put(message, timeout=0.5)
        return True
    except queue.Full:
        print("⚠️ Voice queue full, skipping announcement")
        return False
    except Exception as e:
        print(f"❌ Voice queue error: {str(e)}")
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

    # Use the async function
    success = speak_detection(object_name, location)
    
    if success:
        return jsonify({'message': f'Queued: {object_name} in {location}'}), 200
    else:
        return jsonify({'error': 'Failed to queue speech'}), 500

@voice_bp.route('/api/voice_status', methods=['GET'])
def voice_status():
    """Get voice system status"""
    return jsonify({
        'engine_available': engine is not None,
        'queue_size': voice_queue.qsize(),
        'thread_active': voice_thread.is_alive() if voice_thread else False,
        'voice_active': voice_active
    })

# Initialize voice system when module loads
start_voice_system()

# Cleanup function for graceful shutdown
import atexit
atexit.register(stop_voice_system)