"""
Flight Tracker - Live aircraft tracking via OpenSky Network API
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
import time

# ─── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Live Flight Tracker",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS (aviation dark theme) ─────────────────────────
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0a1628;
    }
    .main .block-container {
        padding-top: 1.5rem;
    }
    h1, h2, h3 {
        color: #ffffff !important;
    }
    .stMarkdown p, .stMarkdown span, .stTextInput label, .stSelectbox label {
        color: #e0e0e0 !important;
    }
    .kpi-card {
        background: linear-gradient(135deg, #003366 0%, #004d99 100%);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 51, 102, 0.3);
        border: 1px solid #0055aa;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #aaccee;
        margin-top: 0.2rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .timestamp {
        color: #88aacc;
        font-size: 0.8rem;
        text-align: right;
        margin-top: -0.5rem;
    }
    .stCheckbox label {
        color: #e0e0e0 !important;
    }
    .stMultiSelect label {
        color: #e0e0e0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Title ─────────────────────────────────────────────────────
st.title("✈️ Live Flight Tracker")
st.markdown("<p style='color:#88aacc;'>Real-time aircraft positions from the OpenSky Network</p>", unsafe_allow_html=True)

# ─── Sidebar controls ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### Controls")
    auto_refresh = st.checkbox("Auto-refresh every 30s", value=True)
    st.markdown("---")
    st.markdown(
        "Data provided by [OpenSky Network](https://opensky-network.org/). "
        "Free API has rate limits — errors are handled gracefully."
    )

# ─── Data fetching ────────────────────────────────────────────
@st.cache_data(ttl=25, show_spinner="Fetching flight data...")
def fetch_flights():
    url = "https://opensky-network.org/api/states/all"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states", [])
        if not states:
            return pd.DataFrame()
        cols = [
            "icao24", "callsign", "origin_country", "time_position",
            "last_contact", "longitude", "latitude", "baro_altitude",
            "on_ground", "velocity", "true_track", "vertical_rate",
            "sensors", "geo_altitude", "squawk", "spi", "position_source",
        ]
        df = pd.DataFrame(states, columns=cols)
        # Clean callsign (strip whitespace)
        df["callsign"] = df["callsign"].str.strip()
        # Replace null/None lat/lon
        df = df.dropna(subset=["latitude", "longitude"])
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch flight data: {e}")
        return pd.DataFrame()
    except (KeyError, ValueError, TypeError) as e:
        st.error(f"Error parsing flight data: {e}")
        return pd.DataFrame()


# ─── Main data load ───────────────────────────────────────────
df = fetch_flights()
now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# ─── KPIs ─────────────────────────────────────────────────────
if not df.empty:
    total_aircraft = len(df)
    countries = df["origin_country"].nunique()
    on_ground = int(df["on_ground"].sum())
    airborne = total_aircraft - on_ground

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value'>{total_aircraft:,}</div>"
            f"<div class='kpi-label'>Total Aircraft</div></div>",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value'>{countries}</div>"
            f"<div class='kpi-label'>Countries</div></div>",
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value'>{airborne:,}</div>"
            f"<div class='kpi-label'>Airborne</div></div>",
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value'>{on_ground:,}</div>"
            f"<div class='kpi-label'>On Ground</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(f"<p class='timestamp'>Last updated: {now_str}</p>", unsafe_allow_html=True)
else:
    st.warning("No flight data available. The API may be rate-limiting. Try again shortly.")
    total_aircraft = 0
    countries = 0

# ─── Country filter ───────────────────────────────────────────
if not df.empty:
    country_list = sorted(df["origin_country"].unique())
    selected_countries = st.multiselect(
        "Filter by country",
        options=country_list,
        default=[],
        placeholder="Select countries...",
    )
    if selected_countries:
        df = df[df["origin_country"].isin(selected_countries)]

# ─── Map ──────────────────────────────────────────────────────
if not df.empty:
    st.subheader("🛩️ Live Aircraft Positions")

    airborne_df = df[df["on_ground"] == False].dropna(subset=["latitude", "longitude"]).copy()
    if not airborne_df.empty:
        map_df = airborne_df[["latitude", "longitude"]].rename(
            columns={"latitude": "lat", "longitude": "lon"}
        )
        st.map(map_df, use_container_width=True)
    else:
        st.info("No airborne aircraft in the current filter selection.")

    # ─── Transparent overlay stats ─────────────────────────────
    st.markdown(
        f"""
        <div style="
            position: relative;
            background: rgba(0, 51, 102, 0.85);
            border-radius: 8px;
            padding: 0.6rem 1rem;
            margin-top: -0.5rem;
            margin-bottom: 1rem;
            border: 1px solid #0055aa;
            color: #ffffff;
            font-size: 0.85rem;
            display: inline-block;
        ">
            ✈️ {len(airborne_df) if not airborne_df.empty else 0} airborne · 
            🌍 {airborne_df['origin_country'].nunique() if not airborne_df.empty else 0} countries
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─── Data table ────────────────────────────────────────────
    st.subheader("📋 Flight Details")

    display_cols = {
        "callsign": "Callsign",
        "origin_country": "Country",
        "baro_altitude": "Altitude (ft)",
        "velocity": "Speed (kts)",
        "true_track": "Heading (°)",
        "vertical_rate": "V. Rate (ft/min)",
        "on_ground": "On Ground",
    }

    table_df = df[list(display_cols.keys())].copy()
    # Convert on_ground to yes/no
    table_df["on_ground"] = table_df["on_ground"].map({True: "🟢 Yes", False: "🔴 No"})
    # Fill nulls
    table_df = table_df.fillna("—")
    table_df = table_df.rename(columns=display_cols)

    col_config = {}
    for col in ["Altitude (ft)", "Speed (kts)", "Heading (°)", "V. Rate (ft/min)"]:
        col_config[col] = st.column_config.NumberColumn(col, format="%.0f")

    st.dataframe(
        table_df,
        column_config=col_config,
        use_container_width=True,
        height=400,
        hide_index=True,
    )

# ─── Auto-refresh ────────────────────────────────────────────
if auto_refresh and not df.empty:
    time.sleep(0.1)
    st.rerun()
