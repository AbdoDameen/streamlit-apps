import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sydney Weather", page_icon=":sun_behind_rain_cloud:", layout="wide")

API_URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": -33.8688,
    "longitude": 151.2093,
    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
    "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,uv_index_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max",
    "timezone": "Australia/Sydney",
    "forecast_days": 7
}

WMO = {
    0: ("Clear", chr(9732)+chr(65039)), 1: ("Mainly clear", chr(127780)), 2: ("Partly cloudy", chr(9925)),
    3: ("Overcast", chr(9729)+chr(65039)), 45: ("Foggy", chr(127787)), 48: ("Rime fog", chr(127787)),
    51: ("Light drizzle", chr(127782)+chr(65039)), 53: ("Moderate drizzle", chr(127782)+chr(65039)),
    55: ("Dense drizzle", chr(127783)), 61: ("Slight rain", chr(127782)+chr(65039)),
    63: ("Moderate rain", chr(127783)), 65: ("Heavy rain", chr(127783)),
    71: ("Slight snow", chr(127784)), 73: ("Moderate snow", chr(127784)), 75: ("Heavy snow", chr(10052)+chr(65039)),
    80: ("Rain showers", chr(127782)+chr(65039)), 81: ("Moderate showers", chr(127783)),
    82: ("Violent showers", chr(127783)), 95: ("Thunderstorm", chr(9928)+chr(65039)),
    96: ("Thunder+hail", chr(9928)+chr(65039)), 99: ("Severe thunder+hail", chr(9928)+chr(65039))
}

@st.cache_data(ttl=900)
def fetch_weather():
    r = requests.get(API_URL, params=PARAMS, timeout=10)
    r.raise_for_status()
    return r.json()

def wind_dir(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[round(deg / 22.5) % 16]

st.markdown("""
<style>
.mcard { background:#0a1628; border:1px solid #1e3a5f; border-radius:12px; padding:1.2rem; text-align:center; }
.mcard .lbl { color:#7eb8da; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px; }
.mcard .val { color:white; font-size:1.8rem; font-weight:700; }
.mcard .sub { color:#5a7a9a; font-size:0.75rem; }
.fcard { background:#0d1f3c; border:1px solid #1e3a5f; border-radius:10px; padding:0.8rem; text-align:center; }
.fcard .day { color:#7eb8da; font-size:0.8rem; }
.fcard .t { color:white; font-size:1.1rem; font-weight:600; }
.fcard .d { color:#8ab4d0; font-size:0.75rem; }
</style>
""", unsafe_allow_html=True)

st.title(":sun_behind_rain_cloud: Sydney Weather")
st.caption("Auto-refreshes every 30 min")

try:
    data = fetch_weather()
except Exception as e:
    st.error(f"Failed: {e}")
    st.stop()

cur = data["current"]
daily = data["daily"]
code = cur["weather_code"]
desc, emoji = WMO.get(code, ("Unknown", chr(10067)))

col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    st.markdown(f"<div style='text-align:center'><span style='font-size:4rem'>{emoji}</span>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align:center;font-size:3.5rem;margin:-0.5rem 0'>{cur['temperature_2m']}&deg;C</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#8ab4d0'>Feels {cur['apparent_temperature']}&deg;C &mdash; {desc}</p>", unsafe_allow_html=True)

m = st.columns(6)
items = [
    ("Humidity", f"{cur['relative_humidity_2m']}%", ""),
    ("Pressure", f"{cur['pressure_msl']} hPa", ""),
    ("Wind", f"{cur['wind_speed_10m']} km/h", f"Gusts {cur['wind_gusts_10m']}"),
    ("Dir", f"{wind_dir(cur['wind_direction_10m'])}", f"{cur['wind_direction_10m']}&deg;"),
    ("Clouds", f"{cur['cloud_cover']}%", ""),
    ("Rain", f"{cur['precipitation']} mm", f"Rain: {cur['rain']} mm"),
]
for i, (lbl, val, sub) in enumerate(items):
    with m[i]:
        st.markdown(f"<div class='mcard'><div class='lbl'>{lbl}</div><div class='val'>{val}</div><div class='sub'>{sub}</div></div>", unsafe_allow_html=True)

# 7-day
st.subheader("7-Day Forecast")
cols = st.columns(7)
for i in range(7):
    day = datetime.fromisoformat(daily["time"][i]).strftime("%a %d")
    with cols[i]:
        st.markdown(f"<div class='fcard'><div class='day'>{day}</div>"
                    f"<div class='t'>&#8593;{daily['temperature_2m_max'][i]}&deg;</div>"
                    f"<div class='t'>&#8595;{daily['temperature_2m_min'][i]}&deg;</div>"
                    f"<div class='d'>&#127783; {daily['precipitation_sum'][i]}mm</div>"
                    f"<div class='d'>&#9728;&#65039; UV {daily['uv_index_max'][i]}</div></div>",
                    unsafe_allow_html=True)

with st.expander("Detailed 7-Day Forecast"):
    df = pd.DataFrame({
        "Date": [datetime.fromisoformat(d).strftime("%a %d %b") for d in daily["time"]],
        "High": daily["temperature_2m_max"],
        "Low": daily["temperature_2m_min"],
        "Rain mm": daily["precipitation_sum"],
        "Rain Prob %": daily["precipitation_probability_max"],
        "Wind km/h": daily["wind_speed_10m_max"],
        "UV": daily["uv_index_max"],
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
