import pandas as pd
import streamlit as st
from datetime import date


st.title("NEK Entrepreneurial Initiative Registry")


st.write(
    """
    This registry tracks active, proposed, and completed initiatives
    supporting the NEK entrepreneurial ecosystem.
    """
)

# --- Sample data (MVP only) ---
data = [
    {
        "Initiative Name": "NEK Entrepreneur Roundtables",
        "Region": "NEK-wide",
        "Status": "Active",
        "Lead Steward": "Rick",
        "Last Check-In": date(2025, 1, 10),
        "Next Check-In": date(2025, 2, 10),
        "Notes": "Monthly facilitator rotation working well."
    },
    {
        "Initiative Name": "Downtown Startup Pop-Ups",
        "Region": "St. Johnsbury",
        "Status": "Proposed",
        "Lead Steward": "TBD",
        "Last Check-In": None,
        "Next Check-In": None,
        "Notes": ""
    }
]

df = pd.DataFrame(data)

# --- Status filter ---
status_filter = st.selectbox(
    "Filter by status",
    ["All", "Proposed", "Active", "Paused", "Completed"]
)

if status_filter != "All":
    df = df[df["Status"] == status_filter]

st.subheader("Editable Initiative Table")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            options=["Proposed", "Active", "Paused", "Completed"]
        ),
        "Last Check-In": st.column_config.DateColumn(),
        "Next Check-In": st.column_config.DateColumn(),
        "Notes": st.column_config.TextColumn()
    },
    #disabled=["Initiative Name"]
)

# --- Save action (MVP placeholder) ---
if st.button("Save changes"):
    st.success("Changes captured (in-memory for now).")
    st.caption("In the next phase, this will persist to a database.")