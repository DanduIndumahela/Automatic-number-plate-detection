from collections import deque
from datetime import datetime, timedelta
import streamlit as st

from config import (
    USER_SHOW_FRAMES, USER_HIDE_OTHER_PLATES, MAX_PROCESS_MINUTES,
    NEXT_CAM_OFFSET_SECONDS, MIN_BUFFER_MINUTES, MAX_BUFFER_MINUTES,
    ANPR_DB_PATH
)
from services.camera_service import load_camera_config, get_location_label, find_best_video_for_time, compute_travel_time_minutes
from services.video_service import process_video_common
from services.email_service import send_detection_alert
from db.database import db_fetch_all

def parse_ts_safe(s: str):
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def auto_chain_process(target_plate, start_location, theft_dt, model, reader, user_email, user_name):
    cfg = load_camera_config()
    if not cfg:
        st.error("camera_config.json not found or invalid.")
        return []

    locations = cfg.get("locations", {})
    graph = cfg.get("camera_graph", {})

    loc_key = (start_location or "").strip().upper()
    if loc_key not in locations:
        st.error(f"Location not mapped in camera_config.json: {start_location}")
        return []

    start_cam = locations[loc_key]
    q = deque([(start_cam, theft_dt, None, None)])
    processed_cameras = set()
    chain_log = []

    while q:
        if st.session_state.get("user_stop_auto", False):
            st.warning("Auto tracking stopped by user.")
            break

        cam_id, search_time, prev_detected_time, prev_cam = q.popleft()

        if cam_id in processed_cameras:
            continue
        processed_cameras.add(cam_id)

        video_path = find_best_video_for_time(cam_id, search_time)
        label = get_location_label(cfg, cam_id)

        st.write(f"### Processing {label} @ {search_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if not video_path:
            st.warning(f"No video found for {label}. Skipping.")
            continue

        found, detected_dt = process_video_common(
            video_path,
            cam_id,
            model,
            reader,
            target_plate=target_plate,
            show_frames=USER_SHOW_FRAMES,
            stop_when_target_found=True,
            start_dt=search_time,
            max_minutes=MAX_PROCESS_MINUTES,
            ui_label=label,
            frame_skip=2
        )

        if not detected_dt:
            st.warning(f"Plate not detected at {label}. Chain stopped.")
            continue

        chain_log.append({
            "location": label,
            "detected_time": detected_dt.strftime("%Y-%m-%d %H:%M:%S")
        })

        if prev_detected_time and prev_cam:
            actual_gap = (detected_dt - prev_detected_time).total_seconds() / 60.0
            travel_minutes = compute_travel_time_minutes(prev_cam, cam_id, cfg)
            if travel_minutes is not None:
                min_allowed = travel_minutes - MIN_BUFFER_MINUTES
                max_allowed = travel_minutes + MAX_BUFFER_MINUTES
                if actual_gap < min_allowed or actual_gap > max_allowed:
                    st.warning(
                        f"Unrealistic detection at {label}. Expected {min_allowed:.1f}-{max_allowed:.1f} min, got {actual_gap:.1f} min."
                    )
                    continue

        base_time = detected_dt
        for next_cam in graph.get(cam_id, []):
            travel_minutes = compute_travel_time_minutes(cam_id, next_cam, cfg)
            if travel_minutes is None:
                next_search_time = base_time + timedelta(seconds=NEXT_CAM_OFFSET_SECONDS)
            else:
                next_search_time = base_time + timedelta(minutes=max(0.0, travel_minutes - MIN_BUFFER_MINUTES))
            q.append((next_cam, next_search_time, detected_dt, cam_id))

    if chain_log:
        send_detection_alert(user_email, user_name, target_plate, chain_log)

    return chain_log

def fetch_vehicle_logs_for_route(vehicle_no: str, start_dt: datetime, end_dt=None, limit: int = 5000):
    q = """
        SELECT location, plate_number, timestamp
        FROM vehicle_logs
        WHERE plate_number = ?
          AND timestamp >= ?
    """
    params = [vehicle_no, start_dt.strftime("%Y-%m-%d %H:%M:%S")]
    if end_dt:
        q += " AND timestamp <= ?"
        params.append(end_dt.strftime("%Y-%m-%d %H:%M:%S"))
    q += " ORDER BY timestamp ASC LIMIT ?"
    params.append(int(limit))
    return db_fetch_all(ANPR_DB_PATH, q, tuple(params))