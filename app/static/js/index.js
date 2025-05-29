// app/static/js/index.js - AI Vision System for Blind Users
console.log('🚀 Loading AI Vision System...');

// Global Variables
let stream = null;
let video = null;
let detectionActive = false;
let detectionInterval = null;
let lastDetections = [];
let paused = false;

// Configuration
const CONFIG = {
    DETECTION_INTERVAL: 2000,  // 2 seconds between detections
    IMAGE_QUALITY: 0.8,        // JPEG quality (0.0 - 1.0)
    RETRY_ATTEMPTS: 3,         // Max retry attempts for failed requests
    VIDEO_CONSTRAINTS: {
        width: { ideal: 640 },
        height: { ideal: 480 }
    }
};

// DOM Elements (will be initialized on page load)
let elements = {};

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', initializeSystem);

/**
 * Main initialization function
 */
function initializeSystem() {
    console.log('🔧 Initializing AI Vision System...');
    
    // Get DOM elements
    initializeDOMElements();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize camera
    initializeCamera();
    
    // Test voice system
    testVoiceSystem();
    
    // Set up keyboard shortcuts for accessibility
    setupKeyboardShortcuts();
    
    console.log('✅ AI Vision System initialized successfully');
}

/**
 * Initialize DOM element references
 */
function initializeDOMElements() {
    elements = {
        video: document.getElementById('cameraFeed'),
        startBtn: document.getElementById('startBtn'),
        stopBtn: document.getElementById('stopBtn'),
        pauseBtn: document.getElementById('pauseBtn'),
        refreshBtn: document.getElementById('refreshBtn'),
        systemStatus: document.getElementById('systemStatus'),
        cameraStatus: document.getElementById('cameraStatus'),
        detectionLog: document.getElementById('detectionLog'),
        lastDetection: document.getElementById('lastDetection'),
        voiceStatus: document.getElementById('voiceStatus'),
        objectCount: document.getElementById('objectCount')
    };
    
    // Store video reference globally for easier access
    video = elements.video;
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Button events
    elements.startBtn.addEventListener('click', startDetection);
    elements.stopBtn.addEventListener('click', stopDetection);
    elements.pauseBtn.addEventListener('click', pauseDetection);
    elements.refreshBtn.addEventListener('click', refreshSystem);
    
    // Video events
    video.addEventListener('click', toggleVideoPlayback);
    video.addEventListener('dblclick', stopCamera);
    
    // Error handling
    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);
}

/**
 * Set up keyboard shortcuts for accessibility
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (event) => {
        // Don't trigger shortcuts if user is typing in an input
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch(event.code) {
            case 'Space':
                event.preventDefault();
                if (detectionActive) {
                    pauseDetection();
                } else {
                    startDetection();
                }
                break;
            case 'KeyS':
                if (event.ctrlKey) {
                    event.preventDefault();
                    startDetection();
                }
                break;
            case 'KeyQ':
                if (event.ctrlKey) {
                    event.preventDefault();
                    stopDetection();
                }
                break;
            case 'KeyR':
                if (event.ctrlKey) {
                    event.preventDefault();
                    refreshSystem();
                }
                break;
        }
    });
    
    console.log('⌨️ Keyboard shortcuts enabled: Space (start/pause), Ctrl+S (start), Ctrl+Q (stop), Ctrl+R (refresh)');
}

/**
 * Initialize camera with proper error handling
 */
async function initializeCamera() {
    console.log('📹 Initializing camera...');
    updateCameraStatus('Requesting Access', 'warning');
    
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: CONFIG.VIDEO_CONSTRAINTS,
            audio: false
        });
        
        video.srcObject = stream;
        updateCameraStatus('Ready', 'success');
        updateSystemStatus('Camera Ready', 'success');
        
        console.log('✅ Camera initialized successfully');
        
        // Announce camera ready for blind users
        announceToUser('Camera is ready. Press the Start Detection button to begin.');
        
    } catch (error) {
        console.error('❌ Camera initialization failed:', error);
        updateCameraStatus('Error', 'danger');
        updateSystemStatus('Camera Error', 'danger');
        
        // Handle different types of camera errors
        let errorMessage = 'Camera access failed. ';
        if (error.name === 'NotAllowedError') {
            errorMessage += 'Please allow camera access and refresh the page.';
        } else if (error.name === 'NotFoundError') {
            errorMessage += 'No camera found. Please connect a camera.';
        } else if (error.name === 'NotReadableError') {
            errorMessage += 'Camera is in use by another application.';
        } else {
            errorMessage += error.message;
        }
        
        alert(errorMessage);
        announceToUser(errorMessage);
    }
}

/**
 * Start object detection
 */
function startDetection() {
    if (!stream || !video.srcObject) {
        const msg = 'Camera is not ready. Please wait for camera initialization.';
        alert(msg);
        announceToUser(msg);
        return;
    }

    if (detectionActive) {
        console.log('⚠️ Detection already active');
        return;
    }

    console.log('🎯 Starting object detection...');
    detectionActive = true;
    paused = false;
    
    updateSystemStatus('Starting Detection', 'primary');
    
    // Start detection loop
    detectionInterval = setInterval(() => {
        if (!paused && detectionActive) {
            captureAndDetect();
        }
    }, CONFIG.DETECTION_INTERVAL);

    // First detection after a short delay
    setTimeout(() => {
        if (detectionActive && !paused) {
            captureAndDetect();
        }
    }, 500);
    
    announceToUser('Object detection started. Objects will be announced as they are detected.');
}

/**
 * Stop object detection
 */
function stopDetection() {
    console.log('🛑 Stopping detection...');
    detectionActive = false;
    paused = false;
    
    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
    
    updateSystemStatus('Detection Stopped', 'secondary');
    updateDetectionLog('Detection stopped');
    updateObjectCount(0);
    
    announceToUser('Object detection stopped.');
}

/**
 * Pause/resume object detection
 */
function pauseDetection() {
    if (!detectionActive) {
        const msg = 'Detection is not running. Please start detection first.';
        alert(msg);
        announceToUser(msg);
        return;
    }

    paused = !paused;
    const status = paused ? 'Detection Paused' : 'Detecting Objects';
    const variant = paused ? 'warning' : 'primary';
    
    updateSystemStatus(status, variant);
    
    const announcement = paused ? 'Detection paused.' : 'Detection resumed.';
    announceToUser(announcement);
    
    console.log(`⏸️ Detection ${paused ? 'paused' : 'resumed'}`);
}

/**
 * Refresh the entire system
 */
function refreshSystem() {
    console.log('🔄 Refreshing system...');
    announceToUser('Refreshing system...');
    setTimeout(() => {
        location.reload();
    }, 1000);
}

/**
 * Toggle video playback (for user interaction)
 */
function toggleVideoPlayback() {
    if (!video.srcObject) return;

    if (video.paused) {
        video.play();
        console.log('▶️ Video resumed');
    } else {
        video.pause();
        console.log('⏸️ Video paused');
    }
}

/**
 * Stop camera completely
 */
function stopCamera() {
    console.log('📹 Stopping camera...');
    
    // Stop detection first
    stopDetection();
    
    // Stop camera stream
    if (stream) {
        stream.getTracks().forEach(track => {
            track.stop();
            console.log(`🔇 Stopped ${track.kind} track`);
        });
        video.srcObject = null;
        stream = null;
    }
    
    updateCameraStatus('Stopped', 'secondary');
    updateSystemStatus('Camera Stopped', 'secondary');
    announceToUser('Camera stopped.');
}

/**
 * Capture frame and send for detection
 */
async function captureAndDetect() {
    if (!video || !video.videoWidth || !video.videoHeight) {
        console.log('⚠️ Video not ready for capture');
        return;
    }

    try {
        updateSystemStatus('Processing Frame', 'info');
        
        // Create canvas and capture frame
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert to base64 with quality setting
        const dataUrl = canvas.toDataURL('image/jpeg', CONFIG.IMAGE_QUALITY);
        
        console.log('📸 Frame captured, sending for detection...');
        
        // Send to backend for detection
        const response = await fetch('/detect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                image: dataUrl,
                timestamp: Date.now()
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const detections = await response.json();
        handleDetectionResults(detections);
        
    } catch (error) {
        console.error('❌ Detection error:', error);
        updateSystemStatus('Detection Error', 'danger');
        updateDetectionLog(`Error: ${error.message}`);
    }
}

/**
 * Handle detection results from backend
 */
function handleDetectionResults(detections) {
    console.log('🎯 Detection results:', detections);
    
    if (!Array.isArray(detections)) {
        console.error('❌ Invalid detection format:', detections);
        return;
    }

    lastDetections = detections;
    
    // Update UI
    updateDetectionLog(detections);
    updateLastDetection(detections);
    updateObjectCount(detections.length);
    
    // Update status based on results
    if (detections.length > 0) {
        updateSystemStatus(`Found ${detections.length} object(s)`, 'success');
    } else {
        updateSystemStatus('Scanning for objects', 'primary');
    }
}

/**
 * Update detection log display
 */
function updateDetectionLog(detections) {
    const logElement = elements.detectionLog;
    if (!logElement) return;

    if (typeof detections === 'string') {
        // Handle string messages (like "Detection stopped")
        logElement.innerHTML = `<div class="text-muted">${detections}</div>`;
        return;
    }

    if (!Array.isArray(detections) || detections.length === 0) {
        logElement.innerHTML = '<div class="text-muted">No objects detected in current frame</div>';
        return;
    }

    const logEntries = detections.map(detection => {
        const confidence = detection.confidence ? ` (${(detection.confidence * 100).toFixed(1)}%)` : '';
        const timestamp = new Date().toLocaleTimeString();
        
        return `
            <div class="detection-entry mb-2 p-2 bg-light rounded border">
                <div class="fw-bold text-primary">
                    ${detection.object.charAt(0).toUpperCase() + detection.object.slice(1)}
                </div>
                <div class="text-muted">
                    Location: <em>${detection.location}</em>${confidence}
                </div>
                <small class="text-muted">${timestamp}</small>
            </div>
        `;
    }).join('');

    logElement.innerHTML = logEntries;
    
    // Auto-scroll to bottom for latest detections
    logElement.scrollTop = logElement.scrollHeight;
}

/**
 * Update last detection display
 */
function updateLastDetection(detections) {
    const element = elements.lastDetection;
    if (!element) return;

    if (Array.isArray(detections) && detections.length > 0) {
        const latest = detections[0];
        element.textContent = `${latest.object} in ${latest.location}`;
        element.className = 'ms-2 fw-bold text-success';
    } else {
        element.textContent = 'None';
        element.className = 'ms-2 text-muted';
    }
}

/**
 * Update object count display
 */
function updateObjectCount(count) {
    const element = elements.objectCount;
    if (!element) return;
    
    element.textContent = count.toString();
    element.className = count > 0 ? 'ms-2 fw-bold text-success' : 'ms-2 text-muted';
}

/**
 * Update system status with badge styling
 */
function updateSystemStatus(status, variant = 'secondary') {
    const element = elements.systemStatus;
    if (!element) return;

    // Remove existing badge classes
    element.className = element.className.replace(/bg-\w+/g, '');
    
    // Add new badge class
    element.classList.add(`bg-${variant}`);
    element.textContent = status;
    
    console.log(`📊 System Status: ${status}`);
}

/**
 * Update camera status
 */
function updateCameraStatus(status, variant = 'secondary') {
    const element = elements.cameraStatus;
    if (!element) return;

    element.className = element.className.replace(/bg-\w+/g, '');
    element.classList.add(`bg-${variant}`);
    element.textContent = status;
}

/**
 * Test voice system functionality
 */
async function testVoiceSystem() {
    console.log('🔊 Testing voice system...');
    updateVoiceStatus('Testing', 'warning');
    
    try {
        const response = await fetch('/api/speak', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                object: 'system',
                location: 'initialization'
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            console.log('✅ Voice system test successful');
            updateVoiceStatus('Working', 'success');
        } else {
            console.warn('⚠️ Voice system test failed:', data.error);
            updateVoiceStatus('Backend Error', 'warning');
            
            // Try browser fallback
            tryBrowserSpeech('Voice system using browser fallback');
        }
        
    } catch (error) {
        console.error('❌ Voice system unreachable:', error);
        updateVoiceStatus('Using Browser', 'info');
        
        // Fallback to browser speech synthesis
        tryBrowserSpeech('Voice system initialized with browser speech');
    }
}

/**
 * Try browser speech synthesis as fallback
 */
function tryBrowserSpeech(message) {
    if ('speechSynthesis' in window) {
        console.log('🔄 Using browser speech synthesis fallback');
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    } else {
        console.error('❌ No speech synthesis available');
        updateVoiceStatus('Not Available', 'danger');
    }
}

/**
 * Announce message to user (for accessibility)
 */
function announceToUser(message) {
    // Try backend voice first, then browser fallback
    fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            object: 'announcement',
            location: message
        })
    }).catch(() => {
        // Fallback to browser speech
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(message);
            utterance.lang = 'en-US';
            window.speechSynthesis.speak(utterance);
        }
    });
}

/**
 * Update voice status display
 */
function updateVoiceStatus(status, variant = 'secondary') {
    const element = elements.voiceStatus;
    if (!element) return;

    element.className = element.className.replace(/bg-\w+/g, '');
    element.classList.add(`bg-${variant}`);
    element.textContent = status;
}

/**
 * Global error handler
 */
function handleGlobalError(event) {
    console.error('🚨 Global error:', event.error);
    updateSystemStatus('System Error', 'danger');
    announceToUser('A system error occurred. Please refresh the page.');
}

/**
 * Handle unhandled promise rejections
 */
function handleUnhandledRejection(event) {
    console.error('🚨 Unhandled promise rejection:', event.reason);
    updateSystemStatus('Promise Error', 'danger');
}

// Log successful loading
console.log('✅ AI Vision System JavaScript loaded successfully');