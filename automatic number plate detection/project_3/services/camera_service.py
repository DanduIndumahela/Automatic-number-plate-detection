import os
import json
from config import CAMERA_CONFIG_PATH, VIDEOS_ROOT

def load_camera_config():
    if not os.path.exists(CAMERA_CONFIG_PATH):
        return None
    with open(CAMERA_CONFIG_PATH, "r") as f:
        return json.load(f)

def get_location_label(cfg: dict, cam_id: str) -> str:
    if not cfg:
        return cam_id
    locations = cfg.get("locations", {})
    inv = {}
    for loc, cid in locations.items():
        inv.setdefault(cid, []).append(loc)
    return inv.get(cam_id, [cam_id])[0]

def compute_travel_time_minutes(cam_from: str, cam_to: str, cfg: dict):
    link_details = cfg.get("link_details", {})
    key = f"{cam_from}->{cam_to}"
    link = link_details.get(key)
    if not link:
        return None
    distance = link.get("distance_km")
    speed = link.get("avg_speed_kmph")
    if distance is None or speed is None:
        return None
    distance = float(distance)
    speed = float(speed)
    if speed <= 0:
        return None
    return (distance / speed) * 60.0

def find_best_video_for_time(cam_id: str, target_dt):
    cam_folder = os.path.join(VIDEOS_ROOT, cam_id)
    if not os.path.isdir(cam_folder):
        return None

    target_date = target_dt.strftime("%Y-%m-%d")
    for ext in (".mp4", ".avi", ".mov", ".mkv"):
        p = os.path.join(cam_folder, target_date + ext)
        if os.path.exists(p):
            return p

    for fn in os.listdir(cam_folder):
        if fn.lower().endswith((".mp4", ".avi", ".mov", ".mkv")) and os.path.splitext(fn)[0] == target_date:
            return os.path.join(cam_folder, fn)
    return None