import json
import numpy as np
from sklearn.manifold import TSNE
from scipy.spatial import cKDTree
import os

# =========================
# CONFIG
# =========================
INPUT_PATH = "backend/data/upenn/embeddings_2024F.json"
OUTPUT_FRONTEND = "course-visualization/public/penn_educ_tsne_coords.json"

# t-SNE + overlap handling params
PERPLEXITY = 30.0
MIN_DIST = 1.0
MAGNIFICATION = 2.0
JITTER_RADIUS = 0.01
RANDOM_SEED = 42

# =========================
# Overlap separation
# =========================
def separate_overlapping_points(coords, similarity_matrix, course_keys,
                                min_dist=1.0, magnification=2.0, jitter_radius=0.01, random_seed=42):
    n = coords.shape[0]
    print(f"Magnifying coordinates by factor {magnification}...")
    coords_scaled = coords * magnification

    print("Finding exact duplicates...")
    tree = cKDTree(coords_scaled)
    duplicate_threshold = min_dist * magnification * 0.1
    pairs = tree.query_pairs(duplicate_threshold, output_type='set')
    keep_together = set()

    print(f"Applying jitter to {len(pairs)} duplicate pairs...")
    np.random.seed(random_seed)
    jittered = np.zeros(n, dtype=bool)

    for i, j in pairs:
        if (i, j) in keep_together:
            continue
        if not jittered[i] and not jittered[j]:
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.uniform(0, jitter_radius * magnification)
            jitter = radius * np.array([np.cos(angle), np.sin(angle)])

            coords_scaled[i] += jitter
            coords_scaled[j] -= jitter
            jittered[i] = True
            jittered[j] = True

    return coords_scaled

# =========================
# Main
# =========================
if __name__ == "__main__":
    print(f"Reading from {INPUT_PATH}...")
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Keep only rows that have embeddings
    courses = []
    for c in data:
        emb = c.get("embedding")
        if isinstance(emb, list) and len(emb) > 0:
            courses.append(c)

    if not courses:
        raise RuntimeError(f"No embeddings found in {INPUT_PATH}.")

    labels = [
        f"{c.get('course_codes',[ ''])[0]} — {c.get('course_title','').strip()}".strip(" —")
        for c in courses
    ]
    # Handle list of codes
    codes = [c.get("course_codes", [""])[0] for c in courses]
    titles = [c.get("course_title", "").strip() for c in courses]

    X = np.array([c["embedding"] for c in courses], dtype=np.float32)
    n, dim = X.shape
    print(f"Loaded {n} courses with embeddings (dim={dim}).")

    # Normalize
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X = X / norms

    # Similarity matrix
    print("Computing cosine similarity matrix...")
    sim_matrix = X @ X.T
    sim_matrix = np.clip(sim_matrix, 0.0, 1.0)
    np.fill_diagonal(sim_matrix, 1.0)
    
    print("Converting similarity to distance matrix...")
    dist_matrix = 1.0 - sim_matrix
    np.fill_diagonal(dist_matrix, 0.0)
    dist_matrix = (dist_matrix + dist_matrix.T) / 2.0

    # Run t-SNE
    safe_perplexity = min(PERPLEXITY, max(2.0, (n - 1) / 3.0))
    print(f"Running t-SNE on {n} courses (perplexity={safe_perplexity:.2f})...")
    
    tsne = TSNE(
        n_components=2,
        metric="precomputed",
        random_state=RANDOM_SEED,
        perplexity=safe_perplexity,
        init="random",
    )
    coords = tsne.fit_transform(dist_matrix)

    # Separate overlaps
    print("Separating overlaps...")
    course_keys = [("unknown", code) for code in codes]
    coords = separate_overlapping_points(
        coords, sim_matrix, course_keys,
        min_dist=MIN_DIST, magnification=MAGNIFICATION,
        jitter_radius=JITTER_RADIUS, random_seed=RANDOM_SEED
    )

    # Save output
    output = []
    for i in range(n):
        x, y = coords[i]
        output.append({
            "code": codes[i],
            "title": titles[i],
            "label": labels[i],
            "x": float(x),
            "y": float(y),
        })

    os.makedirs(os.path.dirname(OUTPUT_FRONTEND), exist_ok=True)
    with open(OUTPUT_FRONTEND, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved t-SNE coordinates to {OUTPUT_FRONTEND}")
