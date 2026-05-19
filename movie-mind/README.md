# Movie Mind 🎬

Multi-modal vector movie recommender using semantic search, TF-IDF latent features, genre/numerical signals, and an ensemble hybrid scoring system.

## How it works

Four recommendation layers, stacked:

1. **Semantic** — Sentence embeddings (all-MiniLM-L6-v2) of overviews, taglines, genres, keywords, cast, director
2. **TF-IDF Latent** — TF-IDF on overviews → SVD (50 components) for keyword-level signal
3. **Numerical + Genre** — Budget, revenue, rating, popularity, recency, runtime, multi-hot genre vector
4. **Ensemble** — All three layers weighted and concatenated (0.5/0.2/0.3)

Each layer embedded into ChromaDB with cosine distance. Final ranking uses a hybrid score blending semantic similarity + weighted rating + popularity + recency.

## Recommenders

| Mode | What it does |
|------|-------------|
| 🔍 Semantic Search | Free-text query → semantic embedding → find nearest neighbors |
| 🎯 Similar Movies | Pick a movie → ensemble embedding → hybrid score (with genre overlap bonus) |
| 🎭 Multi-Blend | Pick 2-3 movies → centroid in ensemble space → blended recommendations |
| ⭐ Curated Picks | Top picks by weighted rating + popularity + genre diversity |

## Setup

```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt

# Set protobuf env var to avoid C extension issues
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Build the index (~2 min, downloads sentence-transformers model)
python3 build_index.py

# Run the app
streamlit run app.py
```

> If `build_index.py` crashes with a protobuf descriptor error, set `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` before running (as shown above). This uses pure-Python protobuf parsing which is slower but avoids the C extension compatibility issue.

## Data

[TMDB 5000 Movie Dataset](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata) — 4,803 movies with overviews, metadata, and credits.

## Stack

- **Vector DB**: ChromaDB (persistent, cosine distance)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **TF-IDF**: scikit-learn (2k features, bigrams, SVD-50)
- **UI**: Streamlit
