import cv2
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import streamlit as st

from config import (
    FORCE_FPS_TO_20, FORCE_FPS_VALUE, YOLO_SCALE, YOLO_CONF, YOLO_IOU,
    YOLO_IMGSZ, MOTION_THRESHOLD
)
from services.ocr_service import extract_timestamp_from_frame, ocr_plate_fast, pad_crop, PLATE_REGEX
from db.database import db_execute
from config import ANPR_DB_PATH

def insert_vehicle_log(location: str, plate_number: str, timestamp: str):
    db_execute(
        ANPR_DB_PATH,
        "INSERT OR IGNORE INTO vehicle_logs (location, plate_number, timestamp) VALUES (?, ?, ?)",
        (location, plate_number, timestamp)
    )
    return True

def process_video_common(
    video_path: str,
    cam_id: str,
    model,
    reader,
    *,
    mode: str = "admin",
    target_plate: Optional[str] = None,
    show_frames: bool = True,
    stop_when_target_found: bool = False,
    hide_other_plates: bool = False,
    start_dt: Optional[datetime] = None,
    max_minutes: int = 10,
    ui_label: Optional[str] = None,
    plate_cooldown_seconds: int = 60,
    frame_skip: int = 2
) -> Tuple[bool, Optional[datetime]]:

    OCR_EVERY = 3
    SHOW_EVERY = 10
    MIN_BOX_W = 70
    MIN_BOX_H = 20
    AR_MIN = 2.0
    AR_MAX = 7.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        st.error(f"Could not open video: {cam_id}")
        return False, None

    if FORCE_FPS_TO_20:
        cap.set(cv2.CAP_PROP_FPS, float(FORCE_FPS_VALUE))

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

    ret, first_frame = cap.read()
    if not ret:
        st.error(f"Could not read first frame: {cam_id}")
        cap.release()
        return False, None

    base_timestamp = extract_timestamp_from_frame(first_frame, reader) or datetime.now()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    if start_dt is not None:
        diff_sec = (start_dt - base_timestamp).total_seconds()
        if diff_sec > 0:
            seek_frame = int(diff_sec * fps)
            seek_frame = max(0, min(seek_frame, total_frames - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
            frame_index = seek_frame
        else:
            frame_index = 0
    else:
        frame_index = 0

    start_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) or 0
    max_frames_to_process = int(max_minutes * 60 * fps)
    end_frame_limit = min(start_frame + max_frames_to_process, total_frames)

    label = ui_label if ui_label else cam_id
    status_box = st.empty()
    live_frame_box = st.empty() if show_frames else None
    prog = st.progress(0)

    prev_gray_frame = None
    last_seen_plate_time: Dict[str, datetime] = {}
    found_target = False
    detected_dt: Optional[datetime] = None
    denom = max(1, (end_frame_limit - start_frame))
    processed_counter = 0

    while cap.isOpened():
        if frame_index >= end_frame_limit:
            break

        ret, frame = cap.read()
        if not ret:
            break

        if frame_skip > 1 and (frame_index % frame_skip != 0):
            frame_index += 1
            continue

        processed_counter += 1
        video_timestamp = base_timestamp + timedelta(seconds=(frame_index / fps))
        ts_str = video_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)

        run_yolo = False
        if prev_gray_frame is not None:
            diff = cv2.absdiff(prev_gray_frame, gray_frame)
            _, thr = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
            motion_percent = (cv2.countNonZero(thr) / thr.size) * 100.0
            if motion_percent >= MOTION_THRESHOLD:
                run_yolo = True
        else:
            run_yolo = True

        prev_gray_frame = gray_frame

        if run_yolo:
            small = cv2.resize(frame, None, fx=YOLO_SCALE, fy=YOLO_SCALE, interpolation=cv2.INTER_LINEAR)
            results = model.predict(small, conf=YOLO_CONF, iou=YOLO_IOU, imgsz=YOLO_IMGSZ, verbose=False)

            if results and results[0].boxes is not None:
                for box in results[0].boxes:
                    sx1, sy1, sx2, sy2 = map(int, box.xyxy[0])
                    x1 = int(sx1 / YOLO_SCALE)
                    y1 = int(sy1 / YOLO_SCALE)
                    x2 = int(sx2 / YOLO_SCALE)
                    y2 = int(sy2 / YOLO_SCALE)

                    x1, y1, x2, y2 = pad_crop(x1, y1, x2, y2, frame.shape[1], frame.shape[0], pad=8)
                    bw, bh = (x2 - x1), (y2 - y1)

                    if bw < MIN_BOX_W or bh < MIN_BOX_H:
                        continue
                    ar = bw / float(max(1, bh))
                    if ar < AR_MIN or ar > AR_MAX:
                        continue

                    if OCR_EVERY > 1 and (processed_counter % OCR_EVERY != 0):
                        continue

                    plate_img = frame[y1:y2, x1:x2]
                    if plate_img.size == 0:
                        continue

                    plate_text, _conf = ocr_plate_fast(reader, plate_img)
                    if not plate_text or not PLATE_REGEX.match(plate_text):
                        continue

                    last_time = last_seen_plate_time.get(plate_text)
                    if last_time and (video_timestamp - last_time).total_seconds() < plate_cooldown_seconds:
                        continue
                    last_seen_plate_time[plate_text] = video_timestamp

                    insert_vehicle_log(cam_id, plate_text, ts_str)
                    status_box.write(f"Detected | {label} | {plate_text} | {ts_str}")

                    if target_plate and plate_text == target_plate:
                        found_target = True
                        detected_dt = video_timestamp

        prog.progress(min((frame_index - start_frame) / denom, 1.0))

        if show_frames and live_frame_box and (frame_index % SHOW_EVERY == 0):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            live_frame_box.image(rgb, caption=label, use_container_width=True)

        if stop_when_target_found and found_target:
            break

        frame_index += 1

    cap.release()
    return found_target, detected_dt