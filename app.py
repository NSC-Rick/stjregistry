import streamlit as st


st.set_page_config(
    page_title="NEK Entrepreneurial Registry Portal",
    layout="wide",
)


# --- Shared Password Gate ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Protected Workspace")
    pwd = st.text_input("Enter access password", type="password")

    if pwd:
        if pwd == st.secrets.get("APP_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    st.caption("This workspace is for internal use.")
    st.stop()
# --- End Password Gate ---

st.title("NEK Registry")

st.markdown(
    """
This is a working prototype of a regional registry portal built with Streamlit.

What this prototype includes:
- Simple, readable pages
- In-memory sample data (where applicable)

What this prototype intentionally excludes:
- Authentication
- Database or persistent storage
- External APIs or integrations
"""
)
