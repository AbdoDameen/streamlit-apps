import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Country Explorer", page_icon=":earth_asia:", layout="wide")

st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] { gap: 2rem; }
</style>
""", unsafe_allow_html=True)

st.title(":earth_asia: Country Explorer")

@st.cache_data(ttl=86400)
def fetch_countries():
    r = requests.get("https://restcountries.com/v3.1/all", timeout=15)
    r.raise_for_status()
    return r.json()

try:
    countries = fetch_countries()
except Exception as e:
    st.error(f"Failed: {e}")
    st.stop()

rows = []
for c in countries:
    currencies = c.get("currencies", {})
    curr_code = list(currencies.keys())[0] if currencies else ""
    rows.append({
        "name": c.get("name", {}).get("common", ""),
        "flag": c.get("flag", ""),
        "capital": ", ".join(c.get("capital", ["N/A"])),
        "region": c.get("region", ""),
        "subregion": c.get("subregion", ""),
        "population": c.get("population", 0),
        "area": c.get("area", 0),
        "density": round(c.get("population", 0) / max(c.get("area", 1), 1), 2),
        "currency": curr_code,
        "languages": ", ".join(c.get("languages", {}).values()),
        "lang_count": len(c.get("languages", {})),
        "independent": c.get("independent", False),
        "un_member": c.get("unMember", False),
    })

df = pd.DataFrame(rows)

tab1, tab2 = st.tabs(["Browse", "Visualize (pygwalker)"])

with tab1:
    regions = ["All"] + sorted(df["region"].dropna().unique())
    region = st.selectbox("Region", regions)
    search = st.text_input("Search country")
    mask = pd.Series([True] * len(df))
    if region != "All":
        mask &= df["region"] == region
    if search:
        mask &= df["name"].str.lower().str.contains(search.lower())
    filtered = df[mask]
    st.write(f"Showing {len(filtered)} countries")
    for _, r in filtered.sort_values("population", ascending=False).iterrows():
        c1, c2, c3 = st.columns([1, 3, 2])
        with c1:
            st.write(f"# {r['flag']}")
        with c2:
            st.markdown(f"**{r['name']}**  \nCapital: {r['capital']} | {r['region']}")
        with c3:
            st.write(f"Population: {r['population']:,}")
            st.write(f"Area: {r['area']:,.0f} km\u00b2")
        st.divider()

with tab2:
    st.subheader("Interactive Data Explorer")
    st.caption("Drag fields to rows/columns/values to build your own analysis")
    viz_df = df[["name","region","subregion","population","area","density","currency","lang_count","independent","un_member"]]
    try:
        import pygwalker as pyg
        pyg.walk(viz_df, spec={"specVersion": 0}, env="Streamlit")
    except Exception as e:
        st.warning(f"pygwalker unavailable: {e}")
        st.dataframe(viz_df, use_container_width=True)
