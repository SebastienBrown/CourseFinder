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
from collections import Counter, defaultdict

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
INPUT_JSON = args.graph_json
INPUT_STUDENT_CSV = args.students_csv
OUTPUT_METRICS_CSV = args.out_csv
MIN_SIM = args.min_sim
KEEP_TOP_K = args.keep_top_k
DEBUG = args.debug

# ---------- Regex / small parsers ----------
pat_code = re.compile(r"[A-Za-z]{2,5}-\d{2,4}[A-Za-z]?")
pat_sem  = re.compile(r"^(\d{4})([A-Z])$")
TERM_ORDER = {"F": 0, "J": 1, "S": 2}

def parse_courses_from_cell(s):
    """Parse a cell into a list of course codes (try list literal, else regex)."""
    try:
        lst = ast.literal_eval(s)
        if isinstance(lst, list):
            return [str(x).strip().upper() for x in lst if isinstance(x, str)]
    except Exception:
        pass
    return [m.group(0).upper() for m in pat_code.finditer(str(s))]

def canon_node_id(codes, semester):
    """Canonical node id = sorted codes + semester joined by '|', stable across order."""
    cleaned = sorted(str(c).strip() for c in codes if c and str(c).strip())
    return "|".join(cleaned + [str(semester).strip()])

def normalize_semester(sem):
    """Return (yyyy, termletter) if valid, else (None, None)."""
    m = pat_sem.match(str(sem).strip())
    return (m.group(1), m.group(2)) if m else (None, None)

# ---------- Read JSON + build UNFILTERED graph ----------
with open(INPUT_JSON, "r") as f:
    data = json.load(f)
print(f"JSON entries: {len(data)}")

edges_acc, node_meta = {}, {}
for entry in data:
    src_codes = entry.get("course_codes", [])
    if isinstance(src_codes, str): src_codes = [src_codes]
    src_sem   = entry.get("semester", "")
    if not src_codes: continue
    u = canon_node_id(src_codes, src_sem)
    node_meta.setdefault(u, (tuple(sorted(src_codes)), src_sem))

    for comp in entry.get("compared_courses", []) or []:
        dst_codes = comp.get("course_codes", [])
        if isinstance(dst_codes, str): dst_codes = [dst_codes]
        dst_sem   = comp.get("semester", "")
        if not dst_codes: continue
        v = canon_node_id(dst_codes, dst_sem)
        node_meta.setdefault(v, (tuple(sorted(dst_codes)), dst_sem))
        sim = comp.get("similarity_score")
        if sim is None or u == v:
            continue
        a, b = sorted((u, v))
        prev = edges_acc.get((a, b))
        edges_acc[(a, b)] = sim if prev is None else max(prev, sim)

G = nx.Graph()
for node, (codes, sem) in node_meta.items():
    G.add_node(node, codes="|".join(codes), semester=sem)
for (u, v), sim in edges_acc.items():
    G.add_edge(u, v, similarity=float(sim), weight=1.0 - float(sim))

# Keep a copy of the ORIGINAL/UNPRUNED graph for "global" RaoQ           # <<< NEW
G_global = G.copy()                                                       # <<< NEW

# Optional: keep only top-K similar neighbors per node (prunes G, not G_global)
if KEEP_TOP_K is not None:
    for n in list(G.nodes()):
        nbrs = list(G[n].items())
        nbrs.sort(key=lambda kv: kv[1].get("similarity", 0.0), reverse=True)
        for drop_u, _ in nbrs[KEEP_TOP_K:]:
            if G.has_edge(n, drop_u):
                G.remove_edge(n, drop_u)

print(f"Graph (possibly pruned): {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
if DEBUG:
    print(f"Global graph (unpruned)  : {G_global.number_of_nodes()} nodes, {G_global.number_of_edges()} edges")

# ---------- Build lookup maps (with robust fallback) ----------
code_sem_to_node, code_to_sem_nodes = {}, {}
for node_id, attrs in G_global.nodes(data=True):  # use global nodes for mapping robustness  # <<< NEW
    codes_str = attrs.get("codes", "")
    sem = attrs.get("semester", "")
    for code in codes_str.split("|"):
        code_u = code.strip().upper()
        code_sem_to_node[(code_u, sem)] = node_id
        code_to_sem_nodes.setdefault(code_u, []).append((sem, node_id))

# ---------- Load students ----------
df = pd.read_csv(INPUT_STUDENT_CSV)
semester_cols = [c for c in df.columns if pat_sem.match(c)]
if DEBUG:
    print("Detected semester columns:", semester_cols)

def pick_fallback_node(code_u, sem_csv):
    """If (code, sem_csv) missing: prefer same term-letter; else most recent semester for that code."""
    if code_u not in code_to_sem_nodes:
        return None
    yy, tt = normalize_semester(sem_csv)
    if tt:
        same_term = [(s, nid) for (s, nid) in code_to_sem_nodes[code_u]
                     if normalize_semester(s)[1] == tt]
        if same_term:
            return sorted(same_term, key=lambda t: t[0])[-1][1]
    return sorted(code_to_sem_nodes[code_u], key=lambda t: t[0])[-1][1]

# ---------- Metric helpers ----------
def _course_level(code):
    """Return 100/200/300/400 from 'SUBJ-123X' or None if no 3-digit block."""
    m = re.search(r"-(\d{3})", str(code))
    return (int(m.group(1)) // 100) * 100 if m else None

def average_course_difficulty_from_row(row, sem_cols):
    """Mean hundreds level across all listed courses (NaN if none)."""
    lvls = []
    for sem in sem_cols:
        for c in parse_courses_from_cell(row[sem]):
            lvl = _course_level(c)
            if lvl is not None:
                lvls.append(lvl)
    return float(np.mean(lvls)) if lvls else float("nan")

def compute_pairwise_shortest_distances(subg, weight_key="weight"):
    """Weighted shortest-path distances for unique pairs (i<j) inside each component."""
    if subg.number_of_nodes() <= 1:
        return []
    lengths = dict(nx.all_pairs_dijkstra_path_length(subg, weight=weight_key))
    nodes = list(subg.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    dists = []
    for u, lu in lengths.items():
        iu = idx[u]
        for v, d in lu.items():
            iv = idx[v]
            if iv > iu:
                dists.append(float(d))
    return dists

def average_pairwise_distance(n_nodes, pairwise):
    """Mean pairwise distance across unordered node pairs in the subgraph."""
    return float(np.mean(pairwise)) if (n_nodes > 1 and pairwise) else float("nan")

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
    """Shannon/Simpson over subjects using *listed* codes."""
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

# ---------- Rao Q helpers ----------
def _subjects_from_codes_attr(codes_attr_str):
    """Parse node 'codes' (pipe-joined) into a set of subject prefixes (handles cross-listing)."""
    subs = set()
    for code in str(codes_attr_str).split("|"):
        s = _subject_from_code(code)
        if s:
            subs.add(s)
    return subs

def rao_q_subject_weighted(subg_unfiltered, all_listed_codes, weight_key="weight", mode="shortest"):
    """
    Rao's Q over subjects for ONE student (with replacement), computed on the student's subgraph:
      - p_i from subject proportions in all_listed_codes.
      - d_ij:
          mode="shortest": mean shortest-path distance between any course in i and any in j (geodesic on student's graph)
          mode="edge":     mean *direct-edge* distance if edge exists else 1.0 (fast fallback)
      - If no observed i–j pairs (or unreachable in 'shortest'): d_ij := 1.0
      - d_ii := 0.0
    Returns float Q (NaN if <2 subjects or graph too small).
    """
    subs = [_subject_from_code(c) for c in all_listed_codes]
    subs = [s for s in subs if s]
    n_codes = len(subs)
    if n_codes == 0:
        return float("nan")
    cnt = Counter(subs)
    subjects = sorted(cnt.keys())
    if len(subjects) == 1:
        return 0.0
    p = {s: cnt[s] / n_codes for s in subjects}

    if subg_unfiltered.number_of_nodes() <= 1:
        return float("nan")

    node_subjects = {n: _subjects_from_codes_attr(subg_unfiltered.nodes[n].get("codes", "")) 
                     for n in subg_unfiltered.nodes()}
    nodes = list(subg_unfiltered.nodes())

    spair_sum = defaultdict(float)
    spair_cnt = defaultdict(int)

    if mode == "shortest":
        lengths = dict(nx.all_pairs_dijkstra_path_length(subg_unfiltered, weight=weight_key))
        for u in nodes:
            lu = lengths.get(u, {})
            Su = node_subjects.get(u, set())
            if not Su:
                continue
            for v, dist_uv in lu.items():
                if v == u:
                    continue
                Sv = node_subjects.get(v, set())
                if not Sv:
                    continue
                d = float(dist_uv)
                for i in Su:
                    for j in Sv:
                        if i == j:
                            continue
                        spair_sum[(i, j)] += d
                        spair_cnt[(i, j)] += 1
    elif mode == "edge":
        idx = {n: k for k, n in enumerate(nodes)}
        for u in nodes:
            Su = node_subjects.get(u, set())
            if not Su:
                continue
            for v in nodes:
                if idx[v] <= idx[u]:
                    continue
                Sv = node_subjects.get(v, set())
                if not Sv:
                    continue
                edata = subg_unfiltered.get_edge_data(u, v)
                d = float(edata.get(weight_key, 1.0)) if edata else 1.0
                for i in Su:
                    for j in Sv:
                        if i == j:
                            continue
                        spair_sum[(i, j)] += d; spair_cnt[(i, j)] += 1
                        spair_sum[(j, i)] += d; spair_cnt[(j, i)] += 1
    else:
        raise ValueError("mode must be 'shortest' or 'edge'")

    def d_ij(i, j):
        if i == j:
            return 0.0
        key = (i, j)
        if spair_cnt.get(key, 0) > 0:
            return spair_sum[key] / spair_cnt[key]
        return 1.0

    Q = 0.0
    for i in subjects:
        for j in subjects:
            Q += p[i] * p[j] * d_ij(i, j)
    return float(Q)

def rao_q_subject_on_global(G_global, mapped_nodes, all_listed_codes, weight_key="weight", mode="shortest"):
    """
    Rao's Q computed using the ORIGINAL (unpruned) global graph distances among the student's mapped nodes.
      - mode="shortest": geodesic distances on G_global between mapped nodes (respects weak ties).
      - mode="edge":     direct-edge distances from G_global; missing edge -> 1.0.
    This answers: what's the expected subject dissimilarity if we measure proximity in the full network?
    """
    subs = [_subject_from_code(c) for c in all_listed_codes]
    subs = [s for s in subs if s]
    n_codes = len(subs)
    if n_codes == 0:
        return float("nan")
    cnt = Counter(subs)
    subjects = sorted(cnt.keys())
    if len(subjects) == 1:
        return 0.0
    p = {s: cnt[s] / n_codes for s in subjects}

    if len(mapped_nodes) <= 1:
        return float("nan")

    node_subjects = {n: _subjects_from_codes_attr(G_global.nodes[n].get("codes", "")) 
                     for n in mapped_nodes}

    spair_sum = defaultdict(float)
    spair_cnt = defaultdict(int)

    mapped_set = set(mapped_nodes)
    if mode == "shortest":
        # Dijkstra from each mapped node, but aggregate only over mapped targets
        for u in mapped_nodes:
            Su = node_subjects.get(u, set())
            if not Su:
                continue
            lu = nx.single_source_dijkstra_path_length(G_global, u, weight=weight_key)
            for v, dist_uv in lu.items():
                if v == u or v not in mapped_set:
                    continue
                Sv = node_subjects.get(v, set())
                if not Sv:
                    continue
                d = float(dist_uv)
                for i in Su:
                    for j in Sv:
                        if i == j:
                            continue
                        spair_sum[(i, j)] += d
                        spair_cnt[(i, j)] += 1
    elif mode == "edge":
        # Direct lookup on global graph
        idx = {n: k for k, n in enumerate(mapped_nodes)}
        for u in mapped_nodes:
            Su = node_subjects.get(u, set())
            if not Su:
                continue
            for v in mapped_nodes:
                if idx[v] <= idx[u]:
                    continue
                Sv = node_subjects.get(v, set())
                if not Sv:
                    continue
                edata = G_global.get_edge_data(u, v)
                d = float(edata.get(weight_key, 1.0)) if edata else 1.0
                for i in Su:
                    for j in Sv:
                        if i == j:
                            continue
                        spair_sum[(i, j)] += d; spair_cnt[(i, j)] += 1
                        spair_sum[(j, i)] += d; spair_cnt[(j, i)] += 1
    else:
        raise ValueError("mode must be 'shortest' or 'edge'")

    def d_ij(i, j):
        if i == j:
            return 0.0
        key = (i, j)
        if spair_cnt.get(key, 0) > 0:
            return spair_sum[key] / spair_cnt[key]
        return 1.0

    Q = 0.0
    for i in subjects:
        for j in subjects:
            Q += p[i] * p[j] * d_ij(i, j)
    return float(Q)

# ---------- Per-student analysis ----------
rows = []

for idx, row in df.iterrows():
    mapped, missing = [], []
    all_listed_codes = []

    for sem in semester_cols:
        parsed_codes = parse_courses_from_cell(row[sem])
        all_listed_codes.extend(parsed_codes)
        for code in parsed_codes:
            code_u = code.strip().upper()
            node_id = code_sem_to_node.get((code_u, sem))
            if node_id is None:
                node_id = pick_fallback_node(code_u, sem)
            if node_id:
                mapped.append(node_id)
            else:
                missing.append(f"{code_u}({sem})")

    mapped = sorted(set(mapped))
    subG_unf = G.subgraph(mapped).copy()     # student's UNFILTERED (but possibly K-pruned) graph

    n_cross = sum(1 for n in mapped if '|' in subG_unf.nodes[n].get('codes', ''))

    # Distance-based metrics (UNFILTERED student graph)
    pairwise = compute_pairwise_shortest_distances(subG_unf, weight_key="weight")
    avg_d = average_pairwise_distance(len(mapped), pairwise)
    max_d = float(np.max(pairwise)) if (pairwise and len(mapped) > 1) else float("nan")

    # Rao's Q (student subgraph, geodesic)
    rao_q_subject_geodesic = rao_q_subject_weighted(subG_unf, all_listed_codes, weight_key="weight", mode="shortest")

    # Rao's Q (GLOBAL graph, geodesic)                                    # <<< NEW
    rao_q_subject_global = rao_q_subject_on_global(                        # <<< NEW
        G_global, mapped, all_listed_codes, weight_key="weight", mode="shortest"
    )                                                                      # <<< NEW

    # OPTIONAL: Rao's Q on GLOBAL graph using direct-edge lookups only     # <<< NEW
    # rao_q_subject_direct = rao_q_subject_on_global(                      # <<< NEW
    #     G_global, mapped, all_listed_codes, weight_key="weight", mode="edge"
    # )

    ecc_r, ecc_d = weighted_eccentricity_stats(subG_unf, weight_key="weight")

    # Apply similarity threshold for cohesion/depth metrics (FILTERED)
    subG = subG_unf.copy()
    for u, v, d in list(subG.edges(data=True)):
        if float(d.get("similarity", 0.0)) < float(MIN_SIM):
            subG.remove_edge(u, v)

    comps = list(nx.connected_components(subG))
    comp_sizes = [len(c) for c in comps]
    avg_clust = average_weighted_clustering(subG, weight_key="similarity")
    prog_depth = longest_chain_hops(subG)
    avg_diff = average_course_difficulty_from_row(row, semester_cols)

    # Subject diversity (from all *listed* codes)
    div = shannon_simpson_from_codes(all_listed_codes)

    rows.append({
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

        # Rao Qs
        "rao_q_subject_geodesic": rao_q_subject_geodesic,   # student graph
        "rao_q_subject_global": rao_q_subject_global,       # original global graph (geodesic)
        # "rao_q_subject_direct": rao_q_subject_direct,     # uncomment if you also want the direct-edge version

        # other graph metrics
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
analysis_df = pd.DataFrame(rows)
analysis_df.to_csv(OUTPUT_METRICS_CSV, index=False)
print(f"Saved metrics: {OUTPUT_METRICS_CSV}")
print(f"Total students: {len(analysis_df)}")

# Optional quick summaries (guard NaNs)
with np.errstate(all="ignore"):
    print(f"Mean RaoQ (student geodesic): {np.nanmean(analysis_df['rao_q_subject_geodesic']):.3f}")
    print(f"Mean RaoQ (global geodesic) : {np.nanmean(analysis_df['rao_q_subject_global']):.3f}")
    # print(f"Mean RaoQ (global direct)   : {np.nanmean(analysis_df['rao_q_subject_direct']):.3f}")  # if enabled
    print(f"Mean ecc radius/diam: {np.nanmean(analysis_df['ecc_radius_weighted']):.3f} / "
          f"{np.nanmean(analysis_df['ecc_diameter_weighted']):.3f}")
    print(f"Mean clustering(sim): {np.nanmean(analysis_df['avg_clustering_similarity']):.3f}")
    print(f"Mean depth(hops): {np.nanmean(analysis_df['progression_depth_hops']):.2f}")
    print(f"Mean difficulty: {np.nanmean(analysis_df['avg_course_difficulty']):.1f}")
    print(f"Mean Shannon(norm): {np.nanmean(analysis_df['shannon_entropy_norm']):.3f}, "
          f"Mean Simpson: {np.nanmean(analysis_df['simpson_index']):.3f}")
