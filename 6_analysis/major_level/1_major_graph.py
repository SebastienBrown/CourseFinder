import json, os
import pandas as pd
import networkx as nx
import numpy as np
from utils import canon_node_id, normalize_codes, dept_replacements

# -----------------------------
# Config
# -----------------------------
INPUT_JSON = os.getenv('INPUT_JSON', '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/3_similarity/gpt_off_the_shelf/output_similarity_all.json')
# OUTPUT_GRAPH_UNFIL = os.getenv('OUTPUT_GRAPH_UNFIL', '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/output/6_scores/graph_all_unfiltered.gexf')
OUTPUT_MAJOR_DATA = os.getenv('OUTPUT_MAJOR_DATA', f'/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/5_scores/major_scores_panel.csv')

# Convert environment variables to proper types
keep_top_k_str = os.getenv('KEEP_TOP_K', 'None')
KEEP_TOP_K = None if keep_top_k_str == 'None' else int(keep_top_k_str)  # If set to an integer (e.g., 20), keep only the top-K neighbors per node.
MIN_SIM = float(os.getenv('MIN_SIM', '0.75'))     # Minimum similarity threshold for keeping edges

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

    # Normalize major codes
    src_codes = normalize_codes(src_codes)
    
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

        # Normalize major codes
        dst_codes = normalize_codes(dst_codes)

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
    G.add_node(node, codes=codes, semester=semester) #codes="|".join(codes)

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
semesters = set()  # semesters = {'2324S', '2324F', ...}
majors = set()     # majors = {'EDST', 'MATH', 'HIST', ...}

for node_id in G.nodes():
    node_codes = G.nodes[node_id]['codes']
    node_semester = G.nodes[node_id]['semester']
    semesters.add(node_semester)
    for code in node_codes:
        major = code.split("-")[0]
        if len(major) != 4:
            print(f"Major: {code}, Node ID: {node_id}, Attributes: {G.nodes[node_id]}")  # <-- debug line
        code_to_node[(code, node_semester)] = node_id
        majors.add(major)

print(majors)

# -----------------------------
# Create graph for each semester-major
# -----------------------------
rows = []

for semester in sorted(semesters):
    majors_in_sem = []

    for major in sorted(majors):
        mapped_nodes = []
        majors_in_sem.append(major)

        # Collect all nodes that belong to this semester-major
        for (code, sem), node_id in code_to_node.items():
            if sem == semester and code.startswith(major):
                mapped_nodes.append(node_id)

        # Deduplicate and sort
        mapped_nodes = sorted(set(mapped_nodes))

        # Create a subgraph containing only the major-semester's courses (from unfiltered graph for distances)
        subG = G.subgraph(mapped_nodes).copy()

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
        
        avg_distance = np.mean(distances) if distances else np.nan
        max_distance = np.max(distances) if distances else np.nan
        
        ###### Filter by minimum similarity ######
        for u, v, d in list(subG.edges(data=True)):
            if d.get("similarity", 0) < MIN_SIM:
                subG.remove_edge(u, v)
        ##########################################
        
        # Get connected components (sets of nodes connected to each other)
        comps = list(nx.connected_components(subG))

        # Sort components by size (largest first)
        comps_sorted = sorted(comps, key=lambda s: len(s), reverse=True)

        # Convert each component to a sorted list of strings for saving in CSV
        comps_lists  = [sorted(map(str, comp)) for comp in comps_sorted]

        # List of component sizes
        comp_sizes = [len(cset) for cset in comps_sorted]

        # Add this major-semester's summary info to rows
        rows.append({
            "semester": semester,
            "major": major,
            "n_majors": 1,
            "n_semesters": 1,
            "n_crosslisted": n_crosslisted,              # How many were cross-listed
            "n_courses_mapped": len(mapped_nodes),         # How many matched to graph nodes
            "n_components": len(comp_sizes),             # How many connected components
            "largest_component": (comp_sizes[0] if comp_sizes else np.nan),  # Size of largest
            "avg_distance": avg_distance,                # Average distance between all course pairs
            "max_distance": max_distance,                # Maximum distance between any course pair
            "component_sizes_sorted": comp_sizes[:10],   # Preview first 10 sizes
            "unmapped_example": "",      # Unmapped courses (if any)
        })
        # end of loop through majors #
    
    # ---- Add "ALL majors" row for this semester ----
    all_nodes = [node_id for (code, sem), node_id in code_to_node.items() if sem == semester]
    all_nodes = sorted(set(all_nodes))

    subG_all = G.subgraph(all_nodes).copy()

    # Count cross-listed
    n_crosslisted = sum(1 for node_id in all_nodes if '|' in subG_all.nodes[node_id]['codes'])

    # Distances
    distances = []
    for i, node1 in enumerate(all_nodes):
        for j, node2 in enumerate(all_nodes):
            if i < j:
                if subG_all.has_edge(node1, node2):
                    sim = subG_all[node1][node2].get("similarity")
                    if sim is None and "weight" in subG_all[node1][node2]:
                        sim = 1.0 - float(subG_all[node1][node2]["weight"])
                    if sim is not None:
                        distances.append(1.0 - float(sim))
                else:
                    distances.append(1.0)

    avg_distance = np.mean(distances) if distances else 1.0
    max_distance = np.max(distances) if distances else 1.0

    for u, v, d in list(subG_all.edges(data=True)):
        if d.get("similarity", 0) < MIN_SIM:
            subG_all.remove_edge(u, v)

    comps = list(nx.connected_components(subG_all))
    comps_sorted = sorted(comps, key=lambda s: len(s), reverse=True)
    comp_sizes = [len(cset) for cset in comps_sorted]

    rows.append({
        "semester": semester,
        "major": "ALL",
        "n_majors": len(majors_in_sem),
        "n_semesters": 1,
        "n_crosslisted": n_crosslisted,
        "n_courses_mapped": len(all_nodes),
        "n_components": len(comp_sizes),
        "largest_component": (comp_sizes[0] if comp_sizes else np.nan),
        "avg_distance": avg_distance,
        "max_distance": max_distance,
        "component_sizes_sorted": comp_sizes[:10],
        "unmapped_example": "",
    })
    # end of loop through semester #

# -----------------------------
# Create graph for major, all semesters
# -----------------------------
for major in sorted(majors):
    # Collect all nodes that belong to this major across all semesters
    major_nodes = [node_id for (code, sem), node_id in code_to_node.items() if code.startswith(major)]
    major_nodes = sorted(set(major_nodes))
    
    if not major_nodes:
        # If no nodes for this major, add a row with zeros
        rows.append({
            "semester": "ALL",
            "major": major,
            "n_majors": 1,
            "n_semesters": 0,
            "n_crosslisted": 0,
            "n_courses_mapped": 0,
            "n_components": 0,
            "largest_component": np.nan,
            "avg_distance": 1.0,
            "max_distance": 1.0,
            "component_sizes_sorted": [],
            "unmapped_example": "",
        })
        continue
    
    # Create a subgraph containing all the major's courses across all semesters
    subG_major = G.subgraph(major_nodes).copy()

    # Count cross-listed
    n_crosslisted = sum(1 for node_id in major_nodes if '|' in subG_major.nodes[node_id]['codes'])
    
    # Calculate average and max distances between courses using unfiltered graph
    distances = []
    for i, node1 in enumerate(major_nodes):
        for j, node2 in enumerate(major_nodes):
            if i < j:  # Only check each pair once
                if subG_major.has_edge(node1, node2):
                    # Get similarity and convert to distance
                    sim = subG_major[node1][node2].get("similarity")
                    if sim is None and "weight" in subG_major[node1][node2]:
                        sim = 1.0 - float(subG_major[node1][node2]["weight"])
                    if sim is not None:
                        distances.append(1.0 - float(sim))
                else:
                    # If no edge exists in unfiltered graph, assume max distance (similarity = 0)
                    distances.append(1.0)
    
    avg_distance = np.mean(distances) if distances else 1.0
    max_distance = np.max(distances) if distances else 1.0
    
    ###### Filter by minimum similarity ######
    for u, v, d in list(subG_major.edges(data=True)):
        if d.get("similarity", 0) < MIN_SIM:
            subG_major.remove_edge(u, v)
    ##########################################
    
    # Get connected components
    comps = list(nx.connected_components(subG_major))
    comps_sorted = sorted(comps, key=lambda s: len(s), reverse=True)
    comp_sizes = [len(cset) for cset in comps_sorted]
    
    # Count how many semesters this major appears in
    semesters_with_major = set()
    for (code, sem), node_id in code_to_node.items():
        if code.startswith(major):
            semesters_with_major.add(sem)
    
    rows.append({
        "semester": "ALL",
        "major": major,
        "n_majors": 1,
        "n_semesters": len(semesters_with_major),  # Number of semesters this major appears in
        "n_crosslisted": n_crosslisted,
        "n_courses_mapped": len(major_nodes),
        "n_components": len(comp_sizes),
        "largest_component": (comp_sizes[0] if comp_sizes else np.nan),
        "avg_distance": avg_distance,
        "max_distance": max_distance,
        "component_sizes_sorted": comp_sizes[:10],
        "unmapped_example": "",
    })

# Convert rows list into a DataFrame
analysis_df = pd.DataFrame(rows)

# -----------------------------
# Organize and export csv
# -----------------------------
analysis_df.to_csv(OUTPUT_MAJOR_DATA, index=False)
print(f"Saved: {OUTPUT_MAJOR_DATA}")

# Show the first 10 rows in the console
print("\nFirst 10 rows:")
print(analysis_df.head(10).to_string())

print(f"\nAnalysis complete!")

