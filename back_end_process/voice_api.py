# back_end_process/voice_api.py - Completely redesigned for better performance

from flask import Blueprint, request, jsonify
import pyttsx3
import threading
import time
import queue
import traceback

voice_bp = Blueprint('voice', __name__)

# Voice system variables
engine = None
engine_lock = threading.Lock()
voice_queue = queue.Queue(maxsize=3)  # Very small queue
voice_thread = None
voice_active = True
voice_initialized = False
last_announcement_time = 0
announcement_cooldown = 2.0  # Minimum 2 seconds between announcements

def init_engine():
    """Initialize TTS engine with minimal settings for maximum reliability"""
    global engine, voice_initialized
    
    try:
        print("🔊 Initializing minimal pyttsx3 engine...")
        
        # Destroy existing engine if any
        if engine is not None:
            try:
                engine.stop()
                del engine
            except:
                pass
        
        engine = pyttsx3.init()
        
        # Minimal configuration for reliability
        voices = engine.getProperty('voices')
        if voices and len(voices) > 0:
            engine.setProperty('voice', voices[0].id)
        
        engine.setProperty('rate', 180)     # Faster speech
        engine.setProperty('volume', 0.8)   # Good volume
        
        # Quick test without runAndWait to avoid blocking
        print("✅ pyttsx3 engine initialized successfully")
        voice_initialized = True
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize pyttsx3: {str(e)}")
        engine = None
        voice_initialized = False
        return False

def voice_worker():
    """Optimized voice worker with timeout protection"""
    global voice_active, voice_initialized, last_announcement_time
    
    print("🎤 Voice worker thread started")
    
    while voice_active:
        try:
            # Get message with short timeout
            try:
                message = voice_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            if message is None:  # Shutdown signal
                print("🔇 Voice worker shutdown")
                break
            
            # Check cooldown to prevent spam
            current_time = time.time()
            if current_time - last_announcement_time < announcement_cooldown:
                print(f"🕐 Voice cooldown active, skipping: {message[:30]}...")
                voice_queue.task_done()
                continue
            
            if not voice_initialized:
                print("⚠️ Voice engine not ready, skipping")
                voice_queue.task_done()
                continue
                
            # Speak with timeout protection
            success = speak_with_timeout(message, timeout_seconds=3.0)
            
            if success:
                last_announcement_time = current_time
                print(f"✅ Spoke: {message[:50]}...")
            else:
                print(f"❌ Failed to speak: {message[:30]}...")
                
            voice_queue.task_done()
            
            # Small delay to prevent overwhelming
            time.sleep(0.2)
            
        except Exception as e:
            print(f"❌ Voice worker error: {str(e)}")
            try:
                voice_queue.task_done()
            except:
                pass
            time.sleep(0.5)
    
    print("🔇 Voice worker stopped")

def speak_with_timeout(message, timeout_seconds=3.0):
    """Speak with timeout protection to prevent hanging"""
    global engine
    
    if not engine or not voice_initialized:
        return False
    
    try:
        # Use a separate thread for speaking with timeout
        speak_result = [False]  # Use list for mutable reference
        
        def speak_thread():
            try:
                with engine_lock:
                    if engine:
                        engine.say(message)
                        engine.runAndWait()
                        speak_result[0] = True
            except Exception as e:
                print(f"❌ Speech thread error: {e}")
        
        # Start speaking thread
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            print(f"⏰ Speech timeout for: {message[:30]}...")
            # Try to stop the engine
            try:
                with engine_lock:
                    if engine:
                        engine.stop()
            except:
                pass
            return False
        
        return speak_result[0]
        
    except Exception as e:
        print(f"❌ Speak timeout error: {e}")
        return False

def start_voice_system():
    """Start voice system with better error handling"""
    global voice_thread, voice_active
    
    print("🚀 Starting optimized voice system...")
    
    # Initialize engine
    if not init_engine():
        print("❌ Voice engine initialization failed")
        return False
    
    # Clear queue
    clear_voice_queue()
    
    # Start worker thread
    if voice_thread is None or not voice_thread.is_alive():
        voice_active = True
        voice_thread = threading.Thread(target=voice_worker, daemon=True, name="VoiceWorker")
        voice_thread.start()
        
        # Wait a bit and check
        time.sleep(0.3)
        if voice_thread.is_alive():
            print("✅ Voice system operational")
            return True
        else:
            print("❌ Voice thread failed to start")
            return False
    
    return True

def clear_voice_queue():
    """Aggressively clear the voice queue"""
    cleared_count = 0
    try:
        while not voice_queue.empty():
            try:
                voice_queue.get_nowait()
                voice_queue.task_done()
                cleared_count += 1
            except queue.Empty:
                break
        
        if cleared_count > 0:
            print(f"🧹 Cleared {cleared_count} voice messages")
            
    except Exception as e:
        print(f"⚠️ Error clearing queue: {e}")

def stop_voice_system():
    """Stop voice system gracefully"""
    global voice_active, voice_thread, voice_initialized
    
    print("🛑 Stopping voice system...")
    voice_active = False
    voice_initialized = False
    
    # Clear queue and signal shutdown
    clear_voice_queue()
    try:
        voice_queue.put(None, timeout=0.5)
    except:
        pass
    
    # Stop thread
    if voice_thread and voice_thread.is_alive():
        voice_thread.join(timeout=2.0)
    
    # Stop engine
    if engine:
        try:
            with engine_lock:
                engine.stop()
        except:
            pass
    
    print("✅ Voice system stopped")

def smart_speak_detection(object_name, location):
    """Smart speaking with cooldown and queue management"""
    global last_announcement_time
    
    if not voice_initialized:
        return False
        
    if not object_name or not location:
        return False
    
    # Check cooldown
    current_time = time.time()
    if current_time - last_announcement_time < announcement_cooldown:
        return False  # Skip due to cooldown
    
    # Format message
    if object_name.lower() == "object":
        message = location
    elif object_name.lower() == "system":
        message = location
    else:
        message = f"{object_name.title()} detected in {location}"
    
    # Limit message length
    if len(message) > 80:
        message = message[:77] + "..."
    
    # Clear queue if full and add message
    try:
        if voice_queue.qsize() >= 2:
            print("🧹 Queue nearly full, clearing...")
            clear_voice_queue()
        
        voice_queue.put(message, block=False)
        print(f"📢 Queued: {message[:40]}...")
        return True
        
    except queue.Full:
        print("⚠️ Queue full, clearing and retrying...")
        clear_voice_queue()
        try:
            voice_queue.put(message, block=False)
            return True
        except:
            return False
    except Exception as e:
        print(f"❌ Queue error: {e}")
        return False

# Keep original function name for compatibility
def speak_detection(object_name, location):
    """Wrapper for backwards compatibility"""
    return smart_speak_detection(object_name, location)

@voice_bp.route('/api/speak', methods=['POST'])
def speak():
    """HTTP endpoint for voice API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        object_name = data.get('object', '')
        location = data.get('location', '')

        if not object_name or not location:
            return jsonify({'error': 'Missing object or location'}), 400

        if not voice_initialized:
            return jsonify({'error': 'Voice system not ready'}), 500

        success = smart_speak_detection(object_name, location)
        
        return jsonify({
            'success': success,
            'message': 'Queued' if success else 'Skipped or failed',
            'queue_size': voice_queue.qsize()
        }), 200
            
    except Exception as e:
        print(f"❌ API error: {e}")
        return jsonify({'error': str(e)}), 500

@voice_bp.route('/api/voice_status', methods=['GET'])
def voice_status():
    """Get detailed voice system status"""
    return jsonify({
        'initialized': voice_initialized,
        'engine_available': engine is not None,
        'queue_size': voice_queue.qsize(),
        'thread_alive': voice_thread.is_alive() if voice_thread else False,
        'cooldown_remaining': max(0, announcement_cooldown - (time.time() - last_announcement_time))
    })

@voice_bp.route('/api/voice_clear', methods=['POST'])
def clear_queue_endpoint():
    """Clear voice queue endpoint"""
    clear_voice_queue()
    return jsonify({
        'message': 'Queue cleared',
        'queue_size': voice_queue.qsize()
    })

@voice_bp.route('/api/voice_restart', methods=['POST'])
def restart_voice():
    """Restart voice system endpoint"""
    stop_voice_system()
    time.sleep(0.5)
    success = start_voice_system()
    return jsonify({
        'success': success,
        'message': 'Restarted' if success else 'Failed to restart'
    })

# Initialize when module loads
print("🔊 Loading voice system...")
if start_voice_system():
    print("✅ Voice system ready")
else:
    print("❌ Voice system initialization failed")

# Cleanup on exit
import atexit
atexit.register(stop_voice_system)