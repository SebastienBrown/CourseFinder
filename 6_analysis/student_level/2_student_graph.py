import json, os
import re
import ast
import pandas as pd
import networkx as nx
import numpy as np

# -----------------------------
# Config
# -----------------------------
filedate = os.environ['FILEDATE']
INPUT_JSON = os.environ['INPUT_JSON']
OUTPUT_STUDENT_DATA = os.environ['OUTPUT_STUDENT_DATA']

# Convert environment variables to proper types
keep_top_k_str = os.environ['KEEP_TOP_K']
KEEP_TOP_K = None if keep_top_k_str == 'None' else int(keep_top_k_str)  # If set to an integer (e.g., 20), keep only the top-K neighbors per node.
MIN_SIM = float(os.environ['MIN_SIM'])     # Minimum similarity threshold for keeping edges

# -----------------------------
# Functions
# -----------------------------
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

# -----------------------------
# Read JSON
# -----------------------------
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
    if isinstance(src_codes, str):
        src_codes = [src_codes]
    
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
        if isinstance(dst_codes, str):
            dst_codes = [dst_codes]

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
G = nx.Graph()

# Add all nodes first.
for node, (codes, semester) in node_codes.items():
    G.add_node(node, codes="|".join(codes), semester=semester)

# Add all edges (no filtering)
for (u, v), sim in edges_acc_unfiltered.items():
    G.add_edge(u, v, similarity=sim, weight=(1.0 - sim))

print(f"Unfiltered graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# -----------------------------
# Load graph
# -----------------------------
# G = nx.read_gexf(OUTPUT_GRAPH_UNFIL)

# Create a lookup dict for course codes
code_to_node = {}
for node_id in G.nodes():
    node_codes = G.nodes[node_id]['codes'].split('|')
    node_semester = G.nodes[node_id]['semester']
    for code in node_codes:
        code_to_node[(code, node_semester)] = node_id

# -----------------------------
# Student Analysis
# -----------------------------
# Load student data
df = pd.read_csv(OUTPUT_STUDENT_DATA)

# Get semester columns (columns with format like "0910F" - 4 digits + capital letter)
semester_pattern = re.compile(r'^\d{4}[A-Z]$')
semester_columns = [col for col in df.columns if semester_pattern.match(col)]

# Loop over every student
rows = [] 

for idx, row in df.iterrows():
    mapped_nodes, missing = [], []  # Separate lists for found and not found courses
    
    # -----------------------------
    # Process each semester column
    # -----------------------------
    for semester_col in semester_columns:
        semester = semester_col  # e.g., "2526F", "2526S"
        courses_in_semester = parse_courses_from_cell(row[semester_col])
        
        for course_code in courses_in_semester:
            lookup_key = (course_code, semester)
            if lookup_key in code_to_node:
                mapped_nodes.append(code_to_node[lookup_key])
            else:
                missing.append(f"{course_code} ({semester})")

    # Remove duplicates and sort alphabetically
    mapped_nodes = sorted(set(mapped_nodes))

    # Create a subgraph containing only the student's courses (from unfiltered graph for distances)
    subG = G.subgraph(mapped_nodes).copy()

    # -----------------------------
    # Breadth and depth scores from unfiltered graph
    # -----------------------------
    # Count cross-listed
    n_crosslisted = sum(1 for node_id in mapped_nodes if '|' in subG.nodes[node_id]['codes'])
    
    # Calculate average and max distances between courses using unfiltered graph
    distances = []
    for i, node1 in enumerate(mapped_nodes):
        for j, node2 in enumerate(mapped_nodes):
            if i < j:  # Only check each pair once
                if subG.has_edge(node1, node2):
                    # Get similarity and convert to distance
                    sim = subG[node1][node2].get("similarity")
                    if sim is None and "weight" in subG[node1][node2]:
                        sim = 1.0 - float(subG[node1][node2]["weight"])
                    if sim is not None:
                        distances.append(1.0 - float(sim))
                else:
                    # If no edge exists in unfiltered graph, assume max distance (similarity = 0)
                    distances.append(1.0)
    
    avg_distance = np.mean(distances) if distances else 1.0
    max_distance = np.max(distances) if distances else 1.0

    # Rao's quadratic entropy (uniform p_i) = ((N-1)/N) * mean(pairwise distances)
    if len(mapped_nodes) <= 1 or not distances:
        rao_q = 0.0
    else:
        rao_q = ((len(mapped_nodes) - 1) / len(mapped_nodes)) * float(np.mean(distances)) 
    
    # Eccentricity scores - Weighted radius/diameter on the largest component (NaN/NaN if empty; 0/0 if singleton)
    n = subG.number_of_nodes()
    if n == 0:
        ecc_r, ecc_d = float("nan"), float("nan")
    else:
        Hc_nodes = max(nx.connected_components(subG), key=len)
        Hc = subG.subgraph(Hc_nodes).copy()
        if Hc.number_of_nodes() == 1:
            ecc_r, ecc_d = 0.0, 0.0
        else:
            # try:
                ecc = nx.eccentricity(Hc, weight="weight")
                ecc_r, ecc_d = float(min(ecc.values())), float(max(ecc.values()))
            # except Exception:
            #     lengths = dict(nx.all_pairs_dijkstra_path_length(Hc, weight="weight"))
            #     ecc_vals = [max(d.values()) for d in lengths.values()]
            #     ecc_r, ecc_d = float(min(ecc_vals)), float(max(ecc_vals))

    # -----------------------------
    # Filter by minimum similarity
    # -----------------------------
    for u, v, d in list(subG.edges(data=True)):
        if d.get("similarity", 0) < MIN_SIM:
            subG.remove_edge(u, v)

    # -----------------------------
    # Connected components
    # -----------------------------
    # Get connected components (sets of nodes connected to each other)
    comps = list(nx.connected_components(subG))

    # Sort components by size (largest first)
    comps_sorted = sorted(comps, key=lambda s: len(s), reverse=True)

    # Convert each component to a sorted list of strings for saving in CSV
    comps_lists  = [sorted(map(str, comp)) for comp in comps_sorted]
    
    # List of component sizes
    comp_sizes = [len(cset) for cset in comps_sorted]

    # -----------------------------
    # Depth scores
    # -----------------------------
    # Mean local clustering coefficient weighted by similarity (NaN if empty)
    if subG.number_of_nodes() == 0:
        avg_clust = float("nan")
    else:
        cdict = nx.clustering(subG, weight="similarity")
        avg_clust = float(np.mean(list(cdict.values()))) if cdict else float("nan")
    
    # Progression depth
    if subG.number_of_nodes() == 0:
        prog_depth = 0
    else:
        # Get the largest connected component
        Hc_nodes = max(nx.connected_components(subG), key=len)
        Hc = subG.subgraph(Hc_nodes).copy()
        if Hc.number_of_nodes() == 1:
            prog_depth = 0
        else:
            # try:
                prog_depth = int(nx.diameter(Hc))
            # except Exception:
            #     lengths = dict(nx.all_pairs_shortest_path_length(Hc))
            #     prog_depth = int(max(max(d.values()) for d in lengths.values()))

    # -----------------------------
    # Append all metrics
    # -----------------------------
    rows.append({
        "student_index": idx,                        # Which student (by order in CSV)
        "StudentID": row.get("StudentID", idx),

        "n_courses": len(mapped_nodes) + len(missing),  # Total courses attempted
        "n_crosslisted": n_crosslisted,              # How many were cross-listed

        "n_courses_mapped": len(mapped_nodes),         # How many matched to graph nodes
        "n_courses_unmapped": len(missing),                  # How many didn't match

        "n_components": len(comp_sizes),             # How many connected components
        "largest_component": (comp_sizes[0] if comp_sizes else 0),  # Size of largest
        "component_sizes_sorted": comp_sizes[:10],   # Preview first 10 sizes
        "unmapped_example": ", ".join(missing),      # Unmapped courses (if any)

        "avg_distance": avg_distance,                # Average distance between all course pairs
        "max_distance": max_distance,                # Maximum distance between any course pair

        "rao_q_uniform": rao_q,
        "ecc_radius_weighted": ecc_r,
        "ecc_diameter_weighted": ecc_d,
        
        "avg_clustering_similarity": avg_clust,
        "progression_depth_hops": prog_depth, 
    })

# Convert rows list into a DataFrame
analysis_df = pd.DataFrame(rows)

# Merge the analysis results with the original dataframe
result_df = df.merge(analysis_df, left_index=True, right_on='student_index', how='left')
    # left_index=True uses row index values (order in CSV)
result_df = result_df.drop('student_index', axis=1) # Drop the redundant student_index column

# -----------------------------
# Organize and export csv
# -----------------------------
# Reorder columns: original columns (except semester), new analysis columns, semester columns (sorted)
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

# Sort by student ID
result_df = result_df.sort_values(by="StudentID", ascending=True)

result_df.to_csv(OUTPUT_STUDENT_DATA, index=False)
print(f"Saved: {OUTPUT_STUDENT_DATA}")

# Show the first 10 rows in the console
print("\nFirst 10 students:")
print(result_df.head(10))

print(f"\nAnalysis complete!")
print(f"Total students analyzed: {len(result_df)}")
print(f"Average courses per student: {result_df['n_courses_listed'].mean():.1f}")
print(f"Average components per student: {result_df['n_components'].mean():.1f}")
print(f"Average largest component size: {result_df['largest_component'].mean():.1f}")

