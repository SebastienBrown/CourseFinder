#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ============================
# Curriculum metrics (flags)
# ============================

import argparse                           # CLI flags
import json, re, ast                      # JSON I/O, regex, safe literal parsing
import numpy as np                        # numeric ops
import pandas as pd                       # CSV I/O
import networkx as nx                     # graphs

# ---------- CLI arguments ----------
parser = argparse.ArgumentParser(description="Compute curriculum diversity/depth metrics per student (no overwrite).")
parser.add_argument("--graph_json", required=True, help="Path to similarity JSON (e.g., output_similarity_2324F.json)")
parser.add_argument("--students_csv", required=True, help="Path to student CSV with per-term columns")
parser.add_argument("--out_csv", required=True, help="Path to write metrics-only CSV")
parser.add_argument("--min_sim", type=float, default=0.75, help="Similarity cutoff for FILTERED subgraphs (default: 0.75)")
parser.add_argument("--keep_top_k", type=int, default=None, help="Keep top-K neighbors by similarity per node (optional)")
parser.add_argument("--debug", action="store_true", help="Verbose debug prints")
args = parser.parse_args()

# ---------- Resolve flags to vars ----------
INPUT_JSON = args.graph_json                          # big JSON similarity file
INPUT_STUDENT_CSV = args.students_csv                  # original student CSV
OUTPUT_METRICS_CSV = args.out_csv                      # metrics-only output CSV
MIN_SIM = args.min_sim                                 # similarity threshold
KEEP_TOP_K = args.keep_top_k                           # optional KNN pruning
DEBUG = args.debug                                     # debug flag

# ---------- Regex / small parsers ----------
pat_code = re.compile(r"[A-Za-z]{2,5}-\d{2,4}[A-Za-z]?")   # course code like ECON-111 / PSYC-498D
pat_sem  = re.compile(r"^(\d{4})([A-Z])$")                 # semester like 2223F / 2021S / 0910F
TERM_ORDER = {"F": 0, "J": 1, "S": 2}                      # within-year ordering

def parse_courses_from_cell(s):
    """Parse a cell into a list of course codes (try list literal, else regex)."""
    try:
        lst = ast.literal_eval(s)                          # try ["ECON-111", "MATH-121"]
        if isinstance(lst, list):
            return [str(x).strip().upper() for x in lst if isinstance(x, str)]
    except Exception:
        pass
    return [m.group(0).upper() for m in pat_code.finditer(str(s))]  # fallback regex

def canon_node_id(codes, semester):
    """Canonical node id = sorted codes + semester joined by '|', stable across order."""
    cleaned = sorted(str(c).strip() for c in codes if c and str(c).strip())
    return "|".join(cleaned + [str(semester).strip()])

def normalize_semester(sem):
    """Return (yyyy, termletter) if valid, else (None, None)."""
    m = pat_sem.match(str(sem).strip())
    return (m.group(1), m.group(2)) if m else (None, None)

# ---------- Read JSON + build UNFILTERED graph ----------
with open(INPUT_JSON, "r") as f:                         # open similarity JSON
    data = json.load(f)                                  # list of course entries
print(f"JSON entries: {len(data)}")                      # quick diag

edges_acc, node_meta = {}, {}                            # edge accumulator, node metadata
for entry in data:                                       # loop over source entries
    src_codes = entry.get("course_codes", [])            # list or str
    if isinstance(src_codes, str): src_codes = [src_codes]
    src_sem   = entry.get("semester", "")                # e.g., '2324F'
    if not src_codes: continue                           # skip empties
    u = canon_node_id(src_codes, src_sem)                # canonical node id
    node_meta.setdefault(u, (tuple(sorted(src_codes)), src_sem))  # store meta once

    for comp in entry.get("compared_courses", []) or []: # neighbors
        dst_codes = comp.get("course_codes", [])
        if isinstance(dst_codes, str): dst_codes = [dst_codes]
        dst_sem   = comp.get("semester", "")
        if not dst_codes: continue
        v = canon_node_id(dst_codes, dst_sem)            # neighbor id
        node_meta.setdefault(v, (tuple(sorted(dst_codes)), dst_sem))
        sim = comp.get("similarity_score")               # similarity in [0,1]
        if sim is None or u == v:                        # skip missing/self
            continue
        a, b = sorted((u, v))                            # undirected edge key
        prev = edges_acc.get((a, b))                     # keep *max* sim if seen twice
        edges_acc[(a, b)] = sim if prev is None else max(prev, sim)

G = nx.Graph()                                           # build graph
for node, (codes, sem) in node_meta.items():             # add nodes
    G.add_node(node, codes="|".join(codes), semester=sem)
for (u, v), sim in edges_acc.items():                    # add edges with sim + distance weight
    G.add_edge(u, v, similarity=float(sim), weight=1.0 - float(sim))

# Optional: keep only top-K similar neighbors per node
if KEEP_TOP_K is not None:
    for n in list(G.nodes()):
        nbrs = list(G[n].items())                        # [(nbr, attrdict), ...]
        nbrs.sort(key=lambda kv: kv[1].get("similarity", 0.0), reverse=True)
        for drop_u, _ in nbrs[KEEP_TOP_K:]:              # drop weaker beyond K
            if G.has_edge(n, drop_u):
                G.remove_edge(n, drop_u)

print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# ---------- Build lookup maps (with robust fallback) ----------
code_sem_to_node, code_to_sem_nodes = {}, {}             # exact + index-by-code
for node_id, attrs in G.nodes(data=True):
    codes_str = attrs.get("codes", "")
    sem = attrs.get("semester", "")
    for code in codes_str.split("|"):
        code_u = code.strip().upper()
        code_sem_to_node[(code_u, sem)] = node_id        # exact (code, semester)
        code_to_sem_nodes.setdefault(code_u, []).append((sem, node_id))  # bucket by code

# ---------- Load students ----------
df = pd.read_csv(INPUT_STUDENT_CSV)                      # original CSV (we do NOT overwrite it)
semester_cols = [c for c in df.columns if pat_sem.match(c)]  # detect per-term columns
if DEBUG:
    print("Detected semester columns:", semester_cols)




def pick_fallback_node(code_u, sem_csv):
    """If (code, sem_csv) missing: prefer same term-letter; else most recent semester for that code."""
    if code_u not in code_to_sem_nodes:                  # no such code anywhere
        return None
    yy, tt = normalize_semester(sem_csv)                 # (yyyy, termletter)
    if tt:
        same_term = [(s, nid) for (s, nid) in code_to_sem_nodes[code_u]
                     if normalize_semester(s)[1] == tt]
        if same_term:
            return sorted(same_term, key=lambda t: t[0])[-1][1]  # most recent lexicographically
    return sorted(code_to_sem_nodes[code_u], key=lambda t: t[0])[-1][1]  # most recent overall

# ---------- Metric helpers ----------
def _course_level(code):
    """Return 100/200/300/400 from 'SUBJ-123X' or None if no 3-digit block."""
    m = re.search(r"-(\d{3})", str(code))
    return (int(m.group(1)) // 100) * 100 if m else None

def average_course_difficulty_from_row(row, sem_cols):
    """Mean hundreds level across all listed courses (NaN if none)."""
    lvls = []                                  # Start an empty list to collect "hundreds" levels (e.g., 100/200/300/400)

    for sem in sem_cols:                       # Loop over each semester column name (e.g., "2223F", "2223S")
        # parse_courses_from_cell reads the cell (row[sem]) and returns a list of course codes
        # e.g., ['ECON-111', 'MATH-211'] even if the cell was a string like '["ECON-111","MATH-211"]'
        for c in parse_courses_from_cell(row[sem]):  
            lvl = _course_level(c)             # Extract the hundreds level from the code, e.g. 'MATH-211' -> 200
            if lvl is not None:                # Only keep valid results (skip malformed codes that don’t match the pattern)
                lvls.append(lvl)               # Add the level (int like 100/200/300/400) to our list

    # If we collected at least one level, compute the arithmetic mean and cast to a plain float.
    # If we found none (no valid courses), return NaN to signal "no data".
    return float(np.mean(lvls)) if lvls else float("nan")

def compute_pairwise_shortest_distances(subg, weight_key="weight"):
    """Weighted shortest-path distances for unique pairs (i<j) inside each component."""
    if subg.number_of_nodes() <= 1:                  # If there are 0 or 1 nodes, there are no pairs to measure.
        return []                                    # Return an empty list to signal "no distances".

    # Run all-pairs Dijkstra on this subgraph using the given edge-weight attribute (default: "weight").
    # Returns a dict-of-dicts like: {u: {v: distance_uv, ...}, ...}. Unreachable pairs are omitted,
    # which naturally skips cross-component pairs.
    lengths = dict(nx.all_pairs_dijkstra_path_length(subg, weight=weight_key))

    nodes = list(subg.nodes())                       # Freeze the node order into a list for stable indexing.
    idx = {n: i for i, n in enumerate(nodes)}        # Map each node to its integer index (for upper-triangle filtering).

    dists = []                                       # We'll accumulate one distance per unordered pair (i<j) here.

    for u, lu in lengths.items():                    # Loop over each source node u and its reachable-targets dict lu.
        iu = idx[u]                                  # Get u's integer index once (micro-optimization).
        for v, d in lu.items():                      # For each reachable target v with distance d = dist(u, v) ...
            iv = idx[v]                              # Get v's index.
            if iv > iu:                              # Keep only upper-triangle entries: i<j (drops self-pairs i==j and duplicates j,i).
                dists.append(float(d))               # Store as a plain Python float (not NumPy scalar).

    return dists                                     # Distances for all unique pairs across all connected components.

def rao_q_from_distances(n_nodes, pairwise):
    """Rao’s Q (uniform p_i) = ((N-1)/N) * mean(pairwise distances)."""
    return 0.0 if n_nodes <= 1 or not pairwise else ((n_nodes - 1) / n_nodes) * float(np.mean(pairwise))

def weighted_eccentricity_stats(subg, weight_key="weight"):
    """Weighted radius/diameter on the largest component (NaN/NaN if empty; 0/0 if singleton)."""
    n = subg.number_of_nodes()
    if n == 0:
        return float("nan"), float("nan")
    Hc_nodes = max(nx.connected_components(subg), key=len)
    Hc = subg.subgraph(Hc_nodes).copy()
    if Hc.number_of_nodes() == 1:
        return 0.0, 0.0
    try:
        ecc = nx.eccentricity(Hc, weight=weight_key)
        return float(min(ecc.values())), float(max(ecc.values()))
    except Exception:
        lengths = dict(nx.all_pairs_dijkstra_path_length(Hc, weight=weight_key))
        ecc_vals = [max(d.values()) for d in lengths.values()]
        return float(min(ecc_vals)), float(max(ecc_vals))

def average_weighted_clustering(subg, weight_key="similarity"):
    """Mean local clustering coefficient weighted by similarity (NaN if empty)."""
    if subg.number_of_nodes() == 0:
        return float("nan")
    cdict = nx.clustering(subg, weight=weight_key)
    return float(np.mean(list(cdict.values()))) if cdict else float("nan")

def longest_chain_hops(subg):
    """Diameter in hops on largest component (proxy for 'progression depth')."""
    if subg.number_of_nodes() == 0:
        return 0
    Hc_nodes = max(nx.connected_components(subg), key=len)
    Hc = subg.subgraph(Hc_nodes).copy()
    if Hc.number_of_nodes() == 1:
        return 0
    try:
        return int(nx.diameter(Hc))
    except Exception:
        lengths = dict(nx.all_pairs_shortest_path_length(Hc))
        return int(max(max(d.values()) for d in lengths.values()))

# ---------- Diversity helpers (Shannon / Simpson / HHI) ----------
def _subject_from_code(code):
    """Extract department prefix: 'ECON-111' -> 'ECON' (None if it doesn’t match)."""
    m = re.match(r"^([A-Za-z]{2,5})-\d{2,4}[A-Za-z]?$", str(code).strip())
    return m.group(1).upper() if m else None

def shannon_simpson_from_codes(all_codes):
    """
    Shannon/Simpson over subjects using *listed* codes:
      - p_i = subject proportions
      - H (Shannon) = -∑ p_i ln p_i
      - H_norm = H / ln(k) for k>=2 (else 0)
      - HHI = ∑ p_i^2
      - Simpson = 1 - HHI
    """
    subs = [_subject_from_code(c) for c in all_codes]
    subs = [s for s in subs if s]
    n = len(subs)
    if n == 0:
        return {
            "shannon_entropy": float("nan"),
            "shannon_entropy_norm": float("nan"),
            "simpson_index": float("nan"),
            "hhi_index": float("nan"),
            "n_subjects": 0,
        }
    from collections import Counter
    cnt = Counter(subs); k = len(cnt)
    p = np.array([c / n for c in cnt.values()], dtype=float)
    mask = p > 0
    H = -np.sum(p[mask] * np.log(p[mask]))
    H_norm = (H / np.log(k)) if k > 1 else 0.0
    hhi = float(np.sum(p * p))
    simpson = 1.0 - hhi
    return {
        "shannon_entropy": float(H),
        "shannon_entropy_norm": float(H_norm),
        "simpson_index": float(simpson),
        "hhi_index": float(hhi),
        "n_subjects": int(k),
    }

# ---------- Per-student analysis ----------
rows = []                                                # all result rows

for idx, row in df.iterrows():                           # iterate students
    mapped, missing = [], []                             # mapped graph nodes, unmatched codes
    all_listed_codes = []                                # keep all listed codes (for Shannon/Simpson)

    for sem in semester_cols:                            # per-term column name (e.g., 2223F)
        parsed_codes = parse_courses_from_cell(row[sem]) # list of codes in that term
        all_listed_codes.extend(parsed_codes)            # collect for diversity metrics
        for code in parsed_codes:
            code_u = code.strip().upper()                # normalize
            node_id = code_sem_to_node.get((code_u, sem))# try exact (code, semester)
            if node_id is None:                          # if missing, use robust fallback
                node_id = pick_fallback_node(code_u, sem)
            if node_id:
                mapped.append(node_id)                   # add mapped node
            else:
                missing.append(f"{code_u}({sem})")       # keep trace of unmapped

    mapped = sorted(set(mapped))                         # unique nodes only
    subG_unf = G.subgraph(mapped).copy()                 # UNFILTERED student subgraph

    n_cross = sum(1 for n in mapped                      # cross-listed count (codes attr contains '|')
                  if '|' in subG_unf.nodes[n].get('codes', ''))

    # Distance-based metrics (UNFILTERED)
    pairwise = compute_pairwise_shortest_distances(subG_unf, weight_key="weight")  # SP distances
    if len(mapped) < 2:                                  # avoid misleading constants
        avg_d = float("nan"); max_d = float("nan")
    else:
        avg_d = float(np.mean(pairwise)) if pairwise else float("nan")
        max_d = float(np.max(pairwise))  if pairwise else float("nan")
    rao_q = rao_q_from_distances(len(mapped), pairwise)  # Rao’s Q from avg pairwise
    ecc_r, ecc_d = weighted_eccentricity_stats(subG_unf, weight_key="weight")  # radius/diameter (weighted)

    # Apply similarity threshold for cohesion/depth metrics (FILTERED)
    subG = subG_unf.copy()
    for u, v, d in list(subG.edges(data=True)):
        if float(d.get("similarity", 0.0)) < float(MIN_SIM):
            subG.remove_edge(u, v)

    comps = list(nx.connected_components(subG))          # components on FILTERED subgraph
    comp_sizes = [len(c) for c in comps]                 # component sizes (desc not required)
    avg_clust = average_weighted_clustering(subG, weight_key="similarity")  # mean clustering
    prog_depth = longest_chain_hops(subG)                # diameter in hops (progression depth)
    avg_diff = average_course_difficulty_from_row(row, semester_cols)       # mean 100/200/300/400

    # Subject diversity (from all *listed* codes)
    div = shannon_simpson_from_codes(all_listed_codes)

    rows.append({                                        # assemble row
        "student_index": idx,
        "StudentID": row.get("StudentID", idx),

        # coverage
        "n_courses": len(mapped) + len(missing),
        "n_crosslisted": n_cross,
        "n_courses_mapped": len(mapped),
        "n_courses_unmapped": len(missing),

        # components (FILTERED)
        "n_components": len(comp_sizes),
        "largest_component": (max(comp_sizes) if comp_sizes else 0),

        # distances (UNFILTERED)
        "avg_distance": avg_d,
        "max_distance": max_d,

        # new metrics
        "rao_q_uniform": rao_q,
        "ecc_radius_weighted": ecc_r,
        "ecc_diameter_weighted": ecc_d,
        "avg_clustering_similarity": avg_clust,
        "progression_depth_hops": prog_depth,
        "avg_course_difficulty": avg_diff,

        # subject diversity
        "shannon_entropy": div["shannon_entropy"],
        "shannon_entropy_norm": div["shannon_entropy_norm"],
        "simpson_index": div["simpson_index"],
        "hhi_index": div["hhi_index"],
        "n_subjects": div["n_subjects"],

        # diagnostics
        "unmapped_example": ", ".join(missing[:6]),
    })

# ---------- Save metrics (no overwrite of the student CSV) ----------
analysis_df = pd.DataFrame(rows)                         # build DataFrame
analysis_df.to_csv(OUTPUT_METRICS_CSV, index=False)      # write metrics-only CSV
print(f"Saved metrics: {OUTPUT_METRICS_CSV}")            # path print
print(f"Total students: {len(analysis_df)}")             # count print

# Optional quick summaries (guard NaNs)
with np.errstate(all="ignore"):
    print(f"Mean RaoQ: {np.nanmean(analysis_df['rao_q_uniform']):.3f}")
    print(f"Mean ecc radius/diam: {np.nanmean(analysis_df['ecc_radius_weighted']):.3f} / "
          f"{np.nanmean(analysis_df['ecc_diameter_weighted']):.3f}")
    print(f"Mean clustering(sim): {np.nanmean(analysis_df['avg_clustering_similarity']):.3f}")
    print(f"Mean depth(hops): {np.nanmean(analysis_df['progression_depth_hops']):.2f}")
    print(f"Mean difficulty: {np.nanmean(analysis_df['avg_course_difficulty']):.1f}")
    print(f"Mean Shannon(norm): {np.nanmean(analysis_df['shannon_entropy_norm']):.3f}, "
          f"Mean Simpson: {np.nanmean(analysis_df['simpson_index']):.3f}")