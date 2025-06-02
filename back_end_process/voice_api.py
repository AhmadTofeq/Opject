# back_end_process/voice_api.py - Fixed version with better queue management

from flask import Blueprint, request, jsonify
import pyttsx3
import threading
import time
import queue
import traceback

voice_bp = Blueprint('voice', __name__)

# Thread-safe voice system
engine = None
engine_lock = threading.Lock()
voice_queue = queue.Queue(maxsize=5)  # Reduced queue size
voice_thread = None
voice_active = True
voice_initialized = False

def init_engine():
    """Initialize the TTS engine with error handling"""
    global engine, voice_initialized
    
    if engine is not None and voice_initialized:
        return True
        
    try:
        print("🔊 Initializing pyttsx3 engine...")
        engine = pyttsx3.init()
        
        # Test if engine works
        voices = engine.getProperty('voices')
        if voices and len(voices) > 0:
            engine.setProperty('voice', voices[0].id)
        
        engine.setProperty('rate', 150)    # Slower, more reliable speech
        engine.setProperty('volume', 0.7)  # Reduced volume
        
        # Test the engine with a short phrase
        engine.say("Voice system ready")
        engine.runAndWait()
        
        voice_initialized = True
        print("✅ pyttsx3 engine initialized and tested successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize pyttsx3: {str(e)}")
        print(f"Full error: {traceback.format_exc()}")
        engine = None
        voice_initialized = False
        return False

def voice_worker():
    """Background thread worker for processing voice queue with better error handling"""
    global voice_active, voice_initialized
    
    print("🎤 Voice worker thread started")
    
    while voice_active:
        try:
            # Get message with timeout
            message = voice_queue.get(timeout=2.0)
            
            if message is None:  # Shutdown signal
                print("🔇 Voice worker received shutdown signal")
                break
            
            if not voice_initialized:
                print("⚠️ Voice engine not initialized, skipping message")
                voice_queue.task_done()
                continue
                
            # Process the message with error handling
            try:
                with engine_lock:
                    if engine is not None:
                        print(f"🔊 Speaking: {message}")
                        engine.say(message)
                        engine.runAndWait()
                        print("✅ Speech completed successfully")
                    else:
                        print("❌ Engine is None, cannot speak")
                        
            except Exception as speech_error:
                print(f"❌ Speech synthesis error: {str(speech_error)}")
                # Try to reinitialize engine on error
                try:
                    engine.stop()
                except:
                    pass
                voice_initialized = False
                init_engine()
                        
            voice_queue.task_done()
            time.sleep(0.1)  # Small delay between messages
            
        except queue.Empty:
            # Normal timeout, continue loop
            continue
        except Exception as e:
            print(f"❌ Voice worker error: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            time.sleep(1)  # Wait before retrying
    
    print("🔇 Voice worker thread stopped")

def start_voice_system():
    """Start the voice system with better initialization"""
    global voice_thread, voice_active
    
    print("🚀 Starting voice system...")
    
    # Initialize engine first
    if not init_engine():
        print("❌ Failed to initialize voice engine")
        return False
    
    # Clear any existing queue
    clear_voice_queue()
    
    # Start worker thread if not already running
    if voice_thread is None or not voice_thread.is_alive():
        voice_active = True
        voice_thread = threading.Thread(target=voice_worker, daemon=True, name="VoiceWorker")
        voice_thread.start()
        print("✅ Voice worker thread started")
        
        # Give thread time to start
        time.sleep(0.5)
        
        if voice_thread.is_alive():
            print("✅ Voice system fully operational")
            return True
        else:
            print("❌ Voice worker thread failed to start")
            return False
    else:
        print("✅ Voice system already running")
        return True

def clear_voice_queue():
    """Clear the voice queue"""
    try:
        while not voice_queue.empty():
            try:
                voice_queue.get_nowait()
                voice_queue.task_done()
            except queue.Empty:
                break
        print("🧹 Voice queue cleared")
    except Exception as e:
        print(f"⚠️ Error clearing voice queue: {e}")

def stop_voice_system():
    """Stop the voice system gracefully"""
    global voice_active, voice_thread, voice_initialized
    
    print("🛑 Stopping voice system...")
    voice_active = False
    
    # Clear queue and add shutdown signal
    clear_voice_queue()
    
    try:
        voice_queue.put(None, timeout=1.0)  # Shutdown signal
    except queue.Full:
        pass
    
    # Wait for thread to finish
    if voice_thread and voice_thread.is_alive():
        voice_thread.join(timeout=3.0)
        if voice_thread.is_alive():
            print("⚠️ Voice thread did not stop gracefully")
        else:
            print("✅ Voice thread stopped")
    
    # Stop engine
    if engine:
        try:
            with engine_lock:
                engine.stop()
        except:
            pass
    
    voice_initialized = False
    print("✅ Voice system stopped")

def speak_detection(object_name, location):
    """Add detection to voice queue for async processing"""
    global voice_initialized
    
    if not voice_initialized:
        print("⚠️ Voice system not initialized")
        return False
        
    if not object_name or not location:
        print("❌ Missing object name or location")
        return False
    
    # Smart message formatting
    if object_name.lower() == "object":
        message = location  # location contains the full message
    elif object_name.lower() == "system":
        message = location  # system announcements
    else:
        clean_object = object_name.replace('_', ' ').strip().title()
        clean_location = location.replace('_', ' ').strip()
        message = f"{clean_object} detected in {clean_location}"
    
    # Limit message length
    if len(message) > 100:
        message = message[:97] + "..."
    
    try:
        # Check queue size and clear if too full
        if voice_queue.qsize() >= 4:
            print("🧹 Voice queue nearly full, clearing old messages")
            clear_voice_queue()
        
        # Add to queue without blocking
        voice_queue.put(message, block=False)
        print(f"📢 Queued voice message: {message[:50]}...")
        return True
        
    except queue.Full:
        print("⚠️ Voice queue full, clearing and retrying")
        clear_voice_queue()
        try:
            voice_queue.put(message, block=False)
            return True
        except queue.Full:
            print("❌ Voice queue still full after clearing")
            return False
    except Exception as e:
        print(f"❌ Voice queue error: {str(e)}")
        return False

@voice_bp.route('/api/speak', methods=['POST'])
def speak():
    """HTTP endpoint for voice API with better error handling"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        object_name = data.get('object', '')
        location = data.get('location', '')

        if not object_name or not location:
            return jsonify({'error': 'Both "object" and "location" are required.'}), 400

        # Check if voice system is running
        if not voice_initialized:
            return jsonify({'error': 'Voice system not initialized'}), 500

        # Use the async function
        success = speak_detection(object_name, location)
        
        if success:
            return jsonify({
                'message': f'Queued: {object_name} in {location}',
                'queue_size': voice_queue.qsize()
            }), 200
        else:
            return jsonify({'error': 'Failed to queue speech'}), 500
            
    except Exception as e:
        print(f"❌ API speak error: {str(e)}")
        return jsonify({'error': f'API error: {str(e)}'}), 500

@voice_bp.route('/api/voice_status', methods=['GET'])
def voice_status():
    """Get voice system status"""
    return jsonify({
        'engine_initialized': voice_initialized,
        'engine_available': engine is not None,
        'queue_size': voice_queue.qsize(),
        'thread_active': voice_thread.is_alive() if voice_thread else False,
        'voice_active': voice_active
    })

@voice_bp.route('/api/voice_clear', methods=['POST'])
def clear_queue():
    """Clear the voice queue manually"""
    clear_voice_queue()
    return jsonify({'message': 'Voice queue cleared', 'queue_size': voice_queue.qsize()})

@voice_bp.route('/api/voice_restart', methods=['POST'])
def restart_voice():
    """Restart the voice system"""
    stop_voice_system()
    time.sleep(1)
    success = start_voice_system()
    return jsonify({
        'success': success,
        'message': 'Voice system restarted' if success else 'Failed to restart voice system'
    })

# Initialize voice system when module loads
print("🔊 Loading voice system...")
if start_voice_system():
    print("✅ Voice system loaded successfully")
else:
    print("❌ Voice system failed to load")

# Cleanup function for graceful shutdown
import atexit
atexit.register(stop_voice_system)