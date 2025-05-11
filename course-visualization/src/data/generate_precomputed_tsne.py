import json
import numpy as np
from sklearn.manifold import TSNE

# Load your similarity data
with open('./course-visualization/src/data/output_courses_similarity.json', 'r') as f:
    data = json.load(f)

# Filter out entries with empty course_codes
valid_data = [entry for entry in data if entry.get('course_codes') and len(entry['course_codes']) > 0]
skipped_entries = [entry for entry in data if not (entry.get('course_codes') and len(entry['course_codes']) > 0)]

# Build unique course list
course_codes = []
code_to_idx = {}
for entry in valid_data:
    for code in entry['course_codes']:
        if code not in code_to_idx:
            code_to_idx[code] = len(course_codes)
            course_codes.append(code)

n = len(course_codes)
sim_matrix = np.zeros((n, n))

# Fill similarity matrix
for entry in valid_data:
    idxA = code_to_idx[entry['course_codes'][0]]
    for comp in entry.get('compared_courses', []):
        if not comp.get('course_codes') or len(comp['course_codes']) == 0:
            print(f"Warning: Empty course_codes in compared_courses: {comp}")
            skipped_entries.append(comp)
            continue
        idxB = code_to_idx.get(comp['course_codes'][0])
        if idxB is None:
            continue
        sim_matrix[idxA, idxB] = comp['similarity_score']
        sim_matrix[idxB, idxA] = comp['similarity_score']
np.fill_diagonal(sim_matrix, 1.0)

# Convert similarity to distance
# Ensure all values are in [0, 1] and no negative values
sim_matrix = np.clip(sim_matrix, 0, 1)
dist_matrix = 1.0 - sim_matrix
np.fill_diagonal(dist_matrix, 0.0)
# Ensure symmetry and non-negativity
dist_matrix = (dist_matrix + dist_matrix.T) / 2
assert np.all(dist_matrix >= 0), "Distance matrix has negative values!"

# Run t-SNE
print(f'Running t-SNE on {n} courses...')
tsne = TSNE(n_components=2, metric='precomputed', random_state=42, perplexity=min(30, n//3), init='random')
coords = tsne.fit_transform(dist_matrix)

# Save coordinates and course codes
output = [
    {'code': code, 'x': float(x), 'y': float(y)}
    for code, (x, y) in zip(course_codes, coords)
]
with open('precomputed_tsne_coords.json', 'w') as f:
    json.dump(output, f, indent=2)

if skipped_entries:
    with open('skipped_entries.json', 'w') as f:
        json.dump(skipped_entries, f, indent=2)
    print(f"Skipped {len(skipped_entries)} entries with empty course_codes. See skipped_entries.json for details.")
else:
    print("No entries with empty course_codes were skipped.")

print('Saved t-SNE coordinates to precomputed_tsne_coords.json') 