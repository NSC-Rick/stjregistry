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
    resp = supabase.table("speakers").select("*").order("name").execute()
    df = pd.DataFrame(resp.data or [])
    
    if "last_spoke_date" in df.columns:
        df["last_spoke_date"] = pd.to_datetime(df["last_spoke_date"], errors="coerce")
    
    return df


df_all = load_speakers()

expected_cols = [
    "id",
    "name",
    "organization",
    "title",
    "email",
    "phone",
    "bio",
    "topics",
    "availability",
    "speaking_fee",
    "region",
    "website",
    "linkedin",
    "last_spoke_date",
    "notes",
    "updated_at",
]

if df_all.empty:
    df_all = pd.DataFrame(columns=expected_cols)
else:
    for c in expected_cols:
        if c not in df_all.columns:
            df_all[c] = pd.NaT if c == "last_spoke_date" else None

# -------------------------
# Filters
# -------------------------
st.subheader("Speakers (Editable)")

col1, col2 = st.columns(2)
with col1:
    availability_choices = ["All", "Available", "Limited", "Unavailable"]
    selected_availability = st.selectbox("Filter by availability", availability_choices, index=0)

with col2:
    region_filter = st.text_input("Filter by region (optional)")

df = df_all.copy()
if selected_availability != "All":
    df = df[df["availability"] == selected_availability]
if region_filter:
    df = df[df["region"].str.contains(region_filter, case=False, na=False)]

base_df = df.reset_index(drop=True).copy()

# -------------------------
# Hide system ID
# -------------------------
row_ids = base_df["id"] if "id" in base_df.columns else None
base_df = base_df.drop(columns=["id"], errors="ignore")

# -------------------------
# Editor
# -------------------------
edited_df = st.data_editor(
    base_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "name": st.column_config.TextColumn("Name", required=True),
        "organization": st.column_config.TextColumn("Organization"),
        "title": st.column_config.TextColumn("Title"),
        "email": st.column_config.TextColumn("Email"),
        "phone": st.column_config.TextColumn("Phone"),
        "bio": st.column_config.TextColumn("Bio"),
        "topics": st.column_config.TextColumn("Topics"),
        "availability": st.column_config.SelectboxColumn(
            "Availability",
            options=["Available", "Limited", "Unavailable"],
        ),
        "speaking_fee": st.column_config.TextColumn("Speaking Fee"),
        "region": st.column_config.TextColumn("Region"),
        "website": st.column_config.TextColumn("Website"),
        "linkedin": st.column_config.TextColumn("LinkedIn"),
        "last_spoke_date": st.column_config.DateColumn("Last Spoke Date"),
        "notes": st.column_config.TextColumn("Notes"),
        "updated_at": st.column_config.TextColumn("Updated At", disabled=True),
    },
)

if row_ids is not None:
    edited_df.insert(0, "id", row_ids)

# -------------------------
# Save logic
# -------------------------
if st.button("💾 Save changes to directory"):
    try:
        work = edited_df.copy()
        work = work.where(pd.notnull(work), None)
        
        work.columns = [
            c.strip().lower().replace(" ", "_").replace("-", "_")
            for c in work.columns
        ]
        
        work = work.dropna(how="all")
        
        allowed_cols = {
            "id",
            "name",
            "organization",
            "title",
            "email",
            "phone",
            "bio",
            "topics",
            "availability",
            "speaking_fee",
            "region",
            "website",
            "linkedin",
            "last_spoke_date",
            "notes",
        }
        work = work[[c for c in work.columns if c in allowed_cols]]
        
        records = work.to_dict(orient="records")
        
        for r in records:
            for k, v in list(r.items()):
                if v is None:
                    continue
                if pd.isna(v):
                    r[k] = None
                elif isinstance(v, pd.Timestamp):
                    r[k] = v.date().isoformat()
        
        to_update, to_insert = [], []
        
        for r in records:
            if r.get("id"):
                to_update.append(r)
            else:
                r.pop("id", None)
                to_insert.append(r)
        
        if to_update:
            supabase.table("speakers").upsert(to_update).execute()
        
        if to_insert:
            supabase.table("speakers").insert(to_insert).execute()
        
        load_speakers.clear()
        st.success("Directory updated successfully.")
        st.rerun()
        
    except Exception as e:
        st.error("Failed to save changes.")
        st.exception(e)

st.caption(
    "Tip: Use the filters above to find available speakers. Add new rows directly in the table."
)
