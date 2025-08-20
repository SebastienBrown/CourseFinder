import json, os
import networkx as nx

# -----------------------------
# Config
# -----------------------------
filedate = os.getenv('FILEDATE', '20250813')
INPUT_JSON = os.getenv('INPUT_JSON', '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/3_similarity/gpt_off_the_shelf/output_similarity_all.json')
OUTPUT_GRAPH_UNFIL = os.getenv('OUTPUT_GRAPH_UNFIL', '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/output/6_scores/graph_all_unfiltered.gexf')

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
G = nx.Graph()

# Add all nodes first.
for node, (codes, semester) in node_codes.items():
    G.add_node(node, codes="|".join(codes), semester=semester)

# Add all edges (no filtering)
for (u, v), sim in edges_acc_unfiltered.items():
    G.add_edge(u, v, similarity=sim, weight=(1.0 - sim))

print(f"Unfiltered graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# -----------------------------
# Save graph
# -----------------------------
# Write the graph to GEXF.
nx.write_gexf(G, OUTPUT_GRAPH_UNFIL)
# nx.write_graphml(G, graphml_path)

# Let the user know where files were saved.
print(f"Saved unfiltered graph: {OUTPUT_GRAPH_UNFIL}")
# print(" -", graphml_path)

