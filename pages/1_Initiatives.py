# pages/1_Initiatives.py

import streamlit as st
import pandas as pd
from supabase import create_client
import datetime as dt

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

    # Normalize date columns for Streamlit
    for col in ["last_check_in", "next_check_in"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    return df


df_all = load_initiatives()

# Ensure expected columns exist even if empty
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
            df_all[c] = None

# -------------------------
# Dashboard Metrics (calm, useful)
# -------------------------
today = dt.date.today()
due_window_days = 14

# Define "active-ish" as things we still care to review
activeish_statuses = ["Active", "Proposed"]

activeish_df = df_all[df_all["status"].isin(activeish_statuses)]

overdue_df = df_all[
    (df_all["status"].isin(activeish_statuses))
    & (df_all["next_check_in"].notna())
    & (df_all["next_check_in"] < today)
].copy()

due_soon_df = df_all[
    (df_all["status"].isin(activeish_statuses))
    & (df_all["next_check_in"].notna())
    & (df_all["next_check_in"] >= today)
    & (df_all["next_check_in"] <= (today + dt.timedelta(days=due_window_days)))
].copy()

recent_df = df_all[
    (df_all["last_check_in"].notna())
    & (df_all["last_check_in"] >= (today - dt.timedelta(days=30)))
].copy()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Active / Proposed", int(len(activeish_df)))
c2.metric("Overdue", int(len(overdue_df)))
c3.metric(f"Due Soon ({due_window_days}d)", int(len(due_soon_df)))
c4.metric("Updated (30d)", int(len(recent_df)))

st.divider()

# -------------------------
# Needs Attention Panel
# -------------------------
st.subheader("Needs Attention")

show_due_soon = st.checkbox("Show due-soon items (in addition to overdue)", value=True)

cols_focus = ["initiative_name", "region", "lead_steward", "status", "next_check_in", "last_check_in"]

if len(overdue_df) == 0 and (not show_due_soon or len(due_soon_df) == 0):
    st.info("Nothing urgent right now — no overdue items (and none due soon, if enabled).")
else:
    if len(overdue_df) > 0:
        st.markdown("**Overdue** (next check-in date has passed)")
        st.dataframe(
            overdue_df[cols_focus].sort_values(by=["next_check_in", "initiative_name"], na_position="last"),
            use_container_width=True,
            hide_index=True,
        )

    if show_due_soon and len(due_soon_df) > 0:
        st.markdown(f"**Due Soon** (next {due_window_days} days)")
        st.dataframe(
            due_soon_df[cols_focus].sort_values(by=["next_check_in", "initiative_name"], na_position="last"),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

# -------------------------
# Filters (for the editable working table)
# -------------------------
st.subheader("Initiatives (Editable)")

status_choices = ["All", "Proposed", "Active", "Paused", "Completed"]
selected_status = st.selectbox("Filter by status", status_choices, index=0)

df = df_all.copy()
if selected_status != "All":
    df = df[df["status"] == selected_status]

# Use a stable copy for the editor
base_df = df.reset_index(drop=True).copy()

edited_df = st.data_editor(
    base_df,
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
            required=True,
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
# Save logic (robust, Supabase-safe)
# -------------------------
if st.button("💾 Save changes to registry"):
    try:
        work = edited_df.copy()

        # Normalize column names defensively
        work.columns = [
            c.strip().lower().replace(" ", "_").replace("-", "_")
            for c in work.columns
        ]

        # Drop completely empty rows (phantom editor row)
        work = work.dropna(how="all")

        # Convert NaN -> None (but keep date objects for now)
        work = work.where(pd.notnull(work), None)

        # Keep payload strictly to known columns (avoid overwriting updated_at etc.)
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

        # Convert date objects -> ISO strings, and NaT/NaN -> None
        for r in records:
            for k, v in list(r.items()):
                if pd.isna(v):
                    r[k] = None
                elif isinstance(v, dt.date):
                    r[k] = v.isoformat()

        to_update = []
        to_insert = []

        for r in records:
            raw_id = r.get("id")

            # Empty string IDs should be treated as missing IDs
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
    "Tip: Keep 'next check-in' dates lightweight — the dashboard will surface overdue and due-soon items automatically."
)
