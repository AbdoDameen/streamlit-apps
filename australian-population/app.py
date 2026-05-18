import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Australian Population", page_icon=":flag-australia:", layout="wide")

st.title(":flag-au: Australian Population & Demographics")
st.caption("Data from World Bank API")

INDICATORS = {
    "SP.POP.TOTL": "Total Population",
    "SP.POP.GROW": "Population Growth (annual %)",
    "SP.DYN.CBRT.IN": "Birth Rate (per 1000)",
    "SP.DYN.CDRT.IN": "Death Rate (per 1000)",
    "SP.DYN.LE00.IN": "Life Expectancy (years)",
    "SP.DYN.TFRT.IN": "Fertility Rate (births/woman)",
    "SP.URB.TOTL.IN.ZS": "Urban Population (%)",
    "SP.POP.DPND": "Dependency Ratio (%)",
    "SP.POP.65UP.TO.ZS": "Population 65+ (%)",
    "SP.POP.1564.TO.ZS": "Working Age Population (%)",
    "SM.POP.NETM": "Net Migration",
}

SELECTED_INDICATORS = ["SP.POP.TOTL", "SP.POP.GROW", "SP.DYN.LE00.IN", "SP.URB.TOTL.IN.ZS", "SP.POP.65UP.TO.ZS", "SP.DYN.TFRT.IN"]

@st.cache_data(ttl=86400)
def fetch_au_data(indicator):
    r = requests.get(f"http://api.worldbank.org/v2/country/AU/indicator/{indicator}?format=json&per_page=100", timeout=10)
    r.raise_for_status()
    return r.json()

all_data = {}
errors = []
for code in INDICATORS:
    try:
        data = fetch_au_data(code)
        if data and len(data) > 1:
            rows = []
            for entry in data[1]:
                if entry["value"] is not None:
                    rows.append({"year": int(entry["date"]), "value": entry["value"]})
            all_data[code] = pd.DataFrame(rows).sort_values("year")
    except Exception as e:
        errors.append(f"{code}: {e}")

st.subheader("Key Indicators Over Time")
cols = st.columns(3)
for i, code in enumerate(SELECTED_INDICATORS[:3]):
    with cols[i]:
        if code in all_data and not all_data[code].empty:
            latest = all_data[code].iloc[-1]
            label = INDICATORS[code]
            st.metric(label, f"{latest['value']:,.2f}" if code == "SP.POP.TOTL" else f"{latest['value']:.2f}", f"Year {latest['year']}")

cols2 = st.columns(3)
for i, code in enumerate(SELECTED_INDICATORS[3:6]):
    with cols2[i]:
        if code in all_data and not all_data[code].empty:
            latest = all_data[code].iloc[-1]
            st.metric(INDICATORS[code], f"{latest['value']:.2f}", f"Year {latest['year']}")

st.subheader("Population Over Time")
if "SP.POP.TOTL" in all_data:
    pop_df = all_data["SP.POP.TOTL"]
    pop_df["population_m"] = pop_df["value"] / 1_000_000
    st.line_chart(pop_df.set_index("year")["population_m"])
    st.caption("Population in millions")

st.subheader("Explore All Indicators")
ind = st.selectbox("Select indicator to visualize", list(INDICATORS.values()))
code = {v: k for k, v in INDICATORS.items()}[ind]
if code in all_data:
    df = all_data[code]
    st.line_chart(df.set_index("year")["value"])
    st.dataframe(df.rename(columns={"value": ind}), use_container_width=True, hide_index=True)

with st.expander("Compare Multiple Indicators"):
    selected = st.multiselect("Select indicators to compare", list(INDICATORS.values()), default=["Population Growth (annual %)", "Life Expectancy (years)"])
    if selected:
        combined = None
        codes = [{v: k for k, v in INDICATORS.items()}[s] for s in selected]
        for c in codes:
            if c in all_data:
                s = all_data[c][["year", "value"]].rename(columns={"value": INDICATORS[c]})
                if combined is None:
                    combined = s
                else:
                    combined = combined.merge(s, on="year", how="outer")
        if combined is not None:
            st.line_chart(combined.set_index("year"))

if errors:
    with st.expander("API Notes"):
        for e in errors:
            st.caption(e)
