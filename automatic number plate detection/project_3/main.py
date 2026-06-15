import streamlit as st

from config import ADMIN_USERNAME, ADMIN_PASSWORD
from db.database import init_databases
from ui.styles import apply_modern_ui
from ui.admin_page import render_admin_page
from ui.user_page import render_user_page

st.set_page_config(page_title="ANPR Portal", layout="wide")
apply_modern_ui()
init_databases()

def get_page_param() -> str:
    try:
        return st.query_params.get("page", "")
    except Exception:
        qp = st.experimental_get_query_params()
        return (qp.get("page", [""])[0]) if qp else ""

page = get_page_param()

if page == "admin":
    render_admin_page(st, ADMIN_USERNAME, ADMIN_PASSWORD)
else:
    render_user_page(st)