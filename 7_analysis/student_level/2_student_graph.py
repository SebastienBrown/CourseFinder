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
OUTPUT_STUDENT_DATA = os.getenv('OUTPUT_STUDENT_DATA', f'/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/5_scores/student_scores_{filedate}.csv')

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
    
    # Process each semester column
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
        "unmapped_example": ", ".join(missing),      # Unmapped courses (if any)
    })

# Convert rows list into a DataFrame
analysis_df = pd.DataFrame(rows)

# Merge the analysis results with the original dataframe
result_df = df.merge(analysis_df, left_index=True, right_on='student_index', how='left')
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
result_df = result_df.sort_values(by="student_idx", ascending=True)

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

