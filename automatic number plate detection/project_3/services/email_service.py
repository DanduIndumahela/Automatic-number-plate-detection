import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_SENDER_ID, GMAIL_APP_PASSWORD, ADMIN_EMAIL, OTP_TTL_SECONDS

logger = logging.getLogger(__name__)

def send_email(receiver, subject, body):
    if not GMAIL_SENDER_ID or not GMAIL_APP_PASSWORD:
        logger.error("Sender ID or App Password not found in environment variables.")
        return False, "Email settings missing in .env"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER_ID
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(GMAIL_SENDER_ID, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_SENDER_ID, receiver, msg.as_string())
        return True, "Email sent"
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False, str(e)

def send_otp_email(email: str, otp: str):
    subject = "Your ANPR Portal OTP"
    body = f"""Hello,

Your OTP for ANPR Portal login is: {otp}

This OTP is valid for {OTP_TTL_SECONDS} seconds.

Regards,
ANPR Portal
"""
    return send_email(email, subject, body)

def send_detection_alert(user_email: str, user_name: str, vehicle_no: str, chain_log: list):
    if not chain_log:
        return (False, "No detections"), (False, "No detections")

    lines = []
    for i, item in enumerate(chain_log, start=1):
        lines.append(f"{i}. Location: {item['location']} | Time: {item['detected_time']}")
    detections_text = "\n".join(lines)

    user_subject = "Vehicle Detection Summary - ANPR"
    user_body = f"""Hello {user_name},

Your vehicle tracking process has completed.

Vehicle Number: {vehicle_no}

Detected Locations:
{detections_text}
"""

    admin_subject = "Admin Vehicle Detection Summary - ANPR"
    admin_body = f"""Hello Admin,

User Name: {user_name}
User Email: {user_email}
Vehicle Number: {vehicle_no}

Detected Locations:
{detections_text}
"""

    ok1, msg1 = send_email(user_email, user_subject, user_body)
    ok2, msg2 = send_email(ADMIN_EMAIL, admin_subject, admin_body)
    return (ok1, msg1), (ok2, msg2)