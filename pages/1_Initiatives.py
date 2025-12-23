# pages/1_Initiatives.py

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import timedelta

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

    for col in ["last_check_in", "next_check_in"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


df_all = load_initiatives()

expected_cols = [
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

if df_all.empty:
    df_all = pd.DataFrame(columns=expected_cols)
else:
    for c in expected_cols:
        if c not in df_all.columns:
            df_all[c] = pd.NaT if "check_in" in c else None

# -------------------------
# Filters
# -------------------------
st.subheader("Initiatives (Editable)")

status_choices = ["All", "Proposed", "Active", "Paused", "Completed"]
selected_status = st.selectbox("Filter by status", status_choices, index=0)

df = df_all.copy()
if selected_status != "All":
    df = df[df["status"] == selected_status]

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
        "initiative_name": st.column_config.TextColumn("Initiative Name", required=True),
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
        "updated_at": st.column_config.TextColumn("updated_at", disabled=True),
    },
)

# Reattach IDs
if row_ids is not None:
    edited_df.insert(0, "id", row_ids)

# -------------------------
# Save logic
# -------------------------
if st.button("💾 Save changes to registry"):
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
            "initiative_name",
            "region",
            "status",
            "lead_steward",
            "last_check_in",
            "next_check_in",
            "notes",
        }
        work = work[[c for c in work.columns if c in allowed_cols]]

        records = work.to_dict(orient="records")

        # ✅ FINAL, CORRECT serialization
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
            supabase.table("initiatives").upsert(to_update).execute()

        if to_insert:
            supabase.table("initiatives").insert(to_insert).execute()

        load_initiatives.clear()
        st.success("Registry updated successfully.")

    except Exception as e:
        st.error("Failed to save changes.")
        st.exception(e)

st.caption(
    "Tip: Keep 'next check-in' dates lightweight — the dashboard will surface overdue and due-soon items automatically."
)
