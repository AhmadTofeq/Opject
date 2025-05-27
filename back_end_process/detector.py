from ultralytics import YOLO
import cv2
import os

model = YOLO(os.path.join("models", "best.pt"))

def detect_objects(frame):
    results = model(frame)[0]
    height, width = frame.shape[:2]
    detections = []

    if results.boxes is not None:
        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < 0.5:
                continue
            cls = int(box.cls[0])
            label = model.names[cls]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            x_center = (x1 + x2) // 2
            y_center = (y1 + y2) // 2
            location = get_position(x_center, y_center, width, height)
            detections.append({"object": label, "location": location})
    return detections

def get_position(x, y, width, height):
    col = int(x * 3 // width)
    row = int(y * 3 // height)
    col = min(max(col, 0), 2)
    row = min(max(row, 0), 2)
    positions = [
        ["top left", "top middle", "top right"],
        ["mid left", "center", "mid right"],
        ["bottom left", "bottom middle", "bottom right"]
    ]
    return positions[row][col]
