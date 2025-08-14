import json, os
import re
import ast
import pandas as pd
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Config
# -----------------------------
filedate = os.getenv('FILEDATE', '20250813')
INPUT_JSON = os.getenv('INPUT_JSON', '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/3_similarity/gpt_off_the_shelf/output_similarity_all.json')
OUTPUT_DATA = os.getenv('OUTPUT_DATA', f'/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/5_scores/student_scores_{filedate}.csv')

# Convert environment variables to proper types
keep_top_k_str = os.getenv('KEEP_TOP_K', 'None')
KEEP_TOP_K = None if keep_top_k_str == 'None' else int(keep_top_k_str)  # If set to an integer (e.g., 20), keep only the top-K neighbors per node.
MIN_SIM = float(os.getenv('MIN_SIM', '0.75'))     # Minimum similarity threshold for keeping edges

# -----------------------------
# Functions
# -----------------------------
def canon_node_id(codes, semester):
    """
    Given a list like ['EDST-200','AMST-200','SOCI-200'] and semester like '2223F',
    return a stable, canonical node ID string that includes both course codes and semester.

    Why do this?
    - We want the same combination of codes AND semester to map to the same node,
      regardless of their order in the list. This allows us to parse cross-listed courses
      while distinguishing between different semesters of the same course.
    """
    # Build a cleaned list:
    # - str(c): ensure each element is a string
    # - .strip(): remove surrounding whitespace
    # - if c and str(c).strip(): skip Nones/empties
    cleaned = [str(c).strip() for c in codes if c and str(c).strip()]
    # Sort for order-independence (['B','A'] -> ['A','B'])
    cleaned_sorted = sorted(cleaned)
    # Join with '|' to create a single canonical ID, e.g., 'AMST-200|EDST-200|SOCI-200|2223F'
    return "|".join(cleaned_sorted + [str(semester).strip()])

def get_sim(d):
    """
    Given an edge attribute dictionary 'd', return the similarity value as a float.
    Similarity may be stored directly as 'similarity' or derived from 'weight'.
    """
    if "similarity" in d and d["similarity"] is not None:
        return float(d["similarity"])
    if "weight" in d and d["weight"] is not None:
        # If 'weight' is actually a distance, convert to similarity
        return 1.0 - float(d["weight"])
    return None  # If no similarity info is found

# Regular expression to find course codes like "ECON-111" or "PSYC-498D"
pat = re.compile(r"[A-Za-z]{2,5}-\d{2,4}[A-Za-z]?")

def parse_courses_from_cell(s):
    """
    Parse a cell containing course codes and return a list of course codes.
    First try: evaluate it as a Python list.
    Fallback: extract codes using regex.
    """
    try:
        # Try to interpret the string as a Python literal (e.g., list)
        lst = ast.literal_eval(s)
        if isinstance(lst, list):
            # Standardize all strings: strip spaces, uppercase
            return [str(x).strip().upper() for x in lst if isinstance(x, str)]
    except Exception:
        pass  # If that fails, continue to regex extraction
    # Fallback: use regex to find all codes in the string
    return [m.group(0).upper() for m in pat.finditer(str(s))]


# -----------------------------
# Read JSON
# -----------------------------
with open(INPUT_JSON, "r") as f:
    data = json.load(f)
print(f"Number of courses: {len(data)}")

# -----------------------------
# Build unfiltered graph for distance calculations
# -----------------------------
print("Building unfiltered graph for distance calculations...")
edges_acc_unfiltered = {}
node_codes = {}

# Iterate over each entry (row) in the input data.
for entry in data:
    # Extract the "source" course code list; if missing, use [].
    src_codes = entry.get("course_codes", [])
    # Extract the source semester; if missing, use empty string.
    src_semester = entry.get("semester", "")

    if not src_codes:
        continue

    # Create a canonical node ID for the source node.
    u = canon_node_id(src_codes, src_semester)

    # Ensure the node is recorded in node_codes.
    node_codes.setdefault(u, (tuple(sorted(src_codes)), src_semester))

    # Extract the list of comparisons from this source entry.
    compared = entry.get("compared_courses", []) or []

    # Loop over all compared items for this source node.
    for comp in compared:
        # Destination (neighbor) course codes for this comparison.
        dst_codes = comp.get("course_codes", [])
        # Destination semester for this comparison.
        dst_semester = comp.get("semester", "")

        if not dst_codes:
            continue

        # Canonical node ID for the neighbor.
        v = canon_node_id(dst_codes, dst_semester)

        # Make sure the neighbor node is recorded with its readable codes and semester.
        node_codes.setdefault(v, (tuple(sorted(dst_codes)), dst_semester))

        # Extract similarity score; could be absent -> None.
        sim = comp.get("similarity_score", None)
        # If similarity is missing, skip this pair.
        if sim is None:
            continue

        # Store the neighbor and similarity (cast to float for safety).
        # Avoid self-loops (u -> u).
        if u == v:
            continue
        # Sort the two node IDs so (u, v) and (v, u) become the same edge key.
        a, b = sorted((u, v))

        # If we already saw an edge for (a, b), keep the maximum similarity encountered.
        prev = edges_acc_unfiltered.get((a, b))
        edges_acc_unfiltered[(a, b)] = sim if prev is None else max(prev, sim)

# Create unfiltered graph
G_unfiltered = nx.Graph()

# Add all nodes first.
for node, (codes, semester) in node_codes.items():
    G_unfiltered.add_node(node, codes="|".join(codes), semester=semester)

# Add all edges (no filtering)
for (u, v), sim in edges_acc_unfiltered.items():
    G_unfiltered.add_edge(u, v, similarity=sim, weight=(1.0 - sim))

print(f"Unfiltered graph: {G_unfiltered.number_of_nodes()} nodes, {G_unfiltered.number_of_edges()} edges")
# Parse the entire JSON file into a Python object.
# We expect a list of dicts, each roughly like:
# [
#     {
#         "course_codes": [
#             "EDST-203",
#             "AMST-203",
#             "SOCI-203"
#         ],
#         "semester": "2223F",
#         "compared_courses": [
#             {
#                 "course_codes": [
#                     "AMST-205"
#                 ],
#                 "semester": "2223F",
#                 "similarity_score": 0.757240453712485
#             },

# ---------- gather similarities ----------
# We will aggregate edges in a dictionary before building the graph.
# Key: a tuple (u, v) with u < v (sorted order) so each undirected edge is unique.
# Value: the maximum similarity observed between u and v across all entries.
edges_acc = {}

# We'll also track the original list of course codes and semester for each node in a dictionary,
# so we can save them as a readable attribute on the node.
# Key: node_id (canonical string), Value: a tuple of (sorted course codes, semester).
node_codes = {}

# Iterate over each entry (row) in the input data.
for entry in data:
      # Extract the "source" course code list; if missing, use [].
      src_codes = entry.get("course_codes", [])

      # Extract the source semester; if missing, use empty string.
      src_semester = entry.get("semester", "")

      if not src_codes:
            continue

      # Create a canonical node ID for the source node.
      u = canon_node_id(src_codes, src_semester)

      # Ensure the node is recorded in node_codes.
      # setdefault inserts the key with the provided default if absent; otherwise it leaves it unchanged.
      node_codes.setdefault(u, (tuple(sorted(src_codes)), src_semester))

      # Extract the list of comparisons from this source entry.
      # The "or []" ensures that if the value is None, we still get an empty list.
      compared = entry.get("compared_courses", []) or []

      # We'll optionally keep only top-K similar neighbors per *source node*.
      # To do that, we first gather all (neighbor, similarity) pairs locally.
      pairs = []

      # Loop over all compared items for this source node.
      for comp in compared:
            # Destination (neighbor) course codes for this comparison.
            dst_codes = comp.get("course_codes", [])

            # Destination semester for this comparison.
            dst_semester = comp.get("semester", "")

            if not dst_codes:
                  continue

            # Canonical node ID for the neighbor.
            v = canon_node_id(dst_codes, dst_semester)

            # Make sure the neighbor node is recorded with its readable codes and semester.
            node_codes.setdefault(v, (tuple(sorted(dst_codes)), dst_semester))

            # Extract similarity score; could be absent -> None.
            sim = comp.get("similarity_score", None)
            if sim is None:
                  continue

            # If a minimum similarity threshold is set, drop weak pairs.
            if MIN_SIM is not None and sim < MIN_SIM:
                  continue

            # Store the neighbor and similarity (cast to float for safety).
            pairs.append((v, float(sim)))

      # If we are keeping only the top-K neighbors (by similarity) for this source node:
      if KEEP_TOP_K is not None and len(pairs) > KEEP_TOP_K:
            # Sort pairs descending by similarity: highest similarity first.
            pairs.sort(key=lambda t: t[1], reverse=True)
            # Truncate to the first KEEP_TOP_K pairs.
            pairs = pairs[:KEEP_TOP_K]

      # Add this source node's pairs into the global accumulator.
      # We treat the graph as undirected, so we sort (u, v) to have a unique key.
      for v, sim in pairs:
            # Avoid self-loops (u -> u).
            if u == v:
                  continue
            # Sort the two node IDs so (u, v) and (v, u) become the same edge key.
            a, b = sorted((u, v))

            # If we already saw an edge for (a, b), keep the maximum similarity encountered.
            # (Later we'll convert similarity to a "distance" weight via 1 - similarity,
            #  and max similarity -> min distance.)
            prev = edges_acc.get((a, b))
            edges_acc[(a, b)] = sim if prev is None else max(prev, sim)

# -----------------------------
# Build graph
# -----------------------------
# Create an empty undirected NetworkX graph.
G = nx.Graph()

# Add all nodes first. Each node gets 'codes' and 'semester' attributes that store the
# human-readable course code list joined by '|' and the semester.
for node, (codes, semester) in node_codes.items():
    G.add_node(node, codes="|".join(codes), semester=semester)

# Add edges with attributes:
# - 'similarity': the similarity score we kept
# - 'weight': a distance for many algorithms = 1 - similarity
for (u, v), sim in edges_acc.items():
    G.add_edge(u, v, similarity=sim, weight=(1.0 - sim))  # weight is often treated as distance.

# Print a quick summary of the graph size to the console.
print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# -----------------------------
# Save graph
# -----------------------------
# Build output filenames from the prefix.
# gexf_path = f"{OUTPUT_PREFIX}.gexf"       # GEXF is a format Gephi can read.
# graphml_path = f"{OUTPUT_PREFIX}.graphml" # GraphML is an XML-based graph format.

# Write the graph to GEXF.
# nx.write_gexf(G, gexf_path)

# Write the graph to GraphML. GraphML is stricter about attribute types;
# we've stored only simple strings/numbers, so this should be fine.
# nx.write_graphml(G, graphml_path)

# Let the user know where files were saved.
# print("Saved:")
# print(" -", gexf_path)
# print(" -", graphml_path)

# # -----------------------------
# # Sanity Check
# # -----------------------------
# print("\n" + "="*50)
# print("SANITY CHECK")
# print("="*50)

# # --- set these ---
# TOL = 1e-9  # Tolerance for floating-point comparisons when checking weights (handles tiny rounding errors).

# # ---------- Rebuild expected node set ----------
# expected_nodes = set()  # Create an empty set to store all unique node IDs expected from the JSON
# for entry in data:
#     src_codes = entry.get("course_codes", [])
#     src_semester = entry.get("semester", "")
#     u = canon_node_id(src_codes, src_semester)  # Canonical ID for the "source" course
#     if u:
#         expected_nodes.add(u)                         # Add to set of expected nodes
#     for comp in entry.get("compared_courses", []) or []:  # Loop over all comparisons for this source
#         dst_codes = comp.get("course_codes", [])
#         dst_semester = comp.get("semester", "")
#         v = canon_node_id(dst_codes, dst_semester)   # Canonical ID for "target" course
#         if v:
#             expected_nodes.add(v)                      # Add target node to set too

# print(f"JSON unique nodes: {len(expected_nodes)}")  # How many unique nodes we found from JSON
# print(f"Graph nodes:       {G.number_of_nodes()}")   # How many nodes are actually in the graph

# # Compare node sets
# extra_in_graph  = set(G.nodes()) - expected_nodes     # Nodes in graph but not in JSON
# missing_in_graph = expected_nodes - set(G.nodes())    # Nodes in JSON but missing from graph

# print(f"Nodes missing in graph: {len(missing_in_graph)}")
# print(f"Nodes present only in graph: {len(extra_in_graph)}")
# if missing_in_graph:
#     print("  e.g.", list(sorted(missing_in_graph))[:5])
# if extra_in_graph:
#     print("  e.g.", list(sorted(extra_in_graph))[:5])

# # ---------- Rebuild expected edge set ----------
# # Apply the SAME rules you used: undirected, de-duplicate by max similarity,
# # optional MIN_SIM and per-node KEEP_TOP_K.

# # First collect per-source neighbor lists if you need top-k
# per_source = {}  # Dictionary: source_node -> list of (neighbor, similarity) pairs
# for entry in data:
#     src_codes = entry.get("course_codes", [])
#     src_semester = entry.get("semester", "")
#     u = canon_node_id(src_codes, src_semester)
#     if not u: 
#         continue
#     pairs = []
#     for comp in entry.get("compared_courses", []) or []:
#         dst_codes = comp.get("course_codes", [])
#         dst_semester = comp.get("semester", "")
#         v = canon_node_id(dst_codes, dst_semester)
#         sim = comp.get("similarity_score", None)
#         if not v or sim is None:
#             continue
#         sim = float(sim)
#         if MIN_SIM is not None and sim < MIN_SIM:  # Drop if below threshold
#             continue
#         if u == v:  # Skip self-loops
#             continue
#         pairs.append((v, sim))
#     # Keep only top-K most similar if required
#     if KEEP_TOP_K is not None and len(pairs) > KEEP_TOP_K:
#         pairs.sort(key=lambda t: t[1], reverse=True)  # Sort by similarity descending
#         pairs = pairs[:KEEP_TOP_K]
#     per_source.setdefault(u, []).extend(pairs)

# # Merge to undirected by keeping MAX similarity (=> min distance)
# expected_edges = {}  # Key: (a,b) sorted tuple; Value: max similarity
# for u, pairs in per_source.items():
#     for v, sim in pairs:
#         a, b = sorted((u, v))  # Sort to enforce undirected uniqueness
#         prev = expected_edges.get((a,b))
#         expected_edges[(a,b)] = sim if prev is None else max(prev, sim)

# print(f"Expected undirected edges: {len(expected_edges)}")
# print(f"Graph edges:               {G.number_of_edges()}")

# graph_edge_set = set(tuple(sorted(e)) for e in G.edges())  # All edges from the graph
# expected_edge_set = set(expected_edges.keys())             # All expected edges from JSON

# missing_edges = expected_edge_set - graph_edge_set         # Edges in JSON but not in graph
# extra_edges   = graph_edge_set - expected_edge_set         # Edges in graph but not in JSON

# print(f"Edges missing in graph: {len(missing_edges)}")
# print(f"Edges present only in graph: {len(extra_edges)}")
# if missing_edges:
#     print("  e.g.", list(sorted(missing_edges))[:5])
# if extra_edges:
#     print("  e.g.", list(sorted(extra_edges))[:5])

# # ---------- Check weights (distance = 1 - similarity) ----------
# bad_weights = []
# for (a,b), exp_sim in expected_edges.items():
#     if not G.has_edge(a,b):
#         continue
#     d = G[a][b]  # This is the edge attribute dictionary
#     # Try to get the stored similarity
#     g_sim = d.get("similarity")
#     if g_sim is None and "weight" in d:  # If similarity missing, reconstruct from weight
#         g_sim = 1.0 - float(d["weight"])
#     if g_sim is None:
#         bad_weights.append((a,b,"missing weight/similarity"))
#         continue
#     # Compare expected similarity vs actual; flag if difference > tolerance
#     if abs(float(g_sim) - float(exp_sim)) > TOL:
#         bad_weights.append((a,b,exp_sim,g_sim))

# print(f"Edges with mismatched similarity/weight: {len(bad_weights)}")
# if bad_weights[:5]:
#     print("  e.g.", bad_weights[:5])

# # ---------- Quick per-node spot checks ----------
# def show_neighbors(node, k=10):
#     """Print top-k nearest neighbors by similarity (descending) from the graph."""
#     if node not in G:
#         print("Node not in graph")
#         return
#     nbrs = []
#     for v in G.neighbors(node):   # Iterate over all connected neighbors
#         d = G[node][v]            # Get edge attributes
#         sim = d.get("similarity") # Try to read similarity directly
#         if sim is None and "weight" in d:
#             sim = 1.0 - float(d["weight"])  # Convert distance to similarity if needed
#         nbrs.append((v, float(sim)))
#     nbrs.sort(key=lambda x: x[1], reverse=True)  # Sort neighbors by similarity descending
#     for v, s in nbrs[:k]:  # Show only the top k
#         print(f"{node} -- {v} : similarity={s:.6f}  distance={1.0 - s:.6f}")

# print("\nSanity check complete!")
# print("="*50)
# print("="*50)


# # -----------------------------
# # Example courses
# # -----------------------------
# #show_neighbors("GEOL-251")                       # if you used single-code nodes
# show_neighbors("AMST-111", k=5)                     # if you used single-code nodes
# #show_neighbors("AMST-200|EDST-200|SOCI-200")     # if you used grouped nodes


# -----------------------------
# Student Analysis
# -----------------------------
# Load student data
df = pd.read_csv(OUTPUT_DATA)

# Get semester columns (columns with format like "0910F" - 4 digits + capital letter)
semester_pattern = re.compile(r'^\d{4}[A-Z]$')
semester_columns = [col for col in df.columns if semester_pattern.match(col)]

# Loop over every student
rows = [] 

for idx, row in df.iterrows():
    mapped_nodes, missing = [], []  # Separate lists for found and not found courses
    
    # Process each semester column
    for semester_col in semester_columns:
        semester = semester_col  # e.g., "2526F", "2526S"
        courses_in_semester = parse_courses_from_cell(row[semester_col])
        
        for course_code in courses_in_semester:
            # Use canon_node_id to get the exact node ID for this course+semester combination
            node_id = canon_node_id([course_code], semester)
            
            # Check if this node exists in the graph
            if node_id in G:
                mapped_nodes.append(node_id)
            else:
                missing.append(f"{course_code} ({semester})")

    # Remove duplicates and sort alphabetically
    mapped_nodes = sorted(set(mapped_nodes))

    # Create a subgraph containing only the student's courses (from unfiltered graph for distances)
    subG_unfiltered = G_unfiltered.subgraph(mapped_nodes).copy()
    
    # Calculate average and max distances between courses using unfiltered graph
    distances = []
    for i, node1 in enumerate(mapped_nodes):
        for j, node2 in enumerate(mapped_nodes):
            if i < j:  # Only check each pair once
                if subG_unfiltered.has_edge(node1, node2):
                    # Get similarity and convert to distance
                    sim = subG_unfiltered[node1][node2].get("similarity")
                    if sim is None and "weight" in subG_unfiltered[node1][node2]:
                        sim = 1.0 - float(subG_unfiltered[node1][node2]["weight"])
                    if sim is not None:
                        distances.append(1.0 - float(sim))
                else:
                    # If no edge exists in unfiltered graph, assume max distance (similarity = 0)
                    distances.append(1.0)
    
    avg_distance = np.mean(distances) if distances else 1.0
    max_distance = np.max(distances) if distances else 1.0
    
    # Create a subgraph containing only the student's courses (from filtered graph for components)
    subG = G.subgraph(mapped_nodes).copy()
    
    # Get connected components (sets of nodes connected to each other)
    comps = list(nx.connected_components(subG))

    # Sort components by size (largest first)
    comps_sorted = sorted(comps, key=lambda s: len(s), reverse=True)
    # Convert each component to a sorted list of strings for saving in CSV
    comps_lists  = [sorted(map(str, comp)) for comp in comps_sorted]

    # List of component sizes
    comp_sizes = [len(cset) for cset in comps_sorted]

    # Add this student's summary info to rows
    rows.append({
        "student_index": idx,                        # Which student (by index in CSV)
        "n_courses_listed": len(mapped_nodes) + len(missing),  # Total courses attempted
        "n_nodes_mapped": len(mapped_nodes),         # How many matched to graph nodes
        "n_unmapped": len(missing),                  # How many didn't match
        "n_components": len(comp_sizes),             # How many connected components
        "largest_component": (comp_sizes[0] if comp_sizes else 0),  # Size of largest
        "avg_distance": avg_distance,                # Average distance between all course pairs
        "max_distance": max_distance,                # Maximum distance between any course pair
        "component_sizes_sorted": comp_sizes[:10],   # Preview first 10 sizes
        "components_json": json.dumps(comps_lists),  # Save full list of components as JSON
        "unmapped_example": ", ".join(missing[:6]),  # First few unmapped courses (if any)
    })

# Convert rows list into a DataFrame
analysis_df = pd.DataFrame(rows)

# Merge with original data to preserve all original columns and rows
# Use student_index to match rows (student_index is 0-based, so we need to adjust)
# analysis_df['student_index'] = analysis_df['student_index'] - 1  # Convert back to 0-based index

# Merge the analysis results with the original dataframe
result_df = df.merge(analysis_df, left_index=True, right_on='student_index', how='left')
result_df = result_df.drop('student_index', axis=1) # Drop the redundant student_index column

# Reorder columns: original columns (except semester), new analysis columns, semester columns (sorted)
# Get original columns excluding semester columns
original_cols = [col for col in df.columns if col not in semester_columns]

# Get new analysis columns (columns that weren't in the original dataframe)
new_analysis_cols = [col for col in result_df.columns if col not in df.columns]

# Sort semester columns: first by year (first 4 chars), then by term (F, J, S)
def sort_semester_key(semester):
    year = semester[:4]  # First 4 characters (e.g., "0910")
    term = semester[4]   # Last character (e.g., "F", "J", "S")
    term_order = {"F": 0, "J": 1, "S": 2}  # F comes first, then J, then S
    return (year, term_order.get(term, 3))  # Unknown terms go last

sorted_semester_cols = sorted(semester_columns, key=sort_semester_key)

# Combine columns in desired order
final_column_order = original_cols + new_analysis_cols + sorted_semester_cols

# Reorder the dataframe
result_df = result_df[final_column_order]

result_df.to_csv(OUTPUT_DATA, index=False)
print(f"Saved: {OUTPUT_DATA}")

# Show the first 10 rows in the console
print("\nFirst 10 students:")
print(result_df.head(10))

print(f"\nAnalysis complete!")
print(f"Total students analyzed: {len(result_df)}")
print(f"Average courses per student: {result_df['n_courses_listed'].mean():.1f}")
print(f"Average components per student: {result_df['n_components'].mean():.1f}")
print(f"Average largest component size: {result_df['largest_component'].mean():.1f}")

