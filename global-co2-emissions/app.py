import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Global CO2 Emissions", page_icon=":factory:", layout="wide")

st.title(":factory: Global CO2 Emissions")
st.caption("Data from World Bank API")

@st.cache_data(ttl=86400)
def fetch_co2():
    r = requests.get("http://api.worldbank.org/v2/country/all/indicator/EN.ATM.CO2E.KT?format=json&per_page=5000", timeout=15)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=86400)
def fetch_country_meta():
    r = requests.get("http://api.worldbank.org/v2/country?format=json&per_page=300", timeout=15)
    r.raise_for_status()
    return r.json()

try:
    data = fetch_co2()
    meta = fetch_country_meta()
except Exception as e:
    st.error(f"Failed: {e}")
    st.stop()

country_map = {}
for c in meta[1]:
    country_map[c["id"]] = {"name": c["name"], "region": c.get("region", {}).get("value", ""), "income": c.get("incomeLevel", {}).get("value", "")}

rows = []
for entry in data[1]:
    if entry["value"] is not None:
        cc = entry["countryiso3code"]
        info = country_map.get(cc, {"name": entry["country"]["value"], "region": "", "income": ""})
        rows.append({
            "country": info["name"],
            "code": cc,
            "year": int(entry["date"]),
            "co2_kt": entry["value"],
            "region": info["region"],
            "income": info["income"],
        })

df = pd.DataFrame(rows)
years = sorted(df["year"].unique())
yr = st.slider("Year", min_value=min(years), max_value=max(years), value=max(years))

df_yr = df[df["year"] == yr]
top20 = df_yr.sort_values("co2_kt", ascending=False).head(20)
total = df_yr["co2_kt"].sum()
top_country = top20.iloc[0]["country"] if not top20.empty else "N/A"
n_countries = len(df_yr)

k1, k2, k3 = st.columns(3)
with k1: st.metric("Total Emissions (kt)", f"{total:,.0f}")
with k2: st.metric("Largest Emitter", f"{top_country} ({top20.iloc[0]['co2_kt']:,.0f} kt)" if not top20.empty else "N/A")
with k3: st.metric("Countries Reporting", n_countries)

st.subheader(f"Top 20 CO2 Emitters ({yr})")
st.bar_chart(top20.set_index("country")["co2_kt"])

st.subheader("Country Comparison")
countries = st.multiselect("Select countries to compare", sorted(df["country"].unique()), default=["United States", "China", "India", "Australia"])
if countries:
    comp = df[df["country"].isin(countries)].pivot_table(index="year", columns="country", values="co2_kt")
    st.line_chart(comp)

with st.expander("pygwalker: Explore the full dataset"):
    try:
        import pygwalker as pyg
        viz = df[df["year"] >= 2000].copy()
        pyg.walk(viz, env="Streamlit")
    except Exception as e:
        st.warning(f"pygwalker: {e}")
        st.dataframe(df[df["year"] >= 2000].head(100), use_container_width=True)
