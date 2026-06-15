from datetime import datetime
import os
import streamlit as st
from db.database import db_fetch_all, db_execute
from config import MODEL_PATH, USER_DB_PATH, ANPR_DB_PATH, VIDEOS_ROOT, MAX_PROCESS_MINUTES
from services.camera_service import load_camera_config, get_location_label, find_best_video_for_time
from services.ocr_service import load_models
from services.video_service import process_video_common

def require_admin_login(st, admin_username, admin_password):
    if st.session_state.get("admin_logged_in", False):
        return
    st.subheader("Admin Login")
    with st.form("admin_login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Login")
    if ok:
        if u == admin_username and p == admin_password:
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid admin credentials")
    st.stop()

def render_admin_page(st, admin_username, admin_password):
    st.title("Admin Panel")
    require_admin_login(st, admin_username, admin_password)
    # keep your current admin menus here using imported helpers
    
    st.sidebar.header("Admin Menu")
    menu = st.sidebar.radio(
        "Go to",
        ["Approvals", "Approved Users", "Search Logs", "Process Camera Videos", "Logout"],
        key="admin_menu"
    )

    if menu == "Logout":
        st.session_state["admin_logged_in"] = False
        st.success("Logged out")
        st.rerun()

    if menu == "Approvals":
        st.subheader("New User Registrations (Approve / Reject)")

        pending = db_fetch_all(
            USER_DB_PATH,
            """
            SELECT id, full_name, email, vehicle_no, status, created_at, license_img_path, rc_img_path
            FROM users
            WHERE status='PENDING'
            ORDER BY id DESC
            LIMIT 500
            """
        )

        if not pending:
            st.info("No pending users")
        else:
            st.warning(f"Pending users: {len(pending)}")
            for uid, name, email, vehicle_no, status, created_at, license_path, rc_path in pending:
                with st.container(border=True):
                    st.write(f"Name: **{name}** | Email: **{email}** | Vehicle: **{vehicle_no}**")
                    st.caption(f"Status: {status} | Registered: {created_at}")

                    cimg1, cimg2 = st.columns(2)
                    with cimg1:
                        st.caption("License Image")
                        if license_path and os.path.exists(license_path):
                            st.image(license_path, use_container_width=True)
                        else:
                            st.info("Missing license image")
                    with cimg2:
                        st.caption("RC Image")
                        if rc_path and os.path.exists(rc_path):
                            st.image(rc_path, use_container_width=True)
                        else:
                            st.info("Missing RC image")

                    c1, c2 = st.columns(2)
                    if c1.button("Approve", key=f"approve_{uid}"):
                        db_execute(USER_DB_PATH, "UPDATE users SET status='APPROVED' WHERE id=?", (uid,))
                        st.success(f"Approved: {email}")
                        st.rerun()

                    if c2.button("Reject", key=f"reject_{uid}"):
                        db_execute(USER_DB_PATH, "UPDATE users SET status='REJECTED' WHERE id=?", (uid,))
                        st.error(f"Rejected: {email}")
                        st.rerun()

    if menu == "Approved Users":
        st.subheader("Approved Users")

        q = st.text_input("Search by email / vehicle / name", key="approved_search").strip()

        sql = """
            SELECT id, full_name, email, vehicle_no, status, created_at, license_img_path, rc_img_path
            FROM users
            WHERE status='APPROVED'
        """
        params = []
        if q:
            sql += " AND (email LIKE ? OR vehicle_no LIKE ? OR full_name LIKE ?)"
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]

        sql += " ORDER BY id DESC LIMIT 500"
        rows = db_fetch_all(USER_DB_PATH, sql, tuple(params))

        st.success(f"Approved users found: {len(rows)}")

        for uid, name, email, vehicle_no, status, created_at, license_path, rc_path in rows:
            with st.container(border=True):
                st.markdown(f"### {name}")
                st.write(f"Email: **{email}** | Vehicle: **{vehicle_no}** | Status: **{status}**")
                st.caption(f"Created: {created_at}")

                c1, c2 = st.columns(2)
                with c1:
                    st.caption("License")
                    if license_path and os.path.exists(license_path):
                        st.image(license_path, use_container_width=True)
                    else:
                        st.info("Missing")
                with c2:
                    st.caption("RC")
                    if rc_path and os.path.exists(rc_path):
                        st.image(rc_path, use_container_width=True)
                    else:
                        st.info("Missing")

                colA, colB = st.columns(2)
                if colA.button("Reject User", key=f"reject_approved_{uid}"):
                    db_execute(USER_DB_PATH, "UPDATE users SET status='REJECTED' WHERE id=?", (uid,))
                    st.error("User rejected.")
                    st.rerun()

                if colB.button("Move to PENDING", key=f"pending_again_{uid}"):
                    db_execute(USER_DB_PATH, "UPDATE users SET status='PENDING' WHERE id=?", (uid,))
                    st.warning("Moved back to pending.")
                    st.rerun()

    if menu == "Search Logs":
        st.subheader("Search ANPR Logs")

        c1, c2, c3 = st.columns(3)
        plate_q = c1.text_input("Plate contains (optional)", key="admin_plate").strip().upper()
        location_q = c2.text_input("Camera ID contains (optional)", key="admin_location").strip().upper()
        limit = c3.number_input("Limit", 10, 5000, 200, 10, key="admin_limit")

        if st.button("Search", key="admin_search_btn"):
            q2 = "SELECT id, location, plate_number, timestamp FROM vehicle_logs"
            params2 = []
            where = []
            if plate_q:
                where.append("plate_number LIKE ?")
                params2.append(f"%{plate_q}%")
            if location_q:
                where.append("location LIKE ?")
                params2.append(f"%{location_q}%")
            if where:
                q2 += " WHERE " + " AND ".join(where)
            q2 += " ORDER BY id DESC LIMIT ?"
            params2.append(int(limit))

            rows = db_fetch_all(ANPR_DB_PATH, q2, tuple(params2))
            st.success(f"Found: {len(rows)}")
            st.table([{"id": r[0], "location": r[1], "plate_number": r[2], "timestamp": r[3]} for r in rows])

        if st.button("Show Latest", key="admin_show_latest"):
            rows = db_fetch_all(
                ANPR_DB_PATH,
                "SELECT id, location, plate_number, timestamp FROM vehicle_logs ORDER BY id DESC LIMIT 200"
            )
            st.table([{"id": r[0], "location": r[1], "plate_number": r[2], "timestamp": r[3]} for r in rows])

    if menu == "Process Camera Videos":
        st.subheader("Process Camera Videos (Admin)")

        st.code(
            f"""{VIDEOS_ROOT}/
  C01/ 2026-03-04.mp4
  C02/ 2026-03-04.mp4
""",
            language="text"
        )

        if not os.path.isdir(VIDEOS_ROOT):
            st.error(f"Videos root folder not found: {VIDEOS_ROOT}")
            st.stop()

        cam_ids = sorted([d for d in os.listdir(VIDEOS_ROOT) if os.path.isdir(os.path.join(VIDEOS_ROOT, d))])
        if not cam_ids:
            st.warning(f"No camera folders found inside {VIDEOS_ROOT}")
            st.stop()

        selected_cams = st.multiselect("Select camera folders", cam_ids, default=cam_ids)

        date_str = st.text_input("Date to process (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
        start_time_str = st.text_input("Start time (HH:MM:SS)", value="00:00:00")
        max_minutes = st.number_input("Max minutes per camera", 1, 120, int(MAX_PROCESS_MINUTES), 1)

        colA, colB = st.columns(2)
        if colA.button("Start Processing", key="admin_start_cam_processing"):
            st.session_state["stop_processing"] = False
            st.session_state["run_cam_processing"] = True

        if colB.button("Stop", key="admin_stop_cam_processing"):
            st.session_state["stop_processing"] = True

        if st.session_state.get("run_cam_processing", False) and not st.session_state.get("stop_processing", False):
            try:
                admin_start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M:%S")
            except Exception:
                st.error("Invalid date/time format. Use YYYY-MM-DD and HH:MM:SS")
                st.stop()

            model, reader = load_models(MODEL_PATH)
            cfg = load_camera_config()

            for cam_id in selected_cams:
                if st.session_state.get("stop_processing", False):
                    break

                video_path = find_best_video_for_time(cam_id, admin_start_dt)
                if not video_path:
                    st.warning(f"{cam_id}: No day-wise video found for {date_str}")
                    continue

                label = get_location_label(cfg, cam_id) if cfg else cam_id
                st.write(f"## Camera: {cam_id} ({label}) | Video: {os.path.basename(video_path)}")

                process_video_common(
                    video_path,
                    cam_id,
                    model,
                    reader,
                    mode="admin",
                    target_plate=None,
                    show_frames=True,
                    stop_when_target_found=False,
                    hide_other_plates=False,
                    start_dt=admin_start_dt,
                    max_minutes=int(max_minutes),
                    ui_label=f"{cam_id} ({label})",
                    frame_skip=2
                )

            st.success("Admin processing completed!")
            st.session_state["run_cam_processing"] = False
