"""
NASA Astronomy Picture of the Day (APOD) Streamlit App
------------------------------------------------------
Browse, search, and save your favorite APOD images.
API: https://api.nasa.gov/planetary/apod
"""

import streamlit as st
import requests
from datetime import date, timedelta
import random as py_random
from typing import Optional, Dict, Any, List

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = "https://api.nasa.gov/planetary/apod"
DEFAULT_API_KEY = "DEMO_KEY"  # 30 req/h – get a free key at api.nasa.gov
MAX_DATE = date.today()
MIN_DATE = date(1995, 6, 16)  # APOD started

st.set_page_config(
    page_title="NASA APOD Explorer",
    page_icon="🌌",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dark space-themed CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
/* --- base dark theme --- */
.stApp {
    background: #0b0c10;
    color: #e0e0e0;
}
h1, h2, h3, h4, h5, h6 {
    color: #f0f0f0 !important;
    font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
}
/* serif for explanations */
.explanation-text {
    font-family: 'Palatino', 'Palatino Linotype', 'Georgia', serif;
    font-size: 1.05rem;
    line-height: 1.6;
    color: #cfcfcf;
}
/* sidebar favourites */
[data-testid="stSidebar"] {
    background: #11131a;
}
[data-testid="stSidebar"] * {
    color: #d0d0d0;
}
/* date input / buttons */
.stDateInput, .stButton button {
    border-radius: 6px !important;
}
.stButton button {
    background: #1f2a3a !important;
    border: 1px solid #3a4b5e !important;
    color: #e0e0e0 !important;
    transition: 0.2s;
}
.stButton button:hover {
    background: #2a3a4f !important;
    border-color: #6a8ab0 !important;
    color: white !important;
}
/* divider */
hr {
    border-color: #2a2e3a;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
def init_session() -> None:
    if "favorites" not in st.session_state:
        st.session_state.favorites = {}  # date_str -> dict
    if "show_hd" not in st.session_state:
        st.session_state.show_hd = True
    if "random_mode" not in st.session_state:
        st.session_state.random_mode = False


init_session()

# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Fetching APOD data…")
def fetch_apod(
    api_key: str = DEFAULT_API_KEY, apod_date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    params: Dict[str, str] = {"api_key": api_key}
    if apod_date:
        params["date"] = apod_date
    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_fav_key(data: dict) -> str:
    return data.get("date", "")


def toggle_favorite(data: dict) -> None:
    key = get_fav_key(data)
    if key in st.session_state.favorites:
        del st.session_state.favorites[key]
    else:
        st.session_state.favorites[key] = data


def random_date() -> date:
    """Return a random date between MIN_DATE and MAX_DATE."""
    delta = (MAX_DATE - MIN_DATE).days
    return MIN_DATE + timedelta(days=py_random.randint(0, delta))


# ---------------------------------------------------------------------------
# Sidebar – Favorites
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⭐ Favorites")
    if not st.session_state.favorites:
        st.caption("No favorites saved yet. Click ★ in the main panel.")
    else:
        for fav_date_str, fav_data in sorted(st.session_state.favorites.items()):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{fav_data.get('title', 'Untitled')}**  \n`{fav_date_str}`")
            with col2:
                if st.button("✕", key=f"rm_fav_{fav_date_str}", help="Remove favorite"):
                    del st.session_state.favorites[fav_date_str]
                    st.rerun()
            st.divider()

    st.markdown("---")
    st.markdown("**🔑 API Key**")
    api_key = st.text_input(
        "API Key",
        value=DEFAULT_API_KEY,
        type="password",
        help="DEMO_KEY allows 30 requests/hour. Get a free key at api.nasa.gov",
        label_visibility="collapsed",
    )

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------
st.title("🌌 Astronomy Picture of the Day")
st.caption("Brought to you by NASA's APOD API")

# --- Date picker + controls ---
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    selected_date = st.date_input(
        "Select date",
        value=date.today(),
        min_value=MIN_DATE,
        max_value=MAX_DATE,
        key="date_picker",
    )

with col2:
    st.markdown("####")
    if st.button("🎲 Random", use_container_width=True):
        rd = random_date()
        st.session_state.random_mode = True
        st.session_state.force_date = rd
        st.rerun()

with col3:
    st.markdown("####")
    hd_toggle = st.toggle("HD", value=st.session_state.show_hd, key="hd_toggle")
    st.session_state.show_hd = hd_toggle

# Determine the date to query
if st.session_state.get("random_mode") and "force_date" in st.session_state:
    query_date = st.session_state.force_date
    # Reset random mode after one use
    st.session_state.random_mode = False
else:
    query_date = selected_date

# Update the date_picker to reflect the random date
if "force_date" in st.session_state and st.session_state.get("random_mode_was", False):
    pass  # already handled above

date_str = query_date.strftime("%Y-%m-%d")

# --- Fetch ---
data = fetch_apod(api_key=api_key, apod_date=date_str)

if data is None:
    st.warning("Could not retrieve APOD data. Check your API key or try again later.")
    st.stop()

# Flag if we used a key/date mismatch
if data.get("date") and data["date"] != date_str:
    st.caption(f"*Note: closest available date is {data['date']}*")

# --- Display ---
media_type = data.get("media_type", "image")

# Image or Video
if media_type == "image":
    img_url = data.get("hdurl" if st.session_state.show_hd else "url") or data.get("url")
    if img_url:
        st.image(img_url, use_container_width=True)
    else:
        st.info("No image URL available for this date.")
elif media_type == "video":
    vid_url = data.get("url", "")
    st.markdown(
        f'<div style="text-align:center;"><iframe src="{vid_url}" '
        f'width="100%" height="480" frameborder="0" allowfullscreen></iframe></div>',
        unsafe_allow_html=True,
    )
else:
    st.info(f"Media type '{media_type}' is not directly supported.")

# --- Metadata ---
st.markdown(f"## {data.get('title', 'Untitled')}")
st.caption(
    f"📅 {data.get('date', '')}"
    + (f"  |  © {data.get('copyright', '').strip()}" if data.get("copyright") else "")
)

# Favorite button
fav_key = get_fav_key(data)
is_fav = fav_key in st.session_state.favorites
btn_label = "★ Unfavorite" if is_fav else "☆ Favorite"
if st.button(btn_label, key="fav_btn", use_container_width=True):
    toggle_favorite(data)
    st.rerun()

# Expandable explanation
with st.expander("📖 View Explanation", expanded=False):
    st.markdown(
        f'<div class="explanation-text">{data.get("explanation", "No explanation available.")}</div>',
        unsafe_allow_html=True,
    )

# --- Raw data expander for debugging ---
with st.expander("📦 Raw API Response", expanded=False):
    st.json(data)
