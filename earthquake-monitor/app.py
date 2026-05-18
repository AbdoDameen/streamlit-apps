import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Earthquake Monitor", page_icon=":earthquake:", layout="wide")

st.markdown("""
<style>
.mcard { background:#1a0a0a; border:1px solid #3a1a1a; border-radius:10px; padding:1rem; text-align:center; }
.mcard .lbl { color:#cc8888; font-size:0.8rem; }
.mcard .val { color:#ff6666; font-size:2rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.title(":earthquake: Earthquake Monitor")
st.caption("Real-time seismic activity from USGS")

TIMEFRAMES = {"Past Hour": "all_hour", "Past Day": "all_day", "Past Week": "all_week", "Past Month": "all_month"}

@st.cache_data(ttl=60)
def fetch_quakes(timeframe):
    r = requests.get(f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{timeframe}.geojson", timeout=10)
    r.raise_for_status()
    return r.json()

tf = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=2)
try:
    data = fetch_quakes(TIMEFRAMES[tf])
except Exception as e:
    st.error(f"Failed: {e}")
    st.stop()

features = data.get("features", [])
rows = []
coords = []
for f in features:
    props = f["properties"]
    geo = f["geometry"]
    lon, lat, depth = geo["coordinates"]
    mag = props.get("mag") or 0
    rows.append({
        "time": datetime.fromtimestamp(props["time"] / 1000).strftime("%Y-%m-%d %H:%M"),
        "place": props.get("place", "Unknown"),
        "mag": round(mag, 1),
        "depth_km": round(depth, 1),
        "type": props.get("type", "earthquake"),
        "tsunami": props.get("tsunami", 0),
        "url": props.get("url", ""),
    })
    if lat and lon:
        coords.append({"lat": lat, "lon": lon, "mag": mag})

df = pd.DataFrame(rows)
min_mag = st.slider("Minimum Magnitude", 0.0, 10.0, 0.0, 0.5)
df = df[df["mag"] >= min_mag]

kpi = st.columns(4)
with kpi[0]: st.markdown(f"<div class='mcard'><div class='lbl'>Earthquakes</div><div class='val'>{len(df)}</div></div>", unsafe_allow_html=True)
with kpi[1]: st.markdown(f"<div class='mcard'><div class='lbl'>Avg Magnitude</div><div class='val'>{df['mag'].mean():.1f}</div></div>", unsafe_allow_html=True)
with kpi[2]: st.markdown(f"<div class='mcard'><div class='lbl'>Largest</div><div class='val'>{df['mag'].max():.1f}</div></div>", unsafe_allow_html=True)
with kpi[3]: st.markdown(f"<div class='mcard'><div class='lbl'>Deepest (km)</div><div class='val'>{df['depth_km'].max():.0f}</div></div>", unsafe_allow_html=True)

# Heatmap
st.subheader("Seismic Activity Map")
coords_df = pd.DataFrame([c for c in coords if c["mag"] >= min_mag])
if not coords_df.empty:
    st.map(coords_df, latitude="lat", longitude="lon", size="mag")
else:
    st.info("No earthquakes in this range")

# Table
st.subheader("Recent Earthquakes")
def color_mag(v):
    if v < 3: return "background: #1a3a1a"
    elif v < 5: return "background: #3a3a1a"
    return "background: #3a1a1a"
styled = df.style.map(color_mag, subset=["mag"])
st.dataframe(styled, use_container_width=True, hide_index=True)

auto = st.checkbox("Auto-refresh (60s)")
if auto:
    st.rerun()
