# back_end_process/voice_api.py - New multi-method voice system

from flask import Blueprint, request, jsonify
import os
import sys
import subprocess
import threading
import time
import queue
import tempfile
import platform

voice_bp = Blueprint('voice', __name__)

# Voice system configuration
voice_queue = queue.Queue(maxsize=5)
voice_thread = None
voice_active = True
last_announcement_time = 0
announcement_cooldown = 1.5
current_voice_method = None
available_methods = []

class VoiceMethod:
    """Base class for voice methods"""
    def __init__(self, name):
        self.name = name
        self.available = False
        
    def test(self):
        """Test if this method is available"""
        return False
        
    def speak(self, text):
        """Speak the given text"""
        return False

class WindowsSAPIVoice(VoiceMethod):
    """Windows SAPI voice using PowerShell"""
    def __init__(self):
        super().__init__("Windows SAPI")
        
    def test(self):
        if platform.system() != "Windows":
            return False
        try:
            # Test PowerShell SAPI
            cmd = ['powershell', '-Command', 'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("test")']
            result = subprocess.run(cmd, capture_output=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
            self.available = result.returncode == 0
            return self.available
        except:
            return False
            
    def speak(self, text):
        try:
            # Escape text for PowerShell
            escaped_text = text.replace('"', '`"').replace("'", "''")
            cmd = [
                'powershell', '-Command', 
                f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Rate = 2; $synth.Volume = 80; $synth.Speak("{escaped_text}")'
            ]
            subprocess.run(cmd, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception as e:
            print(f"❌ Windows SAPI error: {e}")
            return False

class EdgeTTSVoice(VoiceMethod):
    """Microsoft Edge TTS using edge-tts"""
    def __init__(self):
        super().__init__("Edge TTS")
        
    def test(self):
        try:
            import edge_tts
            self.available = True
            return True
        except ImportError:
            try:
                # Try to install edge-tts
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'edge-tts'], 
                             capture_output=True, timeout=30)
                import edge_tts
                self.available = True
                return True
            except:
                return False
                
    def speak(self, text):
        try:
            import edge_tts
            import asyncio
            
            async def speak_async():
                voice = "en-US-AriaNeural"  # Fast, clear voice
                communicate = edge_tts.Communicate(text, voice, rate="+20%")
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    await communicate.save(tmp_file.name)
                    
                    # Play the audio file
                    if platform.system() == "Windows":
                        subprocess.run(['powershell', '-c', f'(New-Object Media.SoundPlayer "{tmp_file.name}").PlaySync()'], 
                                     timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        # For Linux/Mac - would need additional audio players
                        pass
                    
                    # Clean up
                    try:
                        os.unlink(tmp_file.name)
                    except:
                        pass
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(speak_async())
            loop.close()
            return True
            
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
            return False

class SimplePyTTSX3Voice(VoiceMethod):
    """Simplified pyttsx3 implementation"""
    def __init__(self):
        super().__init__("Simple pyttsx3")
        self.engine = None
        
    def test(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 200)
            self.engine.setProperty('volume', 0.8)
            
            # Quick test without runAndWait
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
            
            self.available = True
            return True
        except Exception as e:
            print(f"❌ pyttsx3 test failed: {e}")
            return False
            
    def speak(self, text):
        if not self.engine:
            return False
        try:
            # Simple approach - just say and run
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"❌ Simple pyttsx3 error: {e}")
            # Try to reinitialize
            try:
                self.engine.stop()
                import pyttsx3
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 200)
                self.engine.setProperty('volume', 0.8)
            except:
                pass
            return False

class WebBrowserVoice(VoiceMethod):
    """Fallback using web browser speech"""
    def __init__(self):
        super().__init__("Web Browser")
        
    def test(self):
        # This is always available as a fallback
        self.available = True
        return True
        
    def speak(self, text):
        # This will be handled by the frontend JavaScript
        # We just return True to indicate the message was "queued"
        return True

def initialize_voice_methods():
    """Initialize and test all available voice methods"""
    global available_methods, current_voice_method
    
    print("🔍 Testing voice methods...")
    
    methods = [
        WindowsSAPIVoice(),
        EdgeTTSVoice(), 
        SimplePyTTSX3Voice(),
        WebBrowserVoice()  # Always last as fallback
    ]
    
    available_methods = []
    for method in methods:
        print(f"   Testing {method.name}...")
        if method.test():
            available_methods.append(method)
            print(f"   ✅ {method.name} available")
        else:
            print(f"   ❌ {method.name} not available")
    
    if available_methods:
        current_voice_method = available_methods[0]
        print(f"🔊 Using voice method: {current_voice_method.name}")
        return True
    else:
        print("❌ No voice methods available")
        return False

def voice_worker():
    """Voice worker thread"""
    global voice_active, last_announcement_time, current_voice_method
    
    print("🎤 Voice worker started")
    
    while voice_active:
        try:
            # Get message
            try:
                message = voice_queue.get(timeout=1.0)
            except queue.Empty:
                continue
                
            if message is None:  # Shutdown signal
                break
                
            # Check cooldown
            current_time = time.time()
            if current_time - last_announcement_time < announcement_cooldown:
                print(f"🕐 Cooldown active, skipping: {message[:30]}...")
                voice_queue.task_done()
                continue
            
            # Try to speak
            success = False
            for method in available_methods:
                try:
                    print(f"🔊 Trying {method.name}: {message[:50]}...")
                    success = method.speak(message)
                    if success:
                        current_voice_method = method
                        last_announcement_time = current_time
                        print(f"✅ Spoke with {method.name}")
                        break
                    else:
                        print(f"⚠️ {method.name} failed, trying next...")
                except Exception as e:
                    print(f"❌ {method.name} error: {e}")
                    continue
            
            if not success:
                print(f"❌ All voice methods failed for: {message[:30]}...")
                
            voice_queue.task_done()
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Voice worker error: {e}")
            try:
                voice_queue.task_done()
            except:
                pass
            time.sleep(0.5)
    
    print("🔇 Voice worker stopped")

def start_voice_system():
    """Start the voice system"""
    global voice_thread, voice_active
    
    print("🚀 Starting new voice system...")
    
    # Initialize voice methods
    if not initialize_voice_methods():
        print("❌ No voice methods available")
        return False
    
    # Clear queue
    clear_queue()
    
    # Start worker thread
    if voice_thread is None or not voice_thread.is_alive():
        voice_active = True
        voice_thread = threading.Thread(target=voice_worker, daemon=True)
        voice_thread.start()
        
        time.sleep(0.2)
        if voice_thread.is_alive():
            print("✅ Voice system started")
            return True
        else:
            print("❌ Voice thread failed")
            return False
    
    return True

def clear_queue():
    """Clear the voice queue"""
    count = 0
    try:
        while not voice_queue.empty():
            voice_queue.get_nowait()
            voice_queue.task_done()
            count += 1
        if count > 0:
            print(f"🧹 Cleared {count} voice messages")
    except:
        pass

def stop_voice_system():
    """Stop the voice system"""
    global voice_active, voice_thread
    
    print("🛑 Stopping voice system...")
    voice_active = False
    
    clear_queue()
    try:
        voice_queue.put(None, timeout=0.5)
    except:
        pass
    
    if voice_thread and voice_thread.is_alive():
        voice_thread.join(timeout=2.0)
    
    print("✅ Voice system stopped")

def speak_detection(object_name, location):
    """Add message to voice queue"""
    global last_announcement_time
    
    if not available_methods:
        return False
        
    # Check cooldown
    current_time = time.time()
    if current_time - last_announcement_time < announcement_cooldown:
        return False
        
    # Format message
    if object_name.lower() == "system":
        message = location
    elif object_name.lower() == "object":
        message = location
    else:
        message = f"{object_name.title()} detected in {location}"
    
    # Limit length
    if len(message) > 60:
        message = message[:57] + "..."
    
    try:
        # Clear if queue is getting full
        if voice_queue.qsize() >= 3:
            clear_queue()
        
        voice_queue.put(message, block=False)
        print(f"📢 Queued: {message}")
        return True
        
    except queue.Full:
        clear_queue()
        try:
            voice_queue.put(message, block=False)
            return True
        except:
            return False
    except Exception as e:
        print(f"❌ Queue error: {e}")
        return False

# Flask routes
@voice_bp.route('/api/speak', methods=['POST'])
def speak():
    """Speak endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400
            
        object_name = data.get('object', '')
        location = data.get('location', '')
        
        if not object_name or not location:
            return jsonify({'error': 'Missing data'}), 400
        
        success = speak_detection(object_name, location)
        
        return jsonify({
            'success': success,
            'method': current_voice_method.name if current_voice_method else 'None',
            'queue_size': voice_queue.qsize()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@voice_bp.route('/api/voice_status', methods=['GET'])
def voice_status():
    """Voice status endpoint"""
    return jsonify({
        'available_methods': [m.name for m in available_methods],
        'current_method': current_voice_method.name if current_voice_method else None,
        'queue_size': voice_queue.qsize(),
        'thread_alive': voice_thread.is_alive() if voice_thread else False,
        'cooldown_remaining': max(0, announcement_cooldown - (time.time() - last_announcement_time))
    })

@voice_bp.route('/api/voice_test', methods=['POST'])
def voice_test():
    """Test voice system"""
    success = speak_detection("system", "Voice system test")
    return jsonify({
        'success': success,
        'message': 'Test queued' if success else 'Test failed or on cooldown'
    })

@voice_bp.route('/api/voice_restart', methods=['POST']) 
def voice_restart():
    """Restart voice system"""
    stop_voice_system()
    time.sleep(0.5)
    success = start_voice_system()
    return jsonify({'success': success})

# Initialize on import
print("🔊 Initializing voice system...")
voice_initialized = start_voice_system()
if voice_initialized:
    print("✅ Voice system ready")
else:
    print("⚠️ Voice system has issues but will try fallbacks")

# Cleanup
import atexit
atexit.register(stop_voice_system)