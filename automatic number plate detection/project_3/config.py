import os
from dotenv import load_dotenv

load_dotenv()

ANPR_DB_PATH = "anpr3.db"
USER_DB_PATH = "users3.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

MODEL_PATH = r"model\best.pt"

YOLO_CONF = 0.25
YOLO_IOU = 0.45
YOLO_SCALE = 0.6
YOLO_IMGSZ = 640

MOTION_THRESHOLD = 2.0
OCR_ALLOW = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

OTP_TTL_SECONDS = 120
SESSION_TIMEOUT = 30 * 60

CAMERA_CONFIG_PATH = "camera_config1.json"
VIDEOS_ROOT = "vide"

NEXT_CAM_OFFSET_SECONDS = 10
MAX_PROCESS_MINUTES = 10

USER_SHOW_FRAMES = False
USER_HIDE_OTHER_PLATES = True

#AVG_SPEED_KMPH = 50
#MIN_BUFFER_MINUTES = 1
#MAX_BUFFER_MINUTES = 10

DEBUG_TS_OCR = False

FORCE_FPS_TO_20 = True
FORCE_FPS_VALUE = 20

UPLOADS_DIR = "uploads"
LICENSE_DIR = os.path.join(UPLOADS_DIR, "license")
RC_DIR = os.path.join(UPLOADS_DIR, "rc")

GMAIL_SENDER_ID = os.getenv("GMAIL_SENDER_ID")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")