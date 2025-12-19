import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
import os

# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(layout="wide")
st.title("NEK Entrepreneurial Initiative Registry")

st.caption(
    "This registry supports shared visibility and stewardship of NEK-wide "
    "entrepreneurial initiatives. Changes are saved to the central registry."
)

# ------------------------------------------------------------
# Supabase connection
# ------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Supabase credentials not found. Check Streamlit Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------
@st.cache_data
def load_initiatives():
    response = supabase.table("initiatives").select("*").execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        return df

    # Normalize date columns
    for col in ["last_check_in", "next_check_in"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    return df


df = load_initiatives()

# ------------------------------------------------------------
# Empty-state handling
# ------------------------------------------------------------
if df.empty:
    st.info("No initiatives found yet. Add your first initiative below.")
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
        ]
    )

# ------------------------------------------------------------
# Filters
# ------------------------------------------------------------
status_filter = st.selectbox(
    "Filter by status",
    ["All", "Proposed", "Active", "Paused", "Completed"],
)

display_df = df.copy()

if status_filter != "All" and not display_df.empty:
    display_df = display_df[display_df["status"] == status_filter]

# ------------------------------------------------------------
# Editable table
# ------------------------------------------------------------
st.subheader("Initiatives")

edited_df = st.data_editor(
    display_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "initiative_name": st.column_config.TextColumn(
            "Initiative Name", required=True
        ),
        "region": st.column_config.TextColumn("Region"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=["Proposed", "Active", "Paused", "Completed"],
            required=True,
        ),
        "lead_steward": st.column_config.TextColumn("Lead Steward"),
        "last_check_in": st.column_config.DateColumn("Last Check-In"),
        "next_check_in": st.column_config.DateColumn("Next Check-In"),
        "notes": st.column_config.TextColumn("Notes"),
    },
    disabled=["id"],  # internal key only
)

# ------------------------------------------------------------
# Save changes
# ------------------------------------------------------------
st.divider()

if st.button("💾 Save changes to registry"):
    try:
        records = edited_df.to_dict(orient="records")

        # Remove empty IDs so Supabase can create them
        for r in records:
            if not r.get("id"):
                r.pop("id", None)

        supabase.table("initiatives").upsert(records).execute()

        load_initiatives.clear()
        st.success("Registry updated successfully.")

    except Exception as e:
        st.error("Failed to save changes.")
        st.exception(e)

# ------------------------------------------------------------
# Guidance
# ------------------------------------------------------------
st.caption(
    "Tip: Initiative names should be changed deliberately once in use. "
    "Persistent storage is provided by Supabase."
)
