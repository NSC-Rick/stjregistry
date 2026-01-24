# pages/4_Speaker_Directory.py

import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Speaker Directory", layout="wide")

st.title("Speaker Directory")
st.markdown("Directory of available speakers for NEK entrepreneurial events and programs.")

# -------------------------
# Supabase connection
# -------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Supabase credentials not found. Check Streamlit Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# -------------------------
# Data loading
# -------------------------
@st.cache_data(ttl=60)
def load_speakers():
    # Placeholder - adjust table name as needed
    try:
        resp = supabase.table("speakers").select("*").order("name").execute()
        df = pd.DataFrame(resp.data or [])
        return df
    except Exception as e:
        st.warning(f"Could not load speakers data: {e}")
        return pd.DataFrame()

df_speakers = load_speakers()

if not df_speakers.empty:
    st.dataframe(df_speakers, use_container_width=True)
else:
    st.info("No speaker data available yet. Configure the 'speakers' table in Supabase to populate this directory.")
