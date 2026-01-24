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
    resp = supabase.table("members").select("*").order("name").execute()
    df = pd.DataFrame(resp.data or [])
    return df

df_all = load_members()

expected_cols = [
    "id",
    "name",
    "organization",
    "role",
    "email",
    "phone",
    "region",
    "member_type",
    "expertise_areas",
    "status",
    "notes",
    "updated_at",
]

if df_all.empty:
    df_all = pd.DataFrame(columns=expected_cols)
else:
    for c in expected_cols:
        if c not in df_all.columns:
            df_all[c] = None

# -------------------------
# Filters
# -------------------------
st.subheader("Members (Editable)")

col1, col2 = st.columns(2)
with col1:
    status_choices = ["All", "Active", "Inactive"]
    selected_status = st.selectbox("Filter by status", status_choices, index=0)

with col2:
    type_choices = ["All", "Entrepreneur", "Mentor", "Investor", "Service Provider", "Other"]
    selected_type = st.selectbox("Filter by member type", type_choices, index=0)

df = df_all.copy()
if selected_status != "All":
    df = df[df["status"] == selected_status]
if selected_type != "All":
    df = df[df["member_type"] == selected_type]

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
        "role": st.column_config.TextColumn("Role"),
        "email": st.column_config.TextColumn("Email"),
        "phone": st.column_config.TextColumn("Phone"),
        "region": st.column_config.TextColumn("Region"),
        "member_type": st.column_config.SelectboxColumn(
            "Member Type",
            options=["Entrepreneur", "Mentor", "Investor", "Service Provider", "Other"],
        ),
        "expertise_areas": st.column_config.TextColumn("Expertise Areas"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=["Active", "Inactive"],
            required=True,
        ),
        "notes": st.column_config.TextColumn("Notes"),
        "updated_at": st.column_config.TextColumn("Updated At", disabled=True),
    },
)

if row_ids is not None:
    edited_df.insert(0, "id", row_ids)

# -------------------------
# Save logic
# -------------------------
if st.button(" Save changes to directory"):
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
            "role",
            "email",
            "phone",
            "region",
            "member_type",
            "expertise_areas",
            "status",
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
        
        to_update, to_insert = [], []
        
        for r in records:
            if r.get("id"):
                to_update.append(r)
            else:
                r.pop("id", None)
                to_insert.append(r)
        
        if to_update:
            supabase.table("members").upsert(to_update).execute()
        
        if to_insert:
            supabase.table("members").insert(to_insert).execute()
        
        load_members.clear()
        st.success("Directory updated successfully.")
        st.rerun()
        
    except Exception as e:
        st.error("Failed to save changes.")
        st.exception(e)

st.caption(
    "Tip: Use the filters above to narrow down the member list. Add new rows directly in the table."
)
