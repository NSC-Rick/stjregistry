# pages/1_Initiatives.py

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date

st.set_page_config(page_title="Initiatives", layout="wide")

st.title("NEK Entrepreneurial Initiative Registry")
st.markdown(
    "This registry supports shared visibility and stewardship of NEK-wide "
    "entrepreneurial initiatives. Changes are saved to the central registry."
)

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
def load_initiatives():
    resp = supabase.table("initiatives").select("*").order("initiative_name").execute()
    df = pd.DataFrame(resp.data or [])

    # 🔑 CRITICAL: Normalize date columns for Streamlit
    for col in ["last_check_in", "next_check_in"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    return df

df = load_initiatives()

if df.empty:
    df = pd.DataFrame(
        columns=[
            "id",
            "initiative_name",
            "region",
            "status",
            "lead_steward",
            "last_check_in",
            "next_check_in",
            "notes",
            "updated_at",
        ]
    )

# -------------------------
# Status filter
# -------------------------
status_options = ["All"] + sorted(
    [s for s in df["status"].dropna().unique()]
)

selected_status = st.selectbox("Filter by status", status_options)

if selected_status != "All":
    df = df[df["status"] == selected_status]

# -------------------------
# Editable table
# -------------------------
st.subheader("Initiatives")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": st.column_config.TextColumn(
            "id",
            disabled=True,
            help="System-generated unique identifier",
        ),
        "initiative_name": st.column_config.TextColumn(
            "Initiative Name",
            required=True,
        ),
        "region": st.column_config.TextColumn("Region"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=["Proposed", "Active", "Paused", "Completed"],
        ),
        "lead_steward": st.column_config.TextColumn("Lead Steward"),
        "last_check_in": st.column_config.DateColumn("Last Check-In"),
        "next_check_in": st.column_config.DateColumn("Next Check-In"),
        "notes": st.column_config.TextColumn("Notes"),
        "updated_at": st.column_config.TextColumn(
            "updated_at",
            disabled=True,
        ),
    },
)

# -------------------------
# Save logic
# -------------------------
if st.button("💾 Save changes to registry"):
    try:
        work = edited_df.copy()

        # Normalize column names
        work.columns = [
            c.strip().lower().replace(" ", "_").replace("-", "_")
            for c in work.columns
        ]

        # Drop empty rows
        work = work.dropna(how="all")

        # Convert NaN -> None
        work = work.where(pd.notnull(work), None)

        records = work.to_dict(orient="records")

        to_update = []
        to_insert = []

        for r in records:
            raw_id = r.get("id")
            if raw_id and str(raw_id).strip():
                to_update.append(r)
            else:
                r.pop("id", None)
                to_insert.append(r)

        if to_update:
            supabase.table("initiatives").upsert(to_update).execute()

        if to_insert:
            supabase.table("initiatives").insert(to_insert).execute()

        load_initiatives.clear()
        st.success("Registry updated successfully.")

    except Exception as e:
        st.error("Failed to save changes.")
        st.exception(e)

st.caption(
    "Tip: Initiative names should be changed deliberately once in use. "
    "Persistent storage is provided by Supabase."
)
