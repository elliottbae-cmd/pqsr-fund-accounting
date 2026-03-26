"""Simple password authentication for the PQSR Fund I app."""

import streamlit as st
import hmac


def check_password():
    """Gate the app behind a password prompt.

    Returns True if the user has entered the correct password.
    Password is stored in Streamlit secrets (st.secrets["app_password"]).

    Falls back to allowing access if no password is configured
    (for local development).
    """
    # If no password configured in secrets, allow access (local dev)
    try:
        app_password = st.secrets["app_password"]
    except (FileNotFoundError, KeyError):
        return True

    # Already authenticated this session
    if st.session_state.get("authenticated"):
        return True

    # Show login form
    st.set_page_config(
        page_title="PQSR Fund I | Login",
        page_icon="🔒",
        layout="centered",
    )

    # Center the login form
    st.markdown(
        "<div style='text-align: center; padding-top: 60px;'>",
        unsafe_allow_html=True,
    )

    # Show logo if available
    import os
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png"
    )
    if os.path.exists(logo_path):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo_path, use_container_width=True)

    st.markdown(
        "<h3 style='color: #494949; text-align: center;'>Accounting Portal</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #797979; text-align: center; font-size: 0.9rem;'>"
        "Enter your password to continue</p>",
        unsafe_allow_html=True,
    )

    # Password input
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Sign In", type="primary", use_container_width=True):
        if hmac.compare_digest(password, app_password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    st.markdown("</div>", unsafe_allow_html=True)

    return False
