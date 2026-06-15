import streamlit as st

def apply_modern_ui():
    with open("ui/styles.css", "r", encoding="utf-8") as f:
        css = f.read()

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="page-header-card">
            <h2 class="page-title">VISSION TRACK</h2>
            <p class="page-subtitle">Admin Surveillance Dashboard</p>
        </div>
        """,
        unsafe_allow_html=True
    )