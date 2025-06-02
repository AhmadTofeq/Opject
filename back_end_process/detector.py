# back_end_process/detector.py - Optimized version
from ultralytics import YOLO
import cv2
import os
import sys
import time
import gc

# Get the absolute path to the models directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
model_path = os.path.join(project_root, "models", "best.pt")

print(f"🔍 Loading model from: {model_path}")

# Check if model file exists
if not os.path.exists(model_path):
    print(f"❌ Model file not found at: {model_path}")
    models_dir = os.path.join(project_root, "models")
    if os.path.exists(models_dir):
        print("Available files in models directory:")
        for file in os.listdir(models_dir):
            print(f"   - {file}")
    else:
        print("   Models directory doesn't exist!")
        
    # Fallback to a pre-trained YOLOv8 model
    print("🔄 Falling back to pre-trained YOLOv8n model")
    model_path = "yolov8n.pt"

try:
    # Load model with optimized settings
    model = YOLO(model_path)
    model.overrides['verbose'] = False  # Reduce logging
    print("✅ YOLO model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load YOLO model: {str(e)}")
    sys.exit(1)

# Optimized important labels - reduced set for better performance
IMPORTANT_LABELS = {
    "person", "car", "bus", "dog", "cat", "chair", "bottle",
    "cup", "book", "cell phone", "laptop", "tv", "couch", 
    "dining table", "toilet", "door", "stairs"
}

# Performance tracking
last_detection_time = 0
detection_count = 0

def detect_objects(frame):
    """
    Detect objects in the given frame and return their positions in a 3x3 grid
    Optimized for better performance and stability
    """
    global last_detection_time, detection_count
    
    start_time = time.time()
    
    if frame is None:
        print("❌ No frame provided to detector")
        return []
        
    try:
        # Get frame dimensions
        height, width = frame.shape[:2]
        print(f"🔍 Processing frame: {width}x{height}")
        
        # Optimize detection parameters for performance
        results = model(
            frame, 
            conf=0.6,        # Increased confidence threshold
            iou=0.45,        # IoU threshold for NMS
            max_det=20,      # Limit max detections
            verbose=False,   # Disable verbose output
            save=False,      # Don't save results
            show=False       # Don't show results
        )
        
        detections = []
        processed_boxes = []
        
        # Process detections with improved filtering
        for result in results:
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    try:
                        # Get confidence and class
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        
                        # Skip low confidence detections
                        if conf < 0.6:
                            continue
                            
                        # Get class name
                        label = model.names[cls].lower()
                        
                        # Only process important objects
                        if label not in IMPORTANT_LABELS:
                            continue
                        
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Validate bounding box
                        if x2 <= x1 or y2 <= y1:
                            continue
                            
                        # Calculate center point
                        x_center = (x1 + x2) // 2
                        y_center = (y1 + y2) // 2
                        
                        # Check if this detection overlaps significantly with existing ones
                        bbox = [x1, y1, x2, y2]
                        if not is_duplicate_detection(bbox, processed_boxes, threshold=0.3):
                            processed_boxes.append(bbox)
                            
                            # Get position in 3x3 grid
                            location = get_position(x_center, y_center, width, height)
                            
                            detection = {
                                "object": label,
                                "location": location,
                                "confidence": round(conf, 2),
                                "bbox": bbox
                            }
                            
                            detections.append(detection)
                            print(f"🎯 Detected: {label} ({conf:.2f}) at {location}")
                            
                    except Exception as e:
                        print(f"❌ Error processing detection: {str(e)}")
                        continue
        
        # Sort detections by confidence (highest first)
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Limit number of detections to prevent overload
        if len(detections) > 8:
            detections = detections[:8]
            print(f"⚠️ Limited detections to 8 (from {len(detections)})")
        
        # Performance tracking
        processing_time = time.time() - start_time
        detection_count += 1
        last_detection_time = time.time()
        
        print(f"✅ Detection completed: {len(detections)} objects in {processing_time:.2f}s")
        
        # Clean up memory
        del results
        gc.collect()
        
        return detections
        
    except Exception as e:
        print(f"❌ Detection error: {str(e)}")
        return []

def is_duplicate_detection(bbox1, existing_boxes, threshold=0.3):
    """
    Check if a bounding box significantly overlaps with existing detections
    """
    x1, y1, x2, y2 = bbox1
    area1 = (x2 - x1) * (y2 - y1)
    
    for existing_bbox in existing_boxes:
        ex1, ey1, ex2, ey2 = existing_bbox
        
        # Calculate intersection
        ix1 = max(x1, ex1)
        iy1 = max(y1, ey1)
        ix2 = min(x2, ex2)
        iy2 = min(y2, ey2)
        
        if ix2 > ix1 and iy2 > iy1:
            intersection = (ix2 - ix1) * (iy2 - iy1)
            overlap_ratio = intersection / area1
            
            if overlap_ratio > threshold:
                return True
                
    return False

def get_position(x, y, width, height):
    """
    Convert pixel coordinates to 3x3 grid position with improved accuracy
    """
    try:
        # Add small margin to prevent edge cases
        margin = 0.05  # 5% margin
        
        # Calculate grid position with margins
        col_width = width / 3
        row_height = height / 3
        
        col = int(x / col_width)
        row = int(y / row_height)
        
        # Ensure bounds
        col = max(0, min(2, col))
        row = max(0, min(2, row))
        
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

def get_detection_stats():
    """
    Get detection performance statistics
    """
    return {
        "total_detections": detection_count,
        "last_detection_time": last_detection_time,
        "model_loaded": model is not None
    }