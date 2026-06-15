from datetime import datetime
import os
import re
from typing import Optional

from graphviz import Digraph
import streamlit as st

import config
from services.auth_service import (
    normalize_email, normalize_vehicle, check_email, get_user,
    create_otp, verify_otp, login_user_session, register_user, user_session_guard
)
from services.email_service import send_otp_email
from services.camera_service import load_camera_config, get_location_label
from services.ocr_service import load_models
from services.tracking_service import parse_ts_safe, auto_chain_process, fetch_vehicle_logs_for_route
from config import VIDEOS_ROOT, MODEL_PATH


def build_route_graphviz(rows, theft_dt: datetime, cfg: dict):
    dot = Digraph()
    dot.attr(rankdir="LR")

    root_id = "THEFT"
    dot.node(root_id, f"THEFT TIME\n{theft_dt.strftime('%Y-%m-%d %H:%M:%S')}", shape="box")

    if not rows:
        return dot

    seq = [(get_location_label(cfg, r[0]), r[2]) for r in rows]

    compact = []
    last_loc = None
    for loc, ts in seq:
        if loc != last_loc:
            compact.append((loc, ts))
            last_loc = loc

    prev = root_id
    for i, (loc, ts) in enumerate(compact, start=1):
        node_id = f"N{i}"
        dot.node(node_id, loc, shape="ellipse")
        dot.edge(prev, node_id, label=ts)
        prev = node_id

    return dot


def save_uploaded_file(uploaded_file, folder: str, prefix: str) -> Optional[str]:
    if uploaded_file is None:
        return None

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        ext = ".jpg"

    safe_prefix = re.sub(r"[^a-zA-Z0-9_]+", "_", prefix)
    fname = f"{safe_prefix}_{int(datetime.now().timestamp())}{ext}"
    out_path = os.path.join(folder, fname)

    os.makedirs(folder, exist_ok=True)

    with open(out_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return out_path


def render_user_page(st):
    st.title("ANPR User Portal")
    user_session_guard(st)

    if st.session_state.get("user_logged_in"):
        email = st.session_state.get("user_email")
        user = get_user(email)

        if not user:
            st.session_state.clear()
            st.error("User not found. Please register again.")
            st.stop()

        uid, full_name, email, vehicle_no, status, created_at, lic_path, rc_path = user

        st.success(f"Logged in as: {full_name} ({email})")
        st.write(f"**Vehicle No:** {vehicle_no}")
        st.write(f"**Status:** {status}")

        if status != "APPROVED":
            st.warning("Your account is not approved by Admin yet.")
            st.stop()

        st.divider()
        st.subheader("Auto Tracking (Privacy Mode)")

        cfg = load_camera_config()
        if not cfg:
            st.warning("camera_config.json is missing. Auto Tracking won't work until you add it.")
        else:
            known_locations = sorted(list(cfg.get("locations", {}).keys()))
            st.caption(f"Known locations: {', '.join(known_locations) if known_locations else 'None'}")

        start_location = st.text_input(
            "Last Seen Location (example: RGM / PANYAM / KURNOOL)",
            key="user_start_location"
        )
        theft_time_str = st.text_input(
            "Approx theft time (YYYY-MM-DD HH:MM:SS)",
            placeholder="2026-03-04 13:59:40",
            key="theft_time_input"
        )

        cA, cB, cC = st.columns(3)

        if cA.button("Start Auto Tracking", key="start_auto_tracking"):
            st.session_state["user_stop_auto"] = False

            theft_dt = parse_ts_safe(theft_time_str)
            if not theft_dt:
                st.error("Invalid theft time format. Use: YYYY-MM-DD HH:MM:SS")
                st.stop()

            if not start_location.strip():
                st.error("Please enter last seen location.")
                st.stop()

            if not os.path.isdir(VIDEOS_ROOT):
                st.error(f"Videos root folder not found: {VIDEOS_ROOT}")
                st.stop()

            model, reader = load_models(MODEL_PATH)

            st.info("Auto tracking started. Video frames are hidden for privacy.")
            chain_log = auto_chain_process(
                vehicle_no,
                start_location,
                theft_dt,
                model,
                reader,
                email,
                full_name
            )

            st.subheader("Processing Chain Summary")
            st.dataframe(chain_log, use_container_width=True, hide_index=True)

            st.subheader("Your Route Logs (DB)")
            rows = fetch_vehicle_logs_for_route(vehicle_no, theft_dt, limit=5000)

            if rows:
                cfg2 = load_camera_config()
                st.dataframe(
                    [
                        {
                            "location": get_location_label(cfg2, r[0]),
                            "plate_number": r[1],
                            "timestamp": r[2]
                        }
                        for r in rows
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("Your Route Tree")
                dot = build_route_graphviz(rows, theft_dt, cfg2)
                st.graphviz_chart(dot)
            else:
                st.warning("No logs found for your vehicle after tracking.")

        if cB.button("Stop Auto Tracking", key="stop_auto_tracking"):
            st.session_state["user_stop_auto"] = True
            st.warning("Stop requested. Current processing will stop.")

        if cC.button("Logout", key="user_logout"):
            st.session_state.clear()
            st.rerun()

        st.stop()

    tab1, tab2 = st.tabs(["Login (Email OTP)", "Register"])

    with tab1:
        st.subheader("Login with Email + OTP")
        email = normalize_email(
            st.text_input("Email Address", placeholder="example@gmail.com", key="login_email")
        )
        col1, col2 = st.columns(2)

        if col1.button("Send OTP", key="send_otp_btn"):
            if not check_email(email):
                st.error("Enter valid email address.")
            else:
                user = get_user(email)
                if not user:
                    st.error("This email is not registered. Please register first.")
                else:
                    status = user[4]
                    if status != "APPROVED":
                        st.warning("Your account is not approved by Admin yet.")
                    else:
                        otp = create_otp(email, ttl_seconds=config.OTP_TTL_SECONDS)
                        ok, msg = send_otp_email(email, otp)
                        if ok:
                            st.success("OTP sent to your email.")
                        else:
                            st.error(f"Failed to send OTP email: {msg}")

        entered = st.text_input("Enter OTP", max_chars=6, key="login_otp")

        if col2.button("Verify OTP & Login", key="verify_login_btn"):
            if not check_email(email):
                st.error("Enter valid email address.")
            else:
                user = get_user(email)
                if not user:
                    st.error("Not registered. Please register first.")
                else:
                    status = user[4]
                    if status != "APPROVED":
                        st.warning("Your account is not approved by Admin yet.")
                    else:
                        ok, msg = verify_otp(email, entered)
                        if ok:
                            try:
                                login_user_session(st, email)
                            except TypeError:
                                login_user_session(email)
                            st.success("Login success!")
                            st.rerun()
                        else:
                            st.error(msg)

    with tab2:
        st.subheader("Register New User")

        full_name = st.text_input("Full Name", key="reg_fullname")
        email_r = normalize_email(
            st.text_input("Email Address", placeholder="example@gmail.com", key="reg_email")
        )
        vehicle_no = normalize_vehicle(
            st.text_input("Vehicle Number", placeholder="AP09AB1234", key="reg_vehicle")
        )

        st.markdown("### Upload Documents")
        license_img = st.file_uploader(
            "Upload Driving License Image",
            type=["png", "jpg", "jpeg", "webp"],
            key="reg_license"
        )
        rc_img = st.file_uploader(
            "Upload RC Book Image",
            type=["png", "jpg", "jpeg", "webp"],
            key="reg_rc"
        )

        if st.button("Register", key="reg_btn"):
            if not full_name.strip():
                st.error("Enter full name.")
            elif not check_email(email_r):
                st.error("Enter valid email address.")
            elif len(vehicle_no) < 6:
                st.error("Enter valid vehicle number.")
            elif license_img is None or rc_img is None:
                st.error("Please upload both License and RC images.")
            else:
                safe_prefix = email_r.replace("@", "_").replace(".", "_")
                license_path = save_uploaded_file(license_img, config.LICENSE_DIR, prefix=safe_prefix)
                rc_path = save_uploaded_file(rc_img, config.RC_DIR, prefix=safe_prefix)

                ok, msg = register_user(full_name.strip(), email_r, vehicle_no, license_path, rc_path)
                if ok:
                    st.success(msg)
                    u = get_user(email_r)
                    if u:
                        st.subheader("Registered Details")
                        st.table([{
                            "id": u[0],
                            "full_name": u[1],
                            "email": u[2],
                            "vehicle_no": u[3],
                            "status": u[4],
                            "created_at": u[5],
                            "license_img_path": u[6],
                            "rc_img_path": u[7],
                        }])

                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption("License Preview")
                            if u[6] and os.path.exists(u[6]):
                                st.image(u[6], use_container_width=True)
                        with c2:
                            st.caption("RC Preview")
                            if u[7] and os.path.exists(u[7]):
                                st.image(u[7], use_container_width=True)
                else:
                    st.warning(msg)