import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="World Happiness Index", page_icon=":smiley:", layout="wide")

st.title(":smiley: World Happiness & Well-Being")
st.caption("Key well-being indicators from the World Bank")

INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "GDP per Capita (PPP)",
    "SP.DYN.LE00.IN": "Life Expectancy (years)",
    "SE.ADT.LITR.ZS": "Literacy Rate (%)",
    "SL.UEM.TOTL.ZS": "Unemployment Rate (%)",
    "IT.NET.USER.ZS": "Internet Users (% pop)",
    "EN.ATM.CO2E.PC": "CO2 Emissions per Capita (t)",
    "SH.XPD.CHEX.GD.ZS": "Health Expenditure (% GDP)",
    "SE.PRM.ENRR": "Primary Enrollment Rate (%)",
}

@st.cache_data(ttl=86400)
def fetch_indicator(code):
    r = requests.get(f"http://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=2000", timeout=15)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=86400)
def fetch_countries():
    r = requests.get("http://api.worldbank.org/v2/country?format=json&per_page=300", timeout=15)
    r.raise_for_status()
    return r.json()

try:
    meta = fetch_countries()
except Exception as e:
    st.error(f"Failed: {e}")
    st.stop()

countries = {}
for c in meta[1]:
    countries[c["id"]] = {"name": c["name"], "region": c.get("region", {}).get("value", "")}

indicator = st.selectbox("Select Indicator", list(INDICATORS.values()))
ind_code = {v: k for k, v in INDICATORS.items()}[indicator]

with st.spinner(f"Fetching {indicator}..."):
    data = fetch_indicator(ind_code)

rows = []
for entry in data[1]:
    if entry["value"] is not None:
        cc = entry["countryiso3code"]
        info = countries.get(cc, {"name": entry["country"]["value"], "region": ""})
        rows.append({
            "country": info["name"],
            "code": cc,
            "region": info["region"],
            "year": int(entry["date"]),
            "value": entry["value"],
        })

df = pd.DataFrame(rows)
years = sorted(df["year"].unique())
yr = st.slider("Year", min(years), max(years), max(years))

df_yr = df[df["year"] == yr].dropna()
top = df_yr.sort_values("value", ascending=False).head(15)
bottom = df_yr.sort_values("value", ascending=True).head(15)

k1, k2, k3 = st.columns(3)
with k1: st.metric("Countries Reporting", len(df_yr))
with k2: st.metric("Global Average", f"{df_yr['value'].mean():.2f}")
with k3: st.metric("Highest", f"{top.iloc[0]['country']}: {top.iloc[0]['value']:.2f}" if not top.empty else "N/A")

c1, c2 = st.columns(2)
with c1:
    st.subheader(f"Top 15 ({yr})")
    st.bar_chart(top.set_index("country")["value"])
with c2:
    st.subheader(f"Bottom 15 ({yr})")
    st.bar_chart(bottom.set_index("country")["value"])

st.subheader("Country Trends")
countries_list = st.multiselect("Select countries", sorted(df["country"].unique()), default=["Australia", "United States", "Japan", "Norway", "India"])
if countries_list:
    trend = df[df["country"].isin(countries_list)].pivot_table(index="year", columns="country", values="value")
    st.line_chart(trend)

st.dataframe(df_yr.sort_values("value", ascending=False).head(50), use_container_width=True, hide_index=True)
