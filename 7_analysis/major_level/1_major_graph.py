import json, os
import re
import ast
import pandas as pd
import networkx as nx
import numpy as np

# -----------------------------
# Config
# -----------------------------
filedate = os.getenv('FILEDATE', '20250813')
OUTPUT_GRAPH_UNFIL = os.getenv('OUTPUT_GRAPH_UNFIL', '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/output/6_scores/graph_all_unfiltered.gexf')
OUTPUT_MAJOR_DATA = os.getenv('OUTPUT_MAJOR_DATA', f'/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/5_scores/major_scores_panel.csv')

# Convert environment variables to proper types
keep_top_k_str = os.getenv('KEEP_TOP_K', 'None')
KEEP_TOP_K = None if keep_top_k_str == 'None' else int(keep_top_k_str)  # If set to an integer (e.g., 20), keep only the top-K neighbors per node.
MIN_SIM = float(os.getenv('MIN_SIM', '0.75'))     # Minimum similarity threshold for keeping edges

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

# -----------------------------
# Load graph
# -----------------------------
G = nx.read_gexf(OUTPUT_GRAPH_UNFIL)

# Create a lookup dict for course codes
code_to_node = {}
semesters = set()
majors = set()

for node_id in G.nodes():
    node_codes = G.nodes[node_id]['codes'].split('|')
    node_semester = G.nodes[node_id]['semester']
    semesters.add(node_semester)
    for code in node_codes:
        code_to_node[(code, node_semester)] = node_id
        majors.add(code[:4])  # first 4 chars = major

# Now you have:
# semesters = {'2324S', '2324F', ...}
# majors = {'EDST', 'MATH', 'HIST', ...}

# -----------------------------
# Create graph for each semester-major
# -----------------------------
rows = []

for semester in sorted(semesters):
    majors_in_sem = []

    for major in sorted(majors):
        mapped_nodes, missing = [], []
        majors_in_sem.append(major)

        # Collect all nodes that belong to this semester-major
        for (code, sem), node_id in code_to_node.items():
            if sem == semester and code.startswith(major):
                mapped_nodes.append(node_id)

        if not mapped_nodes:
            missing.append(f"{major} ({semester})")

        # Deduplicate and sort
        mapped_nodes = sorted(set(mapped_nodes))

        # Create a subgraph containing only the major-semester's courses (from unfiltered graph for distances)
        subG = G.subgraph(mapped_nodes).copy()
        
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
            "n_courses_listed": len(mapped_nodes) + len(missing),  # Total courses attempted
            "n_nodes_mapped": len(mapped_nodes),         # How many matched to graph nodes
            "n_unmapped": len(missing),                  # How many didn't match
            "n_components": len(comp_sizes),             # How many connected components
            "largest_component": (comp_sizes[0] if comp_sizes else 0),  # Size of largest
            "avg_distance": avg_distance,                # Average distance between all course pairs
            "max_distance": max_distance,                # Maximum distance between any course pair
            "component_sizes_sorted": comp_sizes[:10],   # Preview first 10 sizes
            "unmapped_example": ", ".join(missing),      # Unmapped courses (if any)
        })
        # end of loop through majors #
    
    # ---- Add "ALL majors" row for this semester ----
    all_nodes = [node_id for (code, sem), node_id in code_to_node.items() if sem == semester]
    all_nodes = sorted(set(all_nodes))

    subG_all = G.subgraph(all_nodes).copy()
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
        "n_courses_listed": len(all_nodes),
        "n_nodes_mapped": len(all_nodes),
        "n_unmapped": 0,
        "n_components": len(comp_sizes),
        "largest_component": (comp_sizes[0] if comp_sizes else 0),
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
            "n_courses_listed": 0,
            "n_nodes_mapped": 0,
            "n_unmapped": 0,
            "n_components": 0,
            "largest_component": 0,
            "avg_distance": 1.0,
            "max_distance": 1.0,
            "component_sizes_sorted": [],
            "unmapped_example": "",
        })
        continue
    
    # Create a subgraph containing all the major's courses across all semesters
    subG_major = G.subgraph(major_nodes).copy()
    
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
        "n_majors": len(semesters_with_major),  # Number of semesters this major appears in
        "n_courses_listed": len(major_nodes),
        "n_nodes_mapped": len(major_nodes),
        "n_unmapped": 0,  # No unmapped since we're working with existing nodes
        "n_components": len(comp_sizes),
        "largest_component": (comp_sizes[0] if comp_sizes else 0),
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
print(analysis_df.head(10))

print(f"\nAnalysis complete!")

