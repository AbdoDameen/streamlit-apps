"""
Sydneymapp — Beautiful Sydney maps from OpenStreetMap data.
Fork of prettymapp by @chrieke.
"""

import copy
import re
from io import StringIO, BytesIO

import streamlit as st

from prettymapp.geo import GeoCodingError, get_aoi
from prettymapp.osm import get_osm_geometries
from prettymapp.plotting import Plot
from prettymapp.settings import STYLES

# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sydneymapp",
    page_icon="🌊",
    initial_sidebar_state="collapsed",
    layout="centered",
)

# ── Sydney Quick-Pick Locations ──────────────────────────────────────────────

SYDNEY_SPOTS = {
    "Sydney CBD": {
        "address": "Sydney CBD, NSW, Australia",
        "custom_title": "Sydney CBD",
        "radius": 1200,
        "style": "Peach",
        "shape": "circle",
        "contour_width": 2,
        "contour_color": "#2F3737",
        "name_on": True,
        "font_size": 30,
        "font_color": "#2F3737",
        "text_x": 0,
        "text_y": -55,
        "text_rotation": 0,
        "bg_shape": "circle",
        "bg_buffer": 6,
        "bg_color": "#F2F4CB",
    },
    "Circular Quay": {
        "address": "Circular Quay, Sydney NSW, Australia",
        "custom_title": "Circular Quay",
        "radius": 500,
        "style": "Peach",
        "shape": "circle",
        "contour_width": 2,
        "contour_color": "#2F3737",
        "name_on": True,
        "font_size": 24,
        "font_color": "#2F3737",
        "text_x": 0,
        "text_y": -25,
        "text_rotation": 0,
        "bg_shape": "circle",
        "bg_buffer": 4,
        "bg_color": "#F2F4CB",
    },
    "Bondi Beach": {
        "address": "Bondi Beach NSW, Australia",
        "custom_title": "Bondi Beach",
        "radius": 600,
        "style": "Auburn",
        "shape": "circle",
        "contour_width": 2,
        "contour_color": "#2F3737",
        "name_on": True,
        "font_size": 26,
        "font_color": "#2F3737",
        "text_x": 0,
        "text_y": -30,
        "text_rotation": 0,
        "bg_shape": "circle",
        "bg_buffer": 4,
        "bg_color": "#F9EFDC",
    },
    "Barangaroo": {
        "address": "Barangaroo NSW, Australia",
        "custom_title": "Barangaroo",
        "radius": 400,
        "style": "Flannel",
        "shape": "circle",
        "contour_width": 2,
        "contour_color": "#2F3737",
        "name_on": True,
        "font_size": 24,
        "font_color": "#2F3737",
        "text_x": 0,
        "text_y": -25,
        "text_rotation": 0,
        "bg_shape": "rectangle",
        "bg_buffer": 4,
        "bg_color": "#EDEFDA",
    },
    "Coogee to Bondi": {
        "address": "Coogee Beach NSW, Australia",
        "custom_title": "Coogee to Bondi",
        "radius": 900,
        "style": "Citrus",
        "shape": "rectangle",
        "contour_width": 3,
        "contour_color": "#FFFFFF",
        "name_on": True,
        "font_size": 28,
        "font_color": "#FFFFFF",
        "text_x": -35,
        "text_y": 35,
        "text_rotation": 0,
        "bg_shape": None,
        "bg_buffer": 5,
        "bg_color": "#000000",
    },
    "Sydney Harbour": {
        "address": "Sydney Harbour NSW, Australia",
        "custom_title": "Sydney Harbour",
        "radius": 1500,
        "style": "Auburn",
        "shape": "rectangle",
        "contour_width": 0,
        "contour_color": "#2F3737",
        "name_on": True,
        "font_size": 32,
        "font_color": "#2F3737",
        "text_x": 40,
        "text_y": 40,
        "text_rotation": 0,
        "bg_shape": "rectangle",
        "bg_buffer": 8,
        "bg_color": "#F9EFDC",
    },
    "Parramatta": {
        "address": "Parramatta NSW, Australia",
        "custom_title": "Parramatta",
        "radius": 700,
        "style": "Flannel",
        "shape": "rectangle",
        "contour_width": 1,
        "contour_color": "#2F3737",
        "name_on": True,
        "font_size": 26,
        "font_color": "#2F3737",
        "text_x": 0,
        "text_y": -30,
        "text_rotation": 0,
        "bg_shape": "rectangle",
        "bg_buffer": 4,
        "bg_color": "#EDEFDA",
    },
    "Manly Beach": {
        "address": "Manly Beach NSW, Australia",
        "custom_title": "Manly Beach",
        "radius": 550,
        "style": "Peach",
        "shape": "circle",
        "contour_width": 2,
        "contour_color": "#2F3737",
        "name_on": True,
        "font_size": 24,
        "font_color": "#2F3737",
        "text_x": 0,
        "text_y": -25,
        "text_rotation": 0,
        "bg_shape": "circle",
        "bg_buffer": 4,
        "bg_color": "#F2F4CB",
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_lc_colors(style_name: str) -> dict:
    """Return {landcover_class: colour} for a given style."""
    cols = {}
    for lc_class, class_style in STYLES[style_name].items():
        colors = class_style.get("cmap", class_style.get("fc"))
        if isinstance(colors, list):
            for idx, c in enumerate(colors):
                cols[f"{lc_class}_{idx}"] = c
        else:
            cols[lc_class] = colors
    return cols


def _slugify(value: str) -> str:
    """Normalise a string into a safe filename slug."""
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-")


def _load_spot(name: str) -> None:
    """Load a Sydney spot into session state."""
    spot = SYDNEY_SPOTS[name]
    st.session_state.update(copy.deepcopy(spot))
    st.session_state["lc_classes"] = list(_get_lc_colors(spot["style"]).keys())
    st.session_state.update(_get_lc_colors(spot["style"]))
    st.session_state["previous_style"] = spot["style"]
    # Clear previous figure so a new one gets generated
    st.session_state.pop("fig", None)
    st.session_state.pop("df", None)


# ── Init Session State ───────────────────────────────────────────────────────

if "lc_classes" not in st.session_state:
    _load_spot("Sydney CBD")

# ── UI Header ────────────────────────────────────────────────────────────────

st.markdown(
    """<div style="text-align: center; margin-bottom: -12px;">
        <h1>🌊 Sydneymapp</h1>
    </div>""",
    unsafe_allow_html=True,
)

st.markdown(
    """<p style="text-align: center; font-size: 0.95rem; color: #888;">
    Beautiful Sydney maps from OpenStreetMap data ·
    <a href="https://github.com/chrieke/prettymapp" target="_blank" style="color: #4A90D9;">
        Fork of prettymapp
    </a>
    </p>""",
    unsafe_allow_html=True,
)

# ── Quick-Pick Sydney Spots ──────────────────────────────────────────────────

st.markdown("### 📍 Quick-pick a Sydney spot")
spot_names = list(SYDNEY_SPOTS.keys())
spot_cols = st.columns(len(spot_names))
for i, name in enumerate(spot_names):
    with spot_cols[i]:
        if st.button(name, use_container_width=True):
            _load_spot(name)
            st.rerun()

st.divider()

# ── Main Form ────────────────────────────────────────────────────────────────

form = st.form(key="form_settings")
col1, col2, col3 = form.columns([3, 1, 1])

address = col1.text_input(
    "Location address (anywhere in the world)",
    key="address",
    placeholder="e.g. Circular Quay, Sydney",
)

radius = col2.slider("Radius (metres)", 100, 1500, key="radius")

style: str = col3.selectbox(
    "Colour theme",
    options=list(STYLES.keys()),
    key="style",
)

# ── Style Customisation ──────────────────────────────────────────────────────

expander = form.expander("🎨 Customise map style")
col1s, col2s, _, col3s = expander.columns([2, 2, 0.1, 1])

shape = col1s.radio("Map shape", options=["circle", "rectangle"], key="shape")

bg_shape = col1s.radio(
    "Background shape", options=["rectangle", "circle", None], key="bg_shape"
)

bg_color = col1s.color_picker("Background colour", key="bg_color")

bg_buffer = col1s.slider(
    "Background size",
    min_value=0,
    max_value=50,
    help="How much the background extends beyond the map edge.",
    key="bg_buffer",
)

col1s.markdown("---")

contour_color = col1s.color_picker("Map contour colour", key="contour_color")

contour_width = col1s.slider(
    "Map contour width",
    0,
    30,
    help="Thickness of the contour line around the map.",
    key="contour_width",
)

# ── Title Settings ───────────────────────────────────────────────────────────

name_on = col2s.checkbox(
    "Display title",
    help="Adds the address (or custom title) to the map.",
    key="name_on",
)

custom_title = col2s.text_input(
    "Custom title (optional, max 30 chars)", max_chars=30, key="custom_title"
)

font_size = col2s.slider("Title font size", 1, 50, key="font_size")
font_color = col2s.color_picker("Title font colour", key="font_color")

text_x = col2s.slider("Title left/right", -100, 100, key="text_x")
text_y = col2s.slider("Title top/bottom", -100, 100, key="text_y")
text_rotation = col2s.slider("Title rotation", -90, 90, key="text_rotation")

# ── Colour Pickers per Land-Use Class ───────────────────────────────────────

# Update colour pickers when style changes
if style != st.session_state.get("previous_style", style):
    st.session_state["lc_classes"] = list(_get_lc_colors(style).keys())
    st.session_state.update(_get_lc_colors(style))

draw_settings = copy.deepcopy(STYLES[style])
for lc_class in st.session_state.get("lc_classes", []):
    picked_color = col3s.color_picker(lc_class, key=lc_class)
    if "_" in lc_class:
        base, idx = lc_class.rsplit("_", 1)
        draw_settings[base]["cmap"][int(idx)] = picked_color
    else:
        draw_settings[lc_class]["fc"] = picked_color

submitted = form.form_submit_button(label="✨ Generate map", type="primary")
st.session_state["previous_style"] = style

# ── Generate Map ─────────────────────────────────────────────────────────────

if submitted:
    with st.spinner("🔄 Downloading OpenStreetMap data and rendering map..."):
        rectangular = shape != "circle"
        try:
            aoi = get_aoi(address=address, radius=radius, rectangular=rectangular)
        except GeoCodingError as e:
            st.error(f"Geocoding error: {e}")
            st.stop()

        df = get_osm_geometries(aoi=aoi)

        config = {
            "aoi_bounds": aoi.bounds,
            "draw_settings": draw_settings,
            "name_on": name_on,
            "name": address if custom_title == "" else custom_title,
            "font_size": font_size,
            "font_color": font_color,
            "text_x": text_x,
            "text_y": text_y,
            "text_rotation": text_rotation,
            "shape": shape,
            "contour_width": contour_width,
            "contour_color": contour_color,
            "bg_shape": bg_shape,
            "bg_buffer": bg_buffer,
            "bg_color": bg_color,
        }

        fig = Plot(df, **config).plot_all()

        # Store for export sections
        st.session_state["fig"] = fig
        st.session_state["df"] = df
        st.session_state["render_config"] = config
        st.session_state["safe_name"] = _slugify(address) if address.strip() else "sydneymapp"

# ── Display Map & Exports ───────────────────────────────────────────────────

if "fig" in st.session_state:
    fig = st.session_state["fig"]
    df = st.session_state.get("df")
    safe_name = st.session_state.get("safe_name", "sydneymapp")

    st.pyplot(
        fig,
        pad_inches=0,
        bbox_inches="tight",
        transparent=True,
        dpi=300,
    )

    # ── Export ───────────────────────────────────────────────────────────
    with st.expander("⬇️ Export map", expanded=True):
        col_png, col_svg = st.columns(2)

        with col_png:
            buf = BytesIO()
            fig.savefig(
                buf,
                format="png",
                dpi=300,
                pad_inches=0,
                bbox_inches="tight",
                transparent=True,
            )
            buf.seek(0)
            st.download_button(
                label="📷 Download PNG (300 dpi)",
                data=buf,
                file_name=f"{safe_name}.png",
                mime="image/png",
                key="dl_png",
                use_container_width=True,
            )

        with col_svg:
            svg_buf = StringIO()
            fig.savefig(
                svg_buf,
                format="svg",
                pad_inches=0,
                bbox_inches="tight",
                transparent=True,
            )
            svg_buf.seek(0)
            st.download_button(
                label="✏️ Download SVG (lossless)",
                data=svg_buf.getvalue(),
                file_name=f"{safe_name}.svg",
                mime="image/svg+xml",
                key="dl_svg",
                use_container_width=True,
            )

    # ── GeoJSON Export ───────────────────────────────────────────────────
    if df is not None:
        with st.expander("🗺️ Export geometries as GeoJSON"):
            st.info(f"{len(df)} OSM geometries loaded")
            st.download_button(
                label="Download GeoJSON",
                data=df.to_json().encode("utf-8"),
                file_name=f"{safe_name}.geojson",
                mime="application/geo+json",
                key="dl_geojson",
            )

st.markdown("---")

# ── Footer / Attribution ─────────────────────────────────────────────────────

st.markdown(
    """<div style="text-align: center; font-size: 0.8rem; color: #999; line-height: 1.7;">
    <p>
        🌊 <strong>Sydneymapp</strong> —
        Beautiful maps generated from
        <a href="https://www.openstreetmap.org" target="_blank" style="color: #4A90D9;">OpenStreetMap</a> data
    </p>
    <p>
        ⚠️ <strong>Disclaimer:</strong> This project is a <b>fork</b> of the excellent
        <a href="https://github.com/chrieke/prettymapp" target="_blank" style="color: #4A90D9;">prettymapp</a>
        by <a href="https://github.com/chrieke" target="_blank" style="color: #4A90D9;">@chrieke</a>.
        All core rendering logic, colour themes, and OSM geometry fetching come from the original project.
        This fork curates Sydney-specific locations as the primary use case.
    </p>
    <p>
        🌐 Works with <i>any</i> address worldwide — not just Sydney.
    </p>
    <p style="font-size: 0.75rem; margin-top: 8px;">
        © 2025 · Built with Streamlit · Data © OpenStreetMap contributors
    </p>
    </div>""",
    unsafe_allow_html=True,
)
