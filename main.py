from ultralytics import YOLO
import cv2
from gtts import gTTS
import threading
import time
import os
from playsound import playsound
from deep_sort_realtime.deepsort_tracker import DeepSort

model = YOLO('yolov8x.pt')

important_labels = {"person", "car", "bus", "dog", "door", "book", "chair", "stairs", "table", "cup", "bottle", "knife", "traffic light"}


threshold_object = 0.8

tracker = DeepSort(max_age=30)

cap = cv2.VideoCapture(0)

last_spoken_labels = set()
last_spoken_ids = set()
last_spoken_time = time.time()
is_speaking = False
mute = False  # Set to True if you want to disable voice

# Get 3x3 region name
def get_position_name(x_center, y_center, frame_width, frame_height):
    col = x_center * 3 // frame_width
    row = y_center * 3 // frame_height

    positions = [
        ["top left", "top middle", "top right"],
        ["mid left", "center", "mid right"],
        ["bot left", "bot middle", "bot right"]
    ]

    return positions[int(row)][int(col)]

def speak_labels_gtts(labels):
    global is_speaking
    is_speaking = True
    try:
        persons = [l for l in labels if l.startswith("person")]
        others = [l for l in labels if not l.startswith("person")]

        sentences = []

        # Speak about persons
        if persons:
            num_persons = len(persons)
            if num_persons == 1:
                sentences.append("There is 1 person.")
            else:
                sentences.append(f"There are {num_persons} persons.")

            for person in persons:
                position = person.replace("person in ", "")
                sentences.append(f"One in {position}.")

        if others:
            if len(others) == 1:
                sentences.append("Also, I see: " + others[0])
            elif len(others) == 2:
                sentences.append("Also, I see: " + " and ".join(others))
            else:
                sentences.append("Also, I see: " + ", ".join(others[:-1]) + ", and " + others[-1])

        # Merge all into one text
        text = " ".join(sentences)

        # Text-to-speech
        tts = gTTS(text=text, lang='en')
        tts.save("temp_voice.mp3")
        playsound("temp_voice.mp3")
        os.remove("temp_voice.mp3")

    except Exception as e:
        print("TTS Error:", e)
    is_speaking = False

cv2.namedWindow("YOLOv8 + DeepSORT", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("YOLOv8 + DeepSORT", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    height, width, _ = frame.shape
    step_x = width // 3
    step_y = height // 3

    for i in range(1, 3):
        cv2.line(frame, (i * step_x, 0), (i * step_x, height), (0, 0, 255), 2)
        cv2.line(frame, (0, i * step_y), (width, i * step_y), (200, 0, 0), 2)

    region_labels = [
        ["top left", "top middle", "top right"],
        ["mid left", "center", "mid right"],
        ["bot left", "bot middle", "bot right"]
    ]
    for row in range(3):
        for col in range(3):
            label = region_labels[row][col]
            x = col * step_x + 10
            y = row * step_y + 30
            cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 255), 1)

    results_model = model(frame)
    results = results_model[0]

    detections = []
    label_dict = {}

    for box in results.boxes.data:
        x1, y1, x2, y2, conf, cls = box
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        conf = float(conf)
        label = model.names[int(cls)]

        if conf < threshold_object:
            continue
        if label not in important_labels:
            continue

        detections.append(([x1, y1, x2 - x1, y2 - y1], conf, label))
        label_dict[label] = (x1, y1, x2, y2)

    # Update tracker
    tracks = tracker.update_tracks(detections, frame=frame)
    current_labels = set()
    current_ids = set()

    for track in tracks:
        if not track.is_confirmed():
            continue
        track_id = track.track_id
        l, t, w, h = track.to_ltrb()
        x_center = int((l + w) / 2)
        y_center = int((t + h) / 2)
        label = track.get_det_class()

        position = get_position_name(x_center, y_center, width, height)
        label_pos = f"{label} in {position}"

        current_labels.add(label_pos)
        current_ids.add(track_id)

        # Draw
        cv2.rectangle(frame, (int(l), int(t)), (int(w), int(h)), (0, 255, 0), 2)
        cv2.putText(frame, f"{label} ID:{track_id}", (int(l), int(t) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    cv2.imshow("YOLOv8 + DeepSORT", frame)

    if (time.time() - last_spoken_time > 10) and (current_ids != last_spoken_ids) and not is_speaking and not mute:
        thread = threading.Thread(target=speak_labels_gtts, args=(list(current_labels),))
        thread.daemon = True
        thread.start()
        last_spoken_ids = current_ids
        last_spoken_time = time.time()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()