# back_end_process/detector.py
from ultralytics import YOLO
import cv2
import os
import sys

# Get the absolute path to the models directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
model_path = os.path.join(project_root, "models", "best.pt")

print(f"🔍 Loading model from: {model_path}")

# Check if model file exists
if not os.path.exists(model_path):
    print(f"❌ Model file not found at: {model_path}")
    print("Available files in models directory:")
    models_dir = os.path.join(project_root, "models")
    if os.path.exists(models_dir):
        for file in os.listdir(models_dir):
            print(f"   - {file}")
    else:
        print("   Models directory doesn't exist!")
        
    # Fallback to a pre-trained YOLOv8 model
    print("🔄 Falling back to pre-trained YOLOv8n model")
    model_path = "yolov8n.pt"

try:
    model = YOLO(model_path)
    print("✅ YOLO model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load YOLO model: {str(e)}")
    sys.exit(1)

# Important labels that we want to detect and announce
IMPORTANT_LABELS = {
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", 
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", 
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", 
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "bottle", 
    "wine glass", "cup", "fork", "knife", "spoon", "bowl", "chair", "couch", 
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", 
    "remote", "keyboard", "cell phone", "book", "clock", "vase", "scissors", 
    "teddy bear", "door", "stairs", "table"
}

def detect_objects(frame):
    """
    Detect objects in the given frame and return their positions in a 3x3 grid
    """
    if frame is None:
        print("❌ No frame provided to detector")
        return []
        
    try:
        # Run YOLO detection
        results = model(frame, conf=0.5, verbose=False)  # 50% confidence threshold
        height, width = frame.shape[:2]
        detections = []

        print(f"🔍 Frame size: {width}x{height}")
        
        # Process detections
        for result in results:
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    # Get confidence and class
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    
                    # Skip low confidence detections
                    if conf < 0.5:
                        continue
                        
                    # Get class name
                    label = model.names[cls]
                    
                    # Only announce important objects
                    if label.lower() not in IMPORTANT_LABELS:
                        continue
                    
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Calculate center point
                    x_center = (x1 + x2) // 2
                    y_center = (y1 + y2) // 2
                    
                    # Get position in 3x3 grid
                    location = get_position(x_center, y_center, width, height)
                    
                    detection = {
                        "object": label,
                        "location": location,
                        "confidence": round(conf, 2),
                        "bbox": [x1, y1, x2, y2]
                    }
                    
                    detections.append(detection)
                    
                    print(f"🎯 Detected: {label} ({conf:.2f}) at {location}")
        
        print(f"✅ Total detections: {len(detections)}")
        return detections
        
    except Exception as e:
        print(f"❌ Detection error: {str(e)}")
        return []

def get_position(x, y, width, height):
    """
    Convert pixel coordinates to 3x3 grid position
    """
    try:
        # Calculate which cell of the 3x3 grid the point falls into
        col = min(int(x * 3 // width), 2)
        row = min(int(y * 3 // height), 2)
        
        # Ensure bounds
        col = max(0, col)
        row = max(0, row)
        
        # Position names for 3x3 grid
        positions = [
            ["top left", "top center", "top right"],
            ["middle left", "center", "middle right"],
            ["bottom left", "bottom center", "bottom right"]
        ]
        
        position = positions[row][col]
        print(f"📍 Position: ({x}, {y}) -> grid[{row}][{col}] -> {position}")
        
        return position
        
    except Exception as e:
        print(f"❌ Position calculation error: {str(e)}")
        return "center"  # Default fallback