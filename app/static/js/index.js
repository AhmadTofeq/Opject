let stream = null;
let video = null;
let paused = false;

document.addEventListener('DOMContentLoaded', () => {
    video = document.getElementById('cameraFeed');

    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then((mediaStream) => {
            stream = mediaStream;
            video.srcObject = mediaStream;
        })
        .catch((err) => {
            alert("Camera access denied or not available.");
            console.error("Camera error:", err);
        });

    // Single click: pause/resume
    video.addEventListener('click', () => {
        if (!video.srcObject) return;

        if (!paused) {
            video.pause();
        } else {
            video.play();
        }
        paused = !paused;
    });

    // Double click: stop camera
    video.addEventListener('dblclick', () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            video.srcObject = null;
            paused = false;
        }
    });
});
