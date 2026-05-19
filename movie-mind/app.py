"""
Movie Mind — Multi-modal vector movie recommender.
Hybrid: semantic search + TF-IDF latent + genre/numerical features + ensemble scoring.
"""
import json, pickle, re
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

BASE = Path(__file__).parent
INDEX_DIR = BASE / "index"
DATA = BASE / "data"

st.set_page_config(page_title="Movie Mind", page_icon="🎬", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html,body,.stApp{font-family:'Inter',sans-serif;background:#0a0a1a;color:#e0e0e0}
h1{font-family:'Inter',sans-serif;font-weight:800;letter-spacing:-0.5px}
.mc{background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px;padding:16px 20px;margin:8px 0;border:1px solid #2a2a4a;transition:all .2s}
.mc:hover{border-color:#e94560;transform:translateY(-2px)}
.mt{color:#e94560;font-weight:700;font-size:1.05rem}
.mm{color:#8899aa;font-size:.82rem}
.mg{display:inline-block;background:#2a2a4a;padding:1px 10px;border-radius:10px;font-size:.72rem;color:#aabbcc;margin:2px 3px 2px 0}
.sb{background:#e94560;color:#fff;padding:1px 10px;border-radius:10px;font-size:.78rem;font-weight:700}
.bar{height:3px;border-radius:2px;background:#2a2a4a;margin-top:6px}
.bf{height:100%;border-radius:2px;background:linear-gradient(90deg,#e94560,#0f3460)}
.insight{background:#12122a;border-radius:12px;padding:16px;border:1px solid #2a2a4a;margin:8px 0}
.ig{color:#e94560;font-size:1.8rem;font-weight:800}
.il{color:#8899aa;font-size:.75rem}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def load():
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    client = chromadb.PersistentClient(path=str(INDEX_DIR), settings=Settings(anonymized_telemetry=False))
    col_sem = client.get_collection("movies_semantic")
    col_ens = client.get_collection("movies_ensemble")
    model = SentenceTransformer(str(INDEX_DIR / "sentence_model"))
    with open(INDEX_DIR / "artifacts.pkl", "rb") as f: artifacts = pickle.load(f)
    with open(INDEX_DIR / "tfidf.pkl", "rb") as f: tfidf = pickle.load(f)
    with open(INDEX_DIR / "svd.pkl", "rb") as f: svd_m = pickle.load(f)
    with open(INDEX_DIR / "scaler.pkl", "rb") as f: scaler = pickle.load(f)
    return col_sem, col_ens, model, artifacts, tfidf, svd_m, scaler

try:
    col_sem, col_ens, model, artifacts, tfidf, svd_m, scaler = load()
    meta = artifacts["meta"]
    title_to_id = {m["title"]: m["id"] for m in meta}
    id_to_title = {m["id"]: m["title"] for m in meta}
    all_genres = artifacts["all_genres"]
except Exception as e:
    st.error(f"Run `python3 build_index.py` first: {e}")
    st.stop()

def get_movie(id_val):
    return next((m for m in meta if m["id"] == id_val), None)

def compute_hybrid_score(query_emb, movie_meta):
    """Hybrid score: semantic similarity + rating boost + popularity + recency."""
    s = float(query_emb[0]) if isinstance(query_emb, (list, np.ndarray)) else 0.5
    r = (movie_meta.get("vote_weighted", 5) - 5) / 5  # -1 to 1
    p = min(movie_meta.get("popularity", 0) / 20, 1)
    rec = movie_meta.get("recency_score", 0.5)
    return 0.45 * s + 0.20 * r + 0.20 * p + 0.15 * rec

def recommend_text(query, n=12):
    emb = model.encode([query])[0].tolist()
    raw = col_sem.query(query_embeddings=[emb], n_results=n*3, include=["distances","metadatas"])
    scored = []
    for i, (mid, dist, m) in enumerate(zip(raw["ids"][0], raw["distances"][0], raw["metadatas"][0])):
        mm = get_movie(int(mid))
        if not mm: continue
        sim = 1 - dist
        hybrid = compute_hybrid_score([sim], mm)
        scored.append((mm, sim, hybrid, "semantic"))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:n]

def recommend_movie(movie_id, n=12):
    """Find similar movies using ensemble embedding + hybrid scoring."""
    mm = get_movie(movie_id)
    if not mm: return []
    
    # Get ensemble embedding for this movie
    ens_result = col_ens.get(ids=[str(movie_id)], include=["embeddings"])
    if not ens_result["embeddings"]: return []
    
    query_emb = ens_result["embeddings"][0]
    raw = col_ens.query(query_embeddings=[query_emb], n_results=n*3, include=["distances","metadatas"])
    
    scored = []
    for mid, dist, m in zip(raw["ids"][0], raw["distances"][0], raw["metadatas"][0]):
        mid_int = int(mid)
        if mid_int == movie_id: continue
        candidate = get_movie(mid_int)
        if not candidate: continue
        sim = 1 - dist
        # Genre overlap bonus
        query_genres = set(mm.get("genre_names", []))
        cand_genres = set(candidate.get("genre_names", []))
        genre_overlap = len(query_genres & cand_genres) / max(len(query_genres | cand_genres), 1)
        hybrid = 0.50 * sim + 0.15 * genre_overlap + 0.20 * (candidate.get("vote_weighted", 5) / 10) + 0.15 * min(candidate.get("popularity", 0) / 20, 1)
        scored.append((candidate, sim, hybrid, "ensemble"))
    
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:n]

def recommend_multi_movie(movie_ids, n=12):
    """Blend multiple movies: centroid in ensemble space."""
    embeddings = []
    for mid in movie_ids:
        r = col_ens.get(ids=[str(mid)], include=["embeddings"])
        if r["embeddings"]:
            embeddings.append(r["embeddings"][0])
    if not embeddings:
        return recommend_movie(movie_ids[0], n)
    centroid = np.mean(embeddings, axis=0).tolist()
    raw = col_ens.query(query_embeddings=[centroid], n_results=n*3, include=["distances","metadatas"])
    scored = []
    for mid, dist, m in zip(raw["ids"][0], raw["distances"][0], raw["metadatas"][0]):
        if int(mid) in movie_ids: continue
        c = get_movie(int(mid))
        if not c: continue
        scored.append((c, 1-dist, 1-dist, "multi-blend"))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:n]

def recommend_hybrid_curated(n=20):
    """Smart picks: high weighted rating + popularity + diverse genres."""
    df = pd.DataFrame(meta)
    df["score"] = (df["vote_weighted"] * 0.4 + np.log1p(df["popularity"]) / 5 * 0.3 + df.get("recency_score", 0.5) * 0.3)
    top = df.nlargest(n*3, "score")
    # Deduplicate genres
    seen_genres = set()
    picks = []
    for _, r in top.iterrows():
        gs = frozenset(r.get("genre_names", []))
        if gs not in seen_genres or len(picks) < n:
            seen_genres.add(gs)
            picks.append((get_movie(r["id"]), 0, r["score"], "curated"))
            if len(picks) >= n: break
    if len(picks) < n:
        for _, r in top.iterrows():
            if len(picks) >= n: break
            mid = r["id"]
            if not any(p[0]["id"] == mid for p in picks):
                picks.append((get_movie(mid), 0, r["score"], "curated"))
    return picks[:n]

def movie_card(m, sim, score, label, key=""):
    genre_str = "".join(f'<span class="mg">{g}</span>' for g in m.get("genre_names", [])[:3])
    year = str(m.get("year", "")) if m.get("year") else ""
    runtime = f'{int(m.get("runtime", 0))}min' if m.get("runtime", 0) else ""
    rating = m.get("vote_average", 0)
    st.markdown(f"""<div class="mc">
        <div class="mt">{m["title"]} <span class="sb">{score:.0%}</span></div>
        <div class="mm">{'⭐'+str(rating) if rating else ''} {'· '+year if year else ''} {'· '+runtime if runtime else ''}</div>
        <div style="margin-top:4px">{genre_str}</div>
        <div class="bar"><div class="bf" style="width:{score*100:.0f}%"></div></div>
    </div>""", unsafe_allow_html=True)

# ── UI ──
st.markdown("""<h1 style="text-align:center;font-size:2.8rem;
background:linear-gradient(135deg,#e94560,#0f3460,#533483);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:0">
🎬 Movie Mind
</h1>
<p style="text-align:center;color:#8899aa;font-size:.9rem;margin-top:-4px">
Multi-modal vector recommender · Semantic · TF-IDF · Hybrid Ensemble
</p>""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Semantic Search", "🎯 Similar Movies", "🎭 Multi-Blend", "⭐ Curated Picks"])

with tab1:
    query = st.text_input("Describe what you want to watch", placeholder="A mind-bending sci-fi with philosophical themes...")
    if query:
        with st.spinner("🧠 Searching..."):
            results = recommend_text(query)
        st.markdown(f'<p style="color:#8899aa">Found {len(results)} matches for your query</p>', unsafe_allow_html=True)
        for m, sim, hybrid, label in results:
            movie_card(m, sim, hybrid, label)

with tab2:
    selected = st.selectbox("Pick a movie you like", [""] + sorted([m["title"] for m in meta]), key="sim_movie")
    if selected:
        mid = title_to_id[selected]
        with st.spinner(f"🔍 Finding movies like {selected}..."):
            results = recommend_movie(mid)
        st.markdown(f'<p style="color:#8899aa">Because you liked <strong>{selected}</strong></p>', unsafe_allow_html=True)
        for m, sim, hybrid, label in results:
            movie_card(m, sim, hybrid, label)

with tab3:
    selected_multi = st.multiselect("Pick 2-3 movies you like", sorted([m["title"] for m in meta]), max_selections=5)
    if len(selected_multi) >= 2:
        mids = [title_to_id[t] for t in selected_multi]
        with st.spinner("🎭 Blending..."):
            results = recommend_multi_movie(mids)
        st.markdown(f'<p style="color:#8899aa">Blending {", ".join(selected_multi)}</p>', unsafe_allow_html=True)
        for m, sim, hybrid, label in results:
            movie_card(m, sim, hybrid, label)

with tab4:
    if st.button("🎲 Generate picks", type="primary"):
        with st.spinner("Curating..."):
            results = recommend_hybrid_curated()
        for m, sim, hybrid, label in results:
            movie_card(m, sim, hybrid, label)

# ── Insights sidebar ──
with st.sidebar:
    st.markdown("### 📊 Stats")
    st.markdown(f"""<div class="insight"><span class="ig">{len(meta)}</span><div class="il">Movies indexed</div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="insight"><span class="ig">{len(all_genres)}</span><div class="il">Genre categories</div></div>""", unsafe_allow_html=True)
    
    top_rated = sorted(meta, key=lambda m: m.get("vote_weighted", 0), reverse=True)[:5]
    st.markdown("### 🏆 Top Rated")
    for m in top_rated:
        st.markdown(f"**{m['title']}** — ⭐ {m['vote_average']:.1f}")
    
    st.markdown("### ⚙️ How it works")
    st.markdown("""
    1. **Semantic** — Sentence embeddings via all-MiniLM-L6-v2  
    2. **TF-IDF** — Latent overview features (SVD-50)  
    3. **Numerical** — Budget, revenue, rating, recency  
    4. **Ensemble** — Weighted concatenation of all signals  
    5. **Hybrid scoring** — Semantic + rating + popularity + recency
    """)

st.markdown("---")
st.markdown("<div style='text-align:center;font-size:.72rem;color:#555'>Data: TMDB 5000 · Embeddings: all-MiniLM-L6-v2 · Vector DB: Chroma · TF-IDF + SVD · Hybrid ensemble</div>", unsafe_allow_html=True)
