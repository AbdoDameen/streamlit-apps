import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="AUD Currency Tracker", page_icon=":dollar:", layout="wide")

st.markdown("""
<style>
.rcard { background:#0a1a0a; border:1px solid #1a3a1a; border-radius:12px; padding:1rem; text-align:center; }
.rcard .code { color:#7ec87e; font-size:1.1rem; font-weight:600; }
.rcard .rate { color:white; font-size:1.6rem; font-weight:700; }
.rcard .name { color:#5a8a5a; font-size:0.75rem; }
</style>
""", unsafe_allow_html=True)

st.title("AUD Exchange Rate Tracker")
st.caption("Live rates against major world currencies")

MAJOR = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound", "JPY": "Japanese Yen",
    "NZD": "NZ Dollar", "CNY": "Chinese Yuan", "SGD": "Singapore Dollar",
    "INR": "Indian Rupee", "KRW": "S. Korean Won", "CHF": "Swiss Franc",
    "CAD": "Canadian Dollar", "HKD": "HK Dollar", "MYR": "Malaysian Ringgit",
    "THB": "Thai Baht", "IDR": "Indonesian Rupiah", "PHP": "Philippine Peso"
}

@st.cache_data(ttl=600)
def fetch_rates():
    r = requests.get("https://latest.currency-api.pages.dev/v1/currencies/aud.json", timeout=10)
    r.raise_for_status()
    return r.json()["aud"]

@st.cache_data(ttl=3600)
def fetch_historical(date_str):
    try:
        r = requests.get(f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/aud.json", timeout=10)
        if r.status_code == 200:
            return r.json()["aud"]
    except:
        pass
    return None

try:
    aud = fetch_rates()
except Exception as e:
    st.error(f"Failed: {e}")
    st.stop()

st.subheader("Live Rates: 1 AUD =")
cols = st.columns(4)
for i, (code, name) in enumerate(MAJOR.items()):
    rate = aud.get(code.lower(), 0)
    with cols[i % 4]:
        st.markdown(f"<div class='rcard'><div class='code'>{code}</div><div class='rate'>{rate:,.4f}</div><div class='name'>{name}</div></div>", unsafe_allow_html=True)

st.subheader("Currency Converter")
ca, cb, cc = st.columns([1, 0.3, 1])
with ca:
    amount = st.number_input("Amount (AUD)", min_value=0.01, value=100.0, step=10.0)
with cb:
    st.write("")
    st.write("")
    st.write(":arrow_right:")
with cc:
    target = st.selectbox("Convert to", list(MAJOR.keys()), index=0)
rate = aud.get(target.lower(), 1)
st.metric("Result", f"{amount * rate:,.2f} {target}")

tab1, tab2 = st.tabs(["Rate Table", "Historical + Visualize"])

with tab1:
    df = pd.DataFrame([
        {"Currency": name, "Code": c, "Rate (1 AUD)": aud.get(c.lower(), 0),
         "1 Unit = AUD": round(1 / max(aud.get(c.lower(), 0.0001), 0.0001), 4)}
        for c, name in MAJOR.items()
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Historical Trends")
    months = st.slider("Months of history", 1, 12, 6)
    compare = st.multiselect("Currencies", list(MAJOR.keys()), default=["USD", "EUR", "GBP", "JPY"])
    if compare:
        with st.spinner("Fetching historical data..."):
            hist = []
            for m in range(months):
                d = datetime.now() - timedelta(days=30 * m)
                ds = d.strftime("%Y.%-m.%-d")
                h = fetch_historical(ds)
                if h:
                    row = {"date": d.strftime("%Y-%m-%d")}
                    for c in compare:
                        val = h.get(c.lower())
                        if val:
                            row[c] = val
                    hist.append(row)
            if hist:
                dfh = pd.DataFrame(hist).sort_values("date")
                st.line_chart(dfh.set_index("date"))
                try:
                    import pygwalker as pyg
                    pyg.walk(dfh, env="Streamlit")
                except Exception as e:
                    st.warning(f"pygwalker: {e}")
