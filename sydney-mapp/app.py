"""
Sydney Map — Beautiful maps from OpenStreetMap data.
"""

import copy
import re
from io import StringIO, BytesIO
from pathlib import Path

import streamlit as st

from prettymapp.geo import GeoCodingError, get_aoi
from prettymapp.osm import get_osm_geometries
from prettymapp.plotting import Plot
from prettymapp.settings import STYLES

# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sydney Map",
    page_icon="🌊",
    initial_sidebar_state="collapsed",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown(
    """<style>
/* ── Font & base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

html, body, .stApp {
    font-family: 'Inter', 'DM Sans', -apple-system, sans-serif;
}

h1 { font-family: 'Inter', sans-serif; font-weight: 800; letter-spacing: -0.5px; }
h2, h3 { font-family: 'Inter', sans-serif; font-weight: 600; }

/* ── Quick-pick buttons ── */
div[data-testid="column"] > div > button[data-testid="baseButton-secondary"] {
    border: none !important;
    border-radius: 14px !important;
    padding: 10px 6px !important;
    font-family: 'DM Sans', 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.3px !important;
    color: #FFFFFF !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    transition: all 0.2s ease !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.3 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
div[data-testid="column"] > div > button[data-testid="baseButton-secondary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.15) !important;
    opacity: 0.92 !important;
}
div[data-testid="column"] > div > button[data-testid="baseButton-secondary"]:active {
    transform: translateY(0) !important;
}

/* ── Main form button ── */
button[data-testid="baseButton-primary"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border-radius: 12px !important;
    padding: 8px 24px !important;
}

/* ── Expander headers ── */
.streamlit-expanderHeader {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}

/* ── Side spacing tweaks ── */
.block-container { padding-top: 1.5rem !important; }
.stDivider { margin: 0.8rem 0 !important; }

/* ── Gallery images ── */
.gallery-img {
    border-radius: 16px;
    width: 100%;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    transition: transform 0.2s ease;
    border: 2px solid #f0f0f0;
}
.gallery-img:hover {
    transform: scale(1.02);
    border-color: #4A90D9;
}
.gallery-caption {
    text-align: center;
    font-family: 'DM Sans', 'Inter', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    color: #555;
    margin-top: 6px;
}
</style>""",
    unsafe_allow_html=True,
)


# ── Sydney Quick-Pick Locations ──────────────────────────────────────────────

# Each spot gets a unique accent colour for its button
SPOT_COLORS = {
    "Sydney CBD": "#1E88E5",
    "Circular Quay": "#43A047",
    "Bondi Beach": "#FB8C00",
    "Barangaroo": "#8E24AA",
    "Coogee to Bondi": "#E53935",
    "Sydney Harbour": "#00ACC1",
    "Parramatta": "#F4511E",
    "Manly Beach": "#3949AB",
}

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
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-")


def _load_spot(name: str) -> None:
    spot = SYDNEY_SPOTS[name]
    st.session_state.update(copy.deepcopy(spot))
    st.session_state["lc_classes"] = list(_get_lc_colors(spot["style"]).keys())
    st.session_state.update(_get_lc_colors(spot["style"]))
    st.session_state["previous_style"] = spot["style"]
    st.session_state.pop("fig", None)
    st.session_state.pop("df", None)


# ── Init Session State ───────────────────────────────────────────────────────

if "lc_classes" not in st.session_state:
    _load_spot("Sydney CBD")


# ── UI Header ────────────────────────────────────────────────────────────────

st.markdown(
    """<div style="text-align: center; margin-bottom: 10px;">
        <h1 style="font-size: 2.4rem; background: linear-gradient(135deg, #1E88E5, #00ACC1, #43A047);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                   background-clip: text; margin-bottom: 0;">
        🌊 Sydney Map
        </h1>
        <p style="font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #888; margin-top: -4px;">
        Beautiful maps from OpenStreetMap data
        </p>
    </div>""",
    unsafe_allow_html=True,
)

# ── Gallery Preview ──────────────────────────────────────────────────────────

ASSETS = Path(__file__).parent / "assets"
gallery_images = [
    ("Sydney CBD", "sydney-cbd-nsw-australia.png"),
    ("Sydney Harbour", "sydney-harbour-nsw-australia.png"),
    ("Bondi Beach", "bondi-beach-nsw-australia.png"),
    ("Circular Quay", "Circular-Quay.png"),
]

with st.container():
    st.markdown(
        """<p style="font-family: 'DM Sans', sans-serif; font-size: 0.85rem;
                   font-weight: 600; color: #666; text-align: center; margin-bottom: 8px;">
        ⭐ Sample maps
        </p>""",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(gallery_images))
    for i, (label, filename) in enumerate(gallery_images):
        img_path = ASSETS / filename
        if img_path.exists():
            with cols[i]:
                st.image(str(img_path), use_container_width=True)
                st.markdown(
                    f"""<p class="gallery-caption">{label}</p>""",
                    unsafe_allow_html=True,
                )

# ── Quick-Pick Sydney Spots ──────────────────────────────────────────────────

st.markdown(
    """<p style="font-family: 'DM Sans', sans-serif; font-size: 0.95rem;
               font-weight: 700; color: #444; margin: 14px 0 4px 0;">
    📍 Quick pick
    </p>""",
    unsafe_allow_html=True,
)

spot_names = list(SYDNEY_SPOTS.keys())

# Generate per-row CSS for colored buttons
# Row 1: spots 0-3, Row 2: spots 4-7
btn_css_parts = []
for row_idx in range(2):
    row_id = f"qp-row-{row_idx}"
    for col_idx in range(4):
        name_idx = row_idx * 4 + col_idx
        color = SPOT_COLORS[spot_names[name_idx]]
        btn_css_parts.append(
            f"#{row_id} div[data-testid=\"column\"]:nth-of-type({col_idx+1}) "
            f"button[data-testid=\"baseButton-secondary\"] "
            f"{{ background: {color} !important; border: none !important; }}"
        )
st.markdown(
    f"<style>{' '.join(btn_css_parts)}</style>",
    unsafe_allow_html=True,
)

# Row 1: first 4 spots
st.markdown('<div id="qp-row-0">', unsafe_allow_html=True)
cols1 = st.columns(4)
for i in range(4):
    name = spot_names[i]
    with cols1[i]:
        if st.button(name, key=f"qp_{name}", use_container_width=True):
            _load_spot(name)
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# Row 2: last 4 spots
st.markdown('<div id="qp-row-1">', unsafe_allow_html=True)
cols2 = st.columns(4)
for i in range(4, 8):
    name = spot_names[i]
    with cols2[i - 4]:
        if st.button(name, key=f"qp_{name}", use_container_width=True):
            _load_spot(name)
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

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

        st.session_state["fig"] = fig
        st.session_state["df"] = df
        st.session_state["render_config"] = config
        st.session_state["safe_name"] = _slugify(address) if address.strip() else "sydney-map"

# ── Display Map & Exports ───────────────────────────────────────────────────

if "fig" in st.session_state:
    fig = st.session_state["fig"]
    df = st.session_state.get("df")
    safe_name = st.session_state.get("safe_name", "sydney-map")

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

# ── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    """<div style="text-align: center; font-size: 0.75rem; color: #aaa; line-height: 1.6;">
    <p>
        🌊 <strong>Sydney Map</strong> —
        Maps from <a href="https://www.openstreetmap.org" target="_blank" style="color: #4A90D9;">OpenStreetMap</a> data
    </p>
    <p>
        Built with Streamlit · Data © OSM contributors
    </p>
    </div>""",
    unsafe_allow_html=True,
)
