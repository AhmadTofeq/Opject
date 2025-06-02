// app/static/js/index.js - Optimized AI Vision System
console.log('🚀 Loading Optimized AI Vision System...');

// Global Variables
let stream = null;
let video = null;
let detectionActive = false;
let detectionInterval = null;
let lastDetections = [];
let paused = false;
let canvas = null;
let ctx = null;

// Optimized Configuration
const CONFIG = {
    DETECTION_INTERVAL: 3000,    // Increased to 3 seconds
    IMAGE_QUALITY: 0.6,          // Reduced quality for better performance
    RETRY_ATTEMPTS: 2,           // Reduced retry attempts
    MAX_RESOLUTION: 640,         // Maximum image width
    VIDEO_CONSTRAINTS: {
        width: { ideal: 640, max: 640 },
        height: { ideal: 480, max: 480 },
        frameRate: { ideal: 15, max: 20 }  // Reduced frame rate
    }
};

// DOM Elements
let elements = {};

// Initialize system
document.addEventListener('DOMContentLoaded', initializeSystem);

function initializeSystem() {
    console.log('🔧 Initializing Optimized AI Vision System...');
    initializeDOMElements();
    setupEventListeners();
    setupKeyboardShortcuts();
    initializeCamera();
    testVoiceSystem();
    console.log('✅ System initialized successfully');
}

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
    
    video = elements.video;
    
    // Create reusable canvas
    canvas = document.createElement('canvas');
    ctx = canvas.getContext('2d');
}

function setupEventListeners() {
    elements.startBtn.addEventListener('click', startDetection);
    elements.stopBtn.addEventListener('click', stopDetection);
    elements.pauseBtn.addEventListener('click', pauseDetection);
    elements.refreshBtn.addEventListener('click', refreshSystem);
    
    video.addEventListener('click', toggleVideoPlayback);
    video.addEventListener('dblclick', stopCamera);
    
    // Better error handling
    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (event) => {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch(event.code) {
            case 'Space':
                event.preventDefault();
                if (detectionActive && !paused) {
                    pauseDetection();
                } else if (detectionActive && paused) {
                    pauseDetection(); // Resume
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
        }
    });
}

async function initializeCamera() {
    console.log('📹 Initializing camera...');
    updateCameraStatus('Requesting Access', 'warning');
    
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: CONFIG.VIDEO_CONSTRAINTS,
            audio: false
        });
        
        video.srcObject = stream;
        
        // Wait for video to be ready
        await new Promise((resolve) => {
            video.onloadedmetadata = () => {
                resolve();
            };
        });
        
        updateCameraStatus('Ready', 'success');
        updateSystemStatus('Camera Ready', 'success');
        
        console.log(`✅ Camera initialized: ${video.videoWidth}x${video.videoHeight}`);
        announceToUser('Camera is ready. Press Space or Start Detection button to begin.');
        
    } catch (error) {
        console.error('❌ Camera initialization failed:', error);
        updateCameraStatus('Error', 'danger');
        updateSystemStatus('Camera Error', 'danger');
        
        let errorMessage = 'Camera access failed. ';
        if (error.name === 'NotAllowedError') {
            errorMessage += 'Please allow camera access and refresh the page.';
        } else if (error.name === 'NotFoundError') {
            errorMessage += 'No camera found.';
        } else if (error.name === 'NotReadableError') {
            errorMessage += 'Camera is busy.';
        }
        
        announceToUser(errorMessage);
    }
}

function startDetection() {
    if (!stream || !video.srcObject) {
        const msg = 'Camera is not ready. Please wait.';
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
    
    updateSystemStatus('Detection Active', 'success');
    
    // Immediate first detection
    setTimeout(() => {
        if (detectionActive && !paused) {
            captureAndDetect();
        }
    }, 500);
    
    // Regular detection interval
    detectionInterval = setInterval(() => {
        if (!paused && detectionActive) {
            captureAndDetect();
        }
    }, CONFIG.DETECTION_INTERVAL);
    
    announceToUser('Object detection started.');
}

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
    
    announceToUser('Detection stopped.');
}

function pauseDetection() {
    if (!detectionActive) {
        const msg = 'Start detection first.';
        announceToUser(msg);
        return;
    }

    paused = !paused;
    const status = paused ? 'Paused' : 'Active';
    const variant = paused ? 'warning' : 'success';
    
    updateSystemStatus(`Detection ${status}`, variant);
    announceToUser(paused ? 'Detection paused.' : 'Detection resumed.');
}

function refreshSystem() {
    announceToUser('Refreshing system...');
    setTimeout(() => location.reload(), 1000);
}

function toggleVideoPlayback() {
    if (!video.srcObject) return;
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

function stopCamera() {
    stopDetection();
    
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
        stream = null;
    }
    
    updateCameraStatus('Stopped', 'secondary');
    updateSystemStatus('Camera Stopped', 'secondary');
    announceToUser('Camera stopped.');
}

async function captureAndDetect() {
    if (!video || !video.videoWidth || !video.videoHeight) {
        console.log('⚠️ Video not ready');
        return;
    }

    try {
        updateSystemStatus('Processing...', 'info');
        
        // Optimize canvas size
        const videoWidth = video.videoWidth;
        const videoHeight = video.videoHeight;
        
        let targetWidth = videoWidth;
        let targetHeight = videoHeight;
        
        // Resize if too large
        if (videoWidth > CONFIG.MAX_RESOLUTION) {
            const scale = CONFIG.MAX_RESOLUTION / videoWidth;
            targetWidth = CONFIG.MAX_RESOLUTION;
            targetHeight = Math.round(videoHeight * scale);
        }
        
        canvas.width = targetWidth;
        canvas.height = targetHeight;
        
        // Draw and compress
        ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
        const dataUrl = canvas.toDataURL('image/jpeg', CONFIG.IMAGE_QUALITY);
        
        console.log(`📸 Capturing ${targetWidth}x${targetHeight} frame...`);
        
        // Send with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const response = await fetch('/detect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                image: dataUrl,
                timestamp: Date.now()
            }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const detections = await response.json();
        handleDetectionResults(detections);
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('⏱️ Request timeout');
            updateSystemStatus('Request Timeout', 'warning');
        } else {
            console.error('❌ Detection error:', error);
            updateSystemStatus('Detection Error', 'warning');
        }
        
        // Continue detection despite errors
        updateDetectionLog('Detection error occurred, continuing...');
    }
}

function handleDetectionResults(detections) {
    if (!Array.isArray(detections)) {
        console.error('❌ Invalid detection format');
        return;
    }

    lastDetections = detections;
    
    updateDetectionLog(detections);
    updateLastDetection(detections);
    updateObjectCount(detections.length);
    
    if (detections.length > 0) {
        updateSystemStatus(`Found ${detections.length} object(s)`, 'success');
        console.log(`🎯 Detection results: ${detections.map(d => d.object).join(', ')}`);
    } else {
        updateSystemStatus('Scanning...', 'primary');
    }
}

function updateDetectionLog(detections) {
    const logElement = elements.detectionLog;
    if (!logElement) return;

    if (typeof detections === 'string') {
        logElement.innerHTML = `<div class="text-muted">${detections}</div>`;
        return;
    }

    if (!Array.isArray(detections) || detections.length === 0) {
        logElement.innerHTML = '<div class="text-muted">No objects detected</div>';
        return;
    }

    // Group by object type for cleaner display
    const grouped = {};
    detections.forEach(det => {
        if (!grouped[det.object]) {
            grouped[det.object] = [];
        }
        grouped[det.object].push(det);
    });

    const logEntries = Object.entries(grouped).map(([object, dets]) => {
        const timestamp = new Date().toLocaleTimeString();
        const locations = dets.map(d => d.location).join(', ');
        const count = dets.length > 1 ? ` (${dets.length})` : '';
        
        return `
            <div class="detection-entry mb-2 p-2 bg-light rounded">
                <div class="fw-bold text-primary">
                    ${object.charAt(0).toUpperCase() + object.slice(1)}${count}
                </div>
                <div class="text-muted">
                    Location: <em>${locations}</em>
                </div>
                <small class="text-muted">${timestamp}</small>
            </div>
        `;
    }).join('');

    logElement.innerHTML = logEntries;
    logElement.scrollTop = logElement.scrollHeight;
}

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

function updateObjectCount(count) {
    const element = elements.objectCount;
    if (!element) return;
    
    element.textContent = count.toString();
    element.className = count > 0 ? 'ms-2 fw-bold text-success' : 'ms-2 text-muted';
}

function updateSystemStatus(status, variant = 'secondary') {
    const element = elements.systemStatus;
    if (!element) return;

    element.className = element.className.replace(/bg-\w+/g, '');
    element.classList.add(`bg-${variant}`);
    element.textContent = status;
}

function updateCameraStatus(status, variant = 'secondary') {
    const element = elements.cameraStatus;
    if (!element) return;

    element.className = element.className.replace(/bg-\w+/g, '');
    element.classList.add(`bg-${variant}`);
    element.textContent = status;
}

async function testVoiceSystem() {
    console.log('🔊 Testing voice system...');
    updateVoiceStatus('Testing', 'warning');
    
    try {
        const response = await fetch('/test_voice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            updateVoiceStatus('Working', 'success');
            console.log('✅ Voice system test successful');
        } else {
            updateVoiceStatus('Error', 'warning');
            tryBrowserSpeech('Voice system using browser fallback');
        }
        
    } catch (error) {
        console.error('❌ Voice system error:', error);
        updateVoiceStatus('Browser Only', 'info');
        tryBrowserSpeech('Voice system using browser speech');
    }
}

function tryBrowserSpeech(message) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.lang = 'en-US';
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
    } else {
        updateVoiceStatus('Not Available', 'danger');
    }
}

function announceToUser(message) {
    console.log(`📢 Announcing: ${message}`);
    
    // Try backend first, then browser fallback
    fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            object: 'system',
            location: message
        })
    }).catch(() => {
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(message);
            utterance.lang = 'en-US';
            utterance.rate = 0.9;
            window.speechSynthesis.speak(utterance);
        }
    });
}

function updateVoiceStatus(status, variant = 'secondary') {
    const element = elements.voiceStatus;
    if (!element) return;

    element.className = element.className.replace(/bg-\w+/g, '');
    element.classList.add(`bg-${variant}`);
    element.textContent = status;
}

function handleGlobalError(event) {
    console.error('🚨 Global error:', event.error);
    updateSystemStatus('System Error', 'danger');
}

function handleUnhandledRejection(event) {
    console.error('🚨 Promise rejection:', event.reason);
    updateSystemStatus('Promise Error', 'warning');
}

console.log('✅ Optimized AI Vision System loaded');