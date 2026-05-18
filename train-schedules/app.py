import streamlit as st
import requests
import pandas as pd
from datetime import datetime as dt

st.set_page_config(page_title="Train Schedules", page_icon=":train:", layout="wide")

st.markdown("""
<style">
.departure-board { background:#111; border:2px solid #ffcc00; border-radius:8px; padding:1rem; font-family:'Courier New',monospace; }
.departure-board .line { color:#ffcc00; font-size:0.9rem; }
.departure-board .dest { color:white; font-size:1rem; }
.departure-board .time { color:#00ff00; font-size:1rem; font-weight:bold; }
.departure-board .delay { color:#ff4444; font-size:0.9rem; }
.departure-board .platform { color:#888; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

st.title(":train: Live Train Departures")
st.caption("Real-time departures via transport.rest (European coverage)")

@st.cache_data(ttl=3600)
def search_stations(query):
    r = requests.get(f"https://v6.transport.rest/locations?query={query}&poi=true&addresses=false", timeout=10)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=60)
def fetch_departures(station_id, duration=60):
    r = requests.get(f"https://v6.transport.rest/stations/{station_id}/departures?duration={duration}", timeout=10)
    r.raise_for_status()
    return r.json()

DEFAULT_STATIONS = {
    "Berlin Hbf": "8011160",
    "Paris Gare du Nord": "8727100",
    "London Liverpool St": "8089108",
    "Amsterdam Centraal": "8400058",
    "Zürich HB": "8503000",
    "Wien Hbf": "8103000",
    "Milano Centrale": "8300052",
    "Madrid Atocha": "7175987",
}

st.sidebar.header("Station")
search_query = st.sidebar.text_input("Search station", value="Berlin")
favorites = st.sidebar.multiselect("Quick select", list(DEFAULT_STATIONS.keys()), default=["Berlin Hbf"])

station_id = None
station_name = None

if favorites:
    station_name = favorites[0]
    station_id = DEFAULT_STATIONS[station_name]

if search_query and not station_id:
    try:
        results = search_stations(search_query)
        if results:
            station_options = {r["name"]: r["id"] for r in results if "id" in r and "name" in r}
            selected = st.sidebar.selectbox("Select station", list(station_options.keys()))
            station_name = selected
            station_id = station_options[selected]
    except Exception as e:
        st.sidebar.warning(f"Search failed: {e}")

duration = st.sidebar.slider("Look ahead (min)", 15, 120, 60)

if station_id:
    st.subheader(f"Departures from {station_name}")
    try:
        deps = fetch_departures(station_id, duration)
        if "departures" in deps and deps["departures"]:
            for dep in deps["departures"][:30]:
                line = dep.get("line", {}).get("name", dep.get("line", {}).get("mode", "?"))
                dest = dep.get("destination", {}).get("name", "Unknown")
                planned = dep.get("plannedWhen", "")
                estimated = dep.get("when", "")
                delay = dep.get("delay", 0)
                platform = dep.get("platform", "?")

                if planned and estimated:
                    pt = dt.fromisoformat(planned.replace("Z", "+00:00")).strftime("%H:%M")
                    et = dt.fromisoformat(estimated.replace("Z", "+00:00")).strftime("%H:%M")
                else:
                    pt = "??:??"
                    et = "??:??"

                if delay and delay > 0:
                    time_display = f"<span style='color:#ff4444'>{et}</span> <span style='color:#888'>(planned {pt})</span> +{delay // 60}min"
                else:
                    time_display = f"<span style='color:#00ff00'>{pt}</span>"

                st.markdown(f"""
                <div style='background:#1a1a1a; border-left:4px solid #ffcc00; padding:0.7rem 1rem; margin:0.3rem 0; border-radius:4px'>
                    <div style='display:flex; justify-content:space-between'>
                        <span style='color:#ffcc00; font-weight:600'>{line}</span>
                        <span style='color:white; font-weight:600'>{dest}</span>
                        <span>{time_display}</span>
                        <span style='color:#888'>Platform {platform}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            auto = st.checkbox("Auto-refresh (30s)")
            if auto:
                st.rerun()
        else:
            st.info("No departures found for this station")
    except Exception as e:
        st.error(f"Failed to fetch departures: {e}")
        st.info("Try a different station. European stations work best with this API.")
else:
    st.info("Search for a station in the sidebar, or select a favorite")
