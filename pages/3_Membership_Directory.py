# pages/3_Membership_Directory.py

import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Membership Directory", layout="wide")

st.title("Membership Directory")
st.markdown("Directory of NEK entrepreneurial ecosystem members and stakeholders.")

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
def load_members():
    # Placeholder - adjust table name as needed
    try:
        resp = supabase.table("members").select("*").order("name").execute()
        df = pd.DataFrame(resp.data or [])
        return df
    except Exception as e:
        st.warning(f"Could not load members data: {e}")
        return pd.DataFrame()

df_members = load_members()

if not df_members.empty:
    st.dataframe(df_members, use_container_width=True)
else:
    st.info("No member data available yet. Configure the 'members' table in Supabase to populate this directory.")
