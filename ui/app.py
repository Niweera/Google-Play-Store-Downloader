from os.path import abspath, join, dirname, realpath
import streamlit as st
import sqlite3
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
from config.Config import SQLITE_DB_NAME

st.set_page_config(page_title="GPSD Dashboard")
st.title("Google Play Store Downloader Dashboard")

main_db_path = abspath(
    join(dirname(dirname(realpath(__file__))), "databases", SQLITE_DB_NAME)
)

conn = sqlite3.connect(main_db_path)
cursor = conn.cursor()

# Auto-refresh every 60 seconds
st_autorefresh(interval=60 * 1000, key="autorefresh")

col1, col2 = st.columns(2)

with col1:
    cursor.execute("SELECT COUNT(*) FROM input_apps")
    total_apps = cursor.fetchone()[0]
    st.metric("Total number of apps", total_apps)

with col2:
    cursor.execute("SELECT COUNT(*) FROM input_apps WHERE downloaded = 1")
    downloaded_apps = cursor.fetchone()[0]
    st.metric("Downloaded apps", downloaded_apps)

n = st.number_input("Number of devices used", min_value=1, value=6)

query_download_queue = f"""
SELECT COUNT(*) AS download_queue_count
FROM (
    SELECT DISTINCT i.app_id
    FROM input_apps i
    LEFT JOIN error_apps e ON i.app_id = e.app_id
    WHERE i.downloaded = 0
    GROUP BY e.error, i.app_id
    HAVING COUNT(DISTINCT e.device) < {n} OR COUNT(e.device) = 0
    EXCEPT
    SELECT DISTINCT ea.app_id
    FROM error_apps ea
    WHERE ea.app_id IN (
        SELECT app_id FROM input_apps WHERE downloaded = 0
    )
    AND ea.error = 'App is incompatible'
    GROUP BY ea.error, ea.app_id
    HAVING COUNT(DISTINCT ea.device) = {n}
);
"""

df_queue = pd.read_sql_query(query_download_queue, conn)

query_incompatible_apps = f"""
SELECT COUNT(*) AS incompatible_app_count
FROM (
    SELECT DISTINCT ea.app_id
    FROM error_apps ea
    WHERE ea.app_id IN (
        SELECT app_id FROM input_apps WHERE downloaded = 0
    )
    AND ea.error = 'App is incompatible'
    GROUP BY ea.error, ea.app_id
    HAVING COUNT(DISTINCT ea.device) = {n}
)
"""

df_incompatible = pd.read_sql_query(query_incompatible_apps, conn)

col1, col2 = st.columns(2)

with col1:
    st.metric("Apps in download queue", df_queue.iloc[0]["download_queue_count"])

with col2:
    st.metric(
        "Number of apps that are incompatible",
        df_incompatible.iloc[0]["incompatible_app_count"],
    )

query_subset = f"""
SELECT 
    NOT EXISTS (
        SELECT DISTINCT i.app_id
        FROM input_apps i
        LEFT JOIN error_apps e ON i.app_id = e.app_id
        WHERE i.downloaded = 0
        GROUP BY e.error, i.app_id
        HAVING COUNT(DISTINCT e.device) < {n} OR COUNT(e.device) = 0
        EXCEPT
        SELECT DISTINCT ea.app_id
        FROM error_apps ea
        WHERE ea.app_id IN (
            SELECT app_id FROM input_apps WHERE downloaded = 0
        )
        AND ea.error = 'App is incompatible'
        GROUP BY ea.error, ea.app_id
        HAVING COUNT(DISTINCT ea.device) = {n}
    ) AS is_subset
"""

df_subset = pd.read_sql_query(query_subset, conn)
is_all_downloaded = bool(df_subset.iloc[0]["is_subset"])
if is_all_downloaded:
    st.subheader("All apps are downloaded.")
else:
    st.subheader("Apps are still downloading...")

    # ETA Calculation
    T_remaining = total_apps - (
        downloaded_apps + df_incompatible.iloc[0]["incompatible_app_count"]
    )
    current_time = datetime.now()

    if "progress_history" not in st.session_state:
        st.session_state.progress_history = []

    st.session_state.progress_history.append((current_time, T_remaining))

    cutoff_time = current_time - timedelta(minutes=10)
    st.session_state.progress_history = [
        (t, r) for (t, r) in st.session_state.progress_history if t >= cutoff_time
    ]

    eta_text = "ETA: calculating..."
    if len(st.session_state.progress_history) >= 2:
        t_old, r_old = st.session_state.progress_history[0]
        t_new, r_new = st.session_state.progress_history[-1]
        delta_apps = r_old - r_new
        delta_minutes = (t_new - t_old).total_seconds() / 60
        if delta_apps > 0 and delta_minutes > 0:
            rate = delta_apps / delta_minutes
            eta_seconds = int(T_remaining / rate * 60)
            eta_timedelta = timedelta(seconds=eta_seconds)
            hours, remainder = divmod(eta_timedelta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            eta_text = f"Estimated time to complete: ~{hours}h {minutes}m {seconds}s"
        else:
            eta_text = "ETA: No progress detected"

    st.info(eta_text)


conn.close()
