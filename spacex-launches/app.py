import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="SpaceX Launches", page_icon=":rocket:", layout="wide")

st.markdown("""
<style>
.mcard { background:#141428; border:1px solid #2a2a5a; border-radius:10px; padding:1.2rem; text-align:center; }
.mcard .lbl { color:#8888cc; font-size:0.8rem; text-transform:uppercase; }
.mcard .val { color:#00d4aa; font-size:2rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.title(":rocket: SpaceX Launch History")

@st.cache_data(ttl=3600)
def fetch_launches():
    all_l = []
    page = 1
    while True:
        r = requests.get(f"https://api.spacexdata.com/v5/launches?limit=50&offset={(page-1)*50}", timeout=10)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        all_l.extend(batch)
        page += 1
        if len(batch) < 50:
            break
    return all_l

try:
    launches = fetch_launches()
except Exception as e:
    st.error(f"Failed: {e}")
    st.stop()

rows = []
for l in launches:
    payload = l.get("payloads") or []
    p_mass = sum((p.get("mass_kg") or 0) for p in payload if isinstance(p, dict)) if isinstance(payload, list) else 0
    rows.append({
        "name": l["name"],
        "date": l["date_utc"][:10],
        "year": l["date_utc"][:4],
        "success": l["success"],
        "rocket": l["rocket"],
        "payload_kg": p_mass,
        "crew": len(l.get("crew") or []),
        "upcoming": l.get("upcoming", False),
        "details": (l.get("details") or "") or "",
        "patch": l.get("links", {}).get("patch", {}).get("small") if l.get("links") else None,
        "webcast": l.get("links", {}).get("webcast") if l.get("links") else None,
        "article": l.get("links", {}).get("article") if l.get("links") else None,
    })

df = pd.DataFrame(rows)

st.sidebar.header("Filters")
years = sorted(df["year"].unique())
yr = st.sidebar.select_slider("Year Range", options=years, value=(years[0], years[-1]))
status = st.sidebar.multiselect("Status", ["All", "Success", "Failed", "Upcoming"], default=["All"])

mask = (df["year"] >= yr[0]) & (df["year"] <= yr[1])
if "All" not in status:
    cond = pd.Series([False]*len(df))
    if "Success" in status: cond |= (df["success"] == True) & ~df["upcoming"]
    if "Failed" in status:  cond |= (df["success"] == False)
    if "Upcoming" in status: cond |= df["upcoming"]
    mask &= cond

df_f = df[mask]
total = len(df_f)
sc = int(df_f["success"].sum())
sr = round(sc / max(total - int(df_f["upcoming"].sum()), 1) * 100, 1)
up = int(df_f["upcoming"].sum())

k1, k2, k3, k4 = st.columns(4)
with k1: st.markdown(f"<div class='mcard'><div class='lbl'>Launches</div><div class='val'>{total}</div></div>", unsafe_allow_html=True)
with k2: st.markdown(f"<div class='mcard'><div class='lbl'>Success Rate</div><div class='val'>{sr}%</div></div>", unsafe_allow_html=True)
with k3: st.markdown(f"<div class='mcard'><div class='lbl'>Upcoming</div><div class='val'>{up}</div></div>", unsafe_allow_html=True)
with k4: st.markdown(f"<div class='mcard'><div class='lbl'>Crew</div><div class='val'>{int(df_f['crew'].sum())}</div></div>", unsafe_allow_html=True)

yearly = df_f.groupby("year").size().reset_index(name="count")
st.subheader("Launches per Year")
st.bar_chart(yearly.set_index("year"))

st.subheader(f"Launches ({len(df_f)} total)")
for _, r in df_f.sort_values("date", ascending=False).iterrows():
    icon = chr(9989) if r["success"] == True else (chr(9203) if r["upcoming"] else chr(10060))
    with st.expander(f"{icon} {r['name']} — {r['date']}"):
        c1, c2 = st.columns([1, 3])
        with c1:
            if r["patch"]:
                st.image(r["patch"], width=120)
        with c2:
            st.write(f"**Rocket:** {r['rocket']}")
            st.write(f"**Payload:** {r['payload_kg']:,.0f} kg" if r["payload_kg"] > 0 else "**Payload:** N/A")
            if r["details"]: st.write(f"**Details:** {r['details']}")
            if r["webcast"]: st.markdown(f"[Watch Webcast]({r['webcast']})")
            if r["article"]: st.markdown(f"[Read Article]({r['article']})")
