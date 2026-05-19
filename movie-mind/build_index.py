#!/usr/bin/env python3
"""Movie Mind — Build vector index with multi-modal embeddings & hybrid scoring."""
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import json, pickle, re
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).parent
DATA = BASE / "data"
INDEX_DIR = BASE / "index"
MOVIES_PATH = DATA / "tmdb_5000_movies.csv"
CREDITS_PATH = DATA / "tmdb_5000_credits.csv"

def json_parse(val):
    if pd.isna(val) or val == "": return []
    try: return json.loads(val) if isinstance(val, str) else val
    except: return []

def build_feature_frame(movies, credits):
    """Build an enriched feature DataFrame with all signals."""
    df = movies.copy()

    # ── Parse JSON columns ──
    for col in ["genres", "keywords", "production_companies", "production_countries", "spoken_languages"]:
        df[col] = df[col].apply(json_parse)
    df["genre_names"] = df["genres"].apply(lambda g: [x["name"] for x in g] if isinstance(g, list) else [])
    df["keyword_names"] = df["keywords"].apply(lambda k: [x["name"] for x in k] if isinstance(k, list) else [])
    df["company_names"] = df["production_companies"].apply(lambda c: [x["name"] for x in c] if isinstance(c, list) else [])

    # ── Parse Credits ──
    credits["cast_json"] = credits["cast"].apply(lambda x: json_parse(x) if isinstance(x, str) else [])
    credits["crew_json"] = credits["crew"].apply(lambda x: json_parse(x) if isinstance(x, str) else [])
    credits["top_cast"] = credits["cast_json"].apply(lambda c: [x["name"] for x in c[:5]] if isinstance(c, list) else [])
    credits["director"] = credits["crew_json"].apply(
        lambda c: next((x["name"] for x in c if isinstance(x, dict) and x.get("job") == "Director"), "") if isinstance(c, list) else ""
    )

    df = df.merge(credits[["movie_id", "top_cast", "director"]], left_on="id", right_on="movie_id", how="left")
    df["top_cast"] = df["top_cast"].apply(lambda c: c if isinstance(c, list) else [])
    df["director"] = df["director"].fillna("")

    # ── Numerical features ──
    df["budget"] = df["budget"].fillna(0).astype(float)
    df["revenue"] = df["revenue"].fillna(0).astype(float)
    df["runtime"] = df["runtime"].fillna(0).astype(float)
    df["popularity"] = df["popularity"].fillna(0).astype(float)
    df["vote_count"] = df["vote_count"].fillna(0).astype(int)
    df["vote_average"] = df["vote_average"].fillna(0).astype(float)

    # ── Derived features ──
    df["profit"] = df["revenue"] - df["budget"]
    df["roi"] = df.apply(lambda r: r["profit"] / r["budget"] if r["budget"] > 0 else 0, axis=1)
    df["budget_log"] = np.log1p(df["budget"])
    df["revenue_log"] = np.log1p(df["revenue"])
    df["popularity_log"] = np.log1p(df["popularity"])

    # ── Year features ──
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["year"] = df["release_date"].dt.year.fillna(0).astype(int)
    df["decade"] = (df["year"] // 10 * 10).astype(int)
    df["age_days"] = (pd.Timestamp.now() - df["release_date"]).dt.days.fillna(0)
    df["recency_score"] = 1 / (1 + df["age_days"] / 365.25)  # exponential recency weight

    # ── Bayesian weighted rating ──
    C = df["vote_average"].mean()
    m_quantile = df["vote_count"].quantile(0.90)
    df["vote_weighted"] = (df["vote_count"] * df["vote_average"] + m_quantile * C) / (df["vote_count"] + m_quantile)

    # ── Language features ──
    df["is_english"] = (df["original_language"] == "en").astype(int)

    # ── Runtime buckets ──
    df["short"] = (df["runtime"] < 90).astype(int)
    df["medium"] = ((df["runtime"] >= 90) & (df["runtime"] < 150)).astype(int)
    df["long"] = (df["runtime"] >= 150).astype(int)

    return df

def build_text_embedding(movie):
    """Build rich text for sentence embedding."""
    parts = []
    for f in ["title", "tagline", "overview"]:
        v = movie.get(f, "")
        if v and isinstance(v, str) and v.strip():
            parts.append(f"{f.capitalize()}: {v.strip()}")
    for label, col in [("Genres", "genre_names"), ("Keywords", "keyword_names"), ("Cast", "top_cast")]:
        vals = movie.get(col, [])
        if vals and isinstance(vals, list):
            parts.append(f"{label}: {', '.join(str(v) for v in vals[:8])}")
    director = movie.get("director", "")
    if director:
        parts.append(f"Director: {director}")
    return " | ".join(parts)

def genre_vector(genre_names, all_genres):
    """Create multi-hot genre vector."""
    vec = [1 if g in genre_names else 0 for g in all_genres]
    return vec

def build_hybrid_vector(movie, all_genres):
    """Build hybrid feature vector: numerical + genre + text latent."""
    vec = []
    vec.append(movie.get("popularity_log", 0))
    vec.append(movie.get("budget_log", 0))
    vec.append(movie.get("revenue_log", 0))
    vec.append(movie.get("vote_weighted", 0))
    vec.append(movie.get("recency_score", 0))
    vec.append(movie.get("runtime", 0) / 300)
    vec.append(movie.get("is_english", 0))
    vec.append(movie.get("roi", 0) / 100)
    vec.extend(genre_vector(movie.get("genre_names", []), all_genres))
    return vec

def main():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Loading data ===")
    movies = pd.read_csv(MOVIES_PATH)
    credits = pd.read_csv(CREDITS_PATH)
    df = build_feature_frame(movies, credits)
    df = df[df["overview"].notna() & (df["overview"] != "")].copy()
    print(f"Loaded {len(df)} movies with overviews")

    all_genres = sorted(set(g for genres in df["genre_names"] for g in genres))
    print(f"Genres: {len(all_genres)}")

    # ── Layer 1: Sentence embeddings (semantic) ──
    print("\n=== Layer 1: Sentence embeddings ===")
    texts = df.apply(build_text_embedding, axis=1).tolist()
    text_model = SentenceTransformer("all-MiniLM-L6-v2")
    sent_embeddings = text_model.encode(texts, show_progress_bar=True, batch_size=64)
    print(f"  Semantic embeddings: {sent_embeddings.shape}")

    # ── Layer 2: TF-IDF on overviews ──
    print("\n=== Layer 2: TF-IDF overview features ===")
    tfidf = TfidfVectorizer(max_features=2000, stop_words="english", ngram_range=(1, 2))
    tfidf_matrix = tfidf.fit_transform(df["overview"].fillna(""))
    svd = TruncatedSVD(n_components=50, random_state=42)
    tfidf_latent = svd.fit_transform(tfidf_matrix)
    print(f"  TF-IDF latent (SVD-50): {tfidf_latent.shape}")

    # ── Layer 3: Hybrid numerical + genre vector ──
    print("\n=== Layer 3: Hybrid feature vector ===")
    hybrid_vecs = np.array([build_hybrid_vector(row, all_genres) for _, row in df.iterrows()])
    scaler = StandardScaler()
    hybrid_scaled = scaler.fit_transform(hybrid_vecs)
    print(f"  Hybrid features: {hybrid_scaled.shape}")

    # ── Layer 4: Ensemble embedding ──
    print("\n=== Layer 4: Ensemble embedding ===")
    sent_norm = sent_embeddings / (np.linalg.norm(sent_embeddings, axis=1, keepdims=True) + 1e-8)
    tfidf_norm = tfidf_latent / (np.linalg.norm(tfidf_latent, axis=1, keepdims=True) + 1e-8)
    hybrid_norm = hybrid_scaled / (np.linalg.norm(hybrid_scaled, axis=1, keepdims=True) + 1e-8)

    # Weighted ensemble: semantic(0.5) + tfidf(0.2) + hybrid(0.3)
    ensemble = np.concatenate([
        sent_norm * 0.5,
        tfidf_norm * 0.2,
        hybrid_norm * 0.3,
    ], axis=1)
    print(f"  Ensemble: {ensemble.shape}")

    # ── Build ChromaDB index (semantic) ──
    print("\n=== Building ChromaDB index (semantic layer) ===")
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(INDEX_DIR), settings=Settings(anonymized_telemetry=False))
    for name in ["movies_semantic", "movies_ensemble"]:
        try: client.delete_collection(name)
        except: pass

    col_sem = client.create_collection("movies_semantic", metadata={"hnsw:space": "cosine"})
    col_ens = client.create_collection("movies_ensemble", metadata={"hnsw:space": "cosine"})

    ids = [str(x) for x in df["id"].tolist()]
    meta_list = [{"title": r["title"], "id": int(r["id"]), "year": int(r["year"]) if r["year"] else 0,
                  "rating": float(r["vote_average"]), "genres": ",".join(r["genre_names"][:4])}
                for _, r in df.iterrows()]

    batch = 100
    for i in range(0, len(ids), batch):
        end = min(i + batch, len(ids))
        col_sem.add(embeddings=sent_embeddings[i:end].tolist(), ids=ids[i:end], metadatas=meta_list[i:end], documents=texts[i:end])
        col_ens.add(embeddings=ensemble[i:end].tolist(), ids=ids[i:end], metadatas=meta_list[i:end])
        print(f"  {end}/{len(ids)}")

    print(f"\n✅ Semantic: {col_sem.count()} | Ensemble: {col_ens.count()}")

    # ── Save artifacts ──
    print("\n=== Saving artifacts ===")
    artifacts = {
        "all_genres": all_genres,
        "ids": ids,
        "titles": df["title"].tolist(),
        "meta": df[["id","title","vote_average","vote_count","vote_weighted","year","popularity","runtime","revenue","budget","genres","genre_names","keyword_names","top_cast","director","overview","tagline","recency_score"]].to_dict("records"),
        "years": df["year"].tolist(),
        "ratings": df["vote_average"].tolist(),
        "weighted_ratings": df["vote_weighted"].tolist(),
        "popularities": df["popularity_log"].tolist(),
    }
    with open(INDEX_DIR / "artifacts.pkl", "wb") as f:
        pickle.dump(artifacts, f)
    text_model.save(str(INDEX_DIR / "sentence_model"))
    with open(INDEX_DIR / "tfidf.pkl", "wb") as f:
        pickle.dump(tfidf, f)
    with open(INDEX_DIR / "svd.pkl", "wb") as f:
        pickle.dump(svd, f)
    with open(INDEX_DIR / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    print("✅ All artifacts saved!")
    print(f"   Movies indexed: {len(df)}")
    print(f"   Embedding dims: semantic={sent_embeddings.shape[1]}, ensemble={ensemble.shape[1]}")

if __name__ == "__main__":
    main()
