import re
import time
import random
import hashlib
from typing import Optional
from config import USER_DB_PATH, OTP_TTL_SECONDS, SESSION_TIMEOUT
from db.database import db_fetch_one, db_execute

def normalize_vehicle(v: str) -> str:
    return (v or "").strip().upper().replace(" ", "")

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def check_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, (email or "").strip()))

def sanitize_email(text: str) -> Optional[str]:
    if not text:
        return None
    text = text.lower().replace(" at the rate ", "@").replace(" at ", "@").replace(" dot ", ".")
    text = text.replace(" underscore ", "_").replace(" dash ", "-")
    text = re.sub(r"\s+", "", text)
    return text if check_email(text) else None

def normalize_email(e: str) -> str:
    return (sanitize_email(e) or "").lower()

def get_user(email: str):
    return db_fetch_one(
        USER_DB_PATH,
        """SELECT id, full_name, email, vehicle_no, status, created_at,
                  license_img_path, rc_img_path
           FROM users WHERE email=?""",
        (email,)
    )

def register_user(full_name: str, email: str, vehicle_no: str, license_path: str, rc_path: str):
    try:
        db_execute(
            USER_DB_PATH,
            """
            INSERT INTO users (full_name, email, vehicle_no, status, created_at, license_img_path, rc_img_path)
            VALUES (?, ?, ?, 'PENDING', datetime('now','localtime'), ?, ?)
            """,
            (full_name, email, vehicle_no, license_path, rc_path)
        )
        return True, "Registered successfully. Wait for Admin approval."
    except Exception:
        return False, "Email already registered. Please login."

def create_otp(email: str, ttl_seconds: int = OTP_TTL_SECONDS) -> str:
    otp = str(random.randint(100000, 999999))
    expires_at = int(time.time()) + ttl_seconds
    db_execute(
        USER_DB_PATH,
        "INSERT OR REPLACE INTO otp_store (email, otp_hash, expires_at) VALUES (?, ?, ?)",
        (email, sha256_hex(otp), expires_at)
    )
    return otp

def verify_otp(email: str, entered: str):
    row = db_fetch_one(USER_DB_PATH, "SELECT otp_hash, expires_at FROM otp_store WHERE email=?", (email,))
    if not row:
        return False, "OTP not generated. Click 'Send OTP'."
    saved_hash, expires_at = row
    if int(time.time()) > int(expires_at):
        return False, "OTP expired. Click 'Send OTP' again."
    if sha256_hex(entered.strip()) != saved_hash:
        return False, "Invalid OTP."
    db_execute(USER_DB_PATH, "DELETE FROM otp_store WHERE email=?", (email,))
    return True, "OTP verified."

def login_user_session(st, email: str):
    st.session_state["user_logged_in"] = True
    st.session_state["user_email"] = email
    st.session_state["user_last_active"] = int(time.time())

def user_session_guard(st):
    if st.session_state.get("user_logged_in"):
        now = int(time.time())
        last = st.session_state.get("user_last_active", now)
        if now - last > SESSION_TIMEOUT:
            st.session_state.clear()
            st.warning("Session expired. Please login again.")
            st.stop()
        st.session_state["user_last_active"] = now