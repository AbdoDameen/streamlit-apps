import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Vehicle Safety Recalls", page_icon=":car:", layout="wide")

st.markdown("""
<style>
.badge-critical { background:#5a1a1a; color:#ff6666; padding:2px 8px; border-radius:4px; font-size:0.8rem; }
.badge-moderate { background:#3a3a1a; color:#ffcc66; padding:2px 8px; border-radius:4px; font-size:0.8rem; }
.badge-minor { background:#1a3a1a; color:#66ff66; padding:2px 8px; border-radius:4px; font-size:0.8rem; }
</style>
""", unsafe_allow_html=True)

st.title(":car: Vehicle Safety Recalls")
st.caption("NHTSA Recall Database")

@st.cache_data(ttl=3600)
def fetch_makes():
    r = requests.get("https://vpic.nhtsa.dot.gov/api/vehicles/getallmakes?format=json", timeout=10)
    r.raise_for_status()
    data = r.json()
    return sorted(set(m["Make_Name"] for m in data["Results"] if m["Make_Name"]))

@st.cache_data(ttl=3600)
def fetch_recalls(make, model, year):
    url = f"https://api.nhtsa.gov/recalls/recallsByVehicle?make={make}&model={model}&modelYear={year}"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        return r.json().get("results", [])
    return []

try:
    makes = fetch_makes()
except Exception as e:
    st.error(f"Failed to load makes: {e}")
    st.stop()

make = st.selectbox("Make", makes, index=makes.index("FORD") if "FORD" in makes else 0)
model = st.text_input("Model (e.g., F-150, Camry, Corolla)", value="F-150")
year = st.number_input("Model Year", min_value=1990, max_value=2026, value=2020)
search = st.button("Search Recalls", type="primary")

if search:
    with st.spinner("Searching NHTSA database..."):
        recalls = fetch_recalls(make, model, year)

    if not recalls:
        st.success(f"No recalls found for {year} {make} {model}")
    else:
        st.warning(f"{len(recalls)} recall(s) found for {year} {make} {model}")

        components = {}
        for r in recalls:
            comp = r.get("Component", "Unknown")
            components[comp] = components.get(comp, 0) + 1

        st.subheader("Recalls by Component")
        comp_df = pd.DataFrame([{"Component": c, "Count": n} for c, n in sorted(components.items(), key=lambda x: -x[1])])
        st.bar_chart(comp_df.set_index("Component"))

        st.subheader("Recall Details")
        for r in recalls:
            comp = r.get("Component", "Unknown")
            critical = any(k in comp.lower() for k in ["air bag", "airbag", "brake", "steering", "engine", "fuel", "fire"])
            badge = "badge-critical" if critical else ("badge-moderate" if "seat" in comp.lower() or "window" in comp.lower() else "badge-minor")
            label = "CRITICAL" if critical else ("MODERATE" if "seat" in comp.lower() else "MINOR")

            with st.expander(f"{r.get('NHTSACampaignNumber', 'N/A')} — {comp}"):
                st.markdown(f"<span class='{badge}'>{label}</span>", unsafe_allow_html=True)
                st.write(f"**Summary:** {r.get('Summary', 'N/A')}")
                st.write(f"**Date:** {r.get('RecallDate', 'N/A')}")
                st.write(f"**Consequence:** {r.get('Consequence', 'N/A')}")
                st.write(f"**Remedy:** {r.get('Remedy', 'N/A')}")
