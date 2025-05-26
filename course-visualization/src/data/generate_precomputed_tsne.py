import json
import numpy as np
from sklearn.manifold import TSNE

# Load your similarity data
with open('./output_courses_similarity.json', 'r') as f:
    data = json.load(f)

out = ['499', '490', '390','498', '210F']

# Filter out courses with course codes
filtered_courses = []
for course in data:
    # Check if any of the main course codes contain the excluded numbers
    if any(code in course['course_codes'] for code in out):
        continue
    # Check if any of the compared courses contain the excluded numbers
    if any(any(code in comp.get('course_codes', []) for code in out) for comp in course.get('compared_courses', [])):
        continue
    filtered_courses.append(course)
print(f"Filtered out {len(data) - len(filtered_courses)} courses with course codes containing {out}.")
data = filtered_courses

# Filter out entries with empty course_codes
valid_data = [entry for entry in data if entry.get('course_codes') and len(entry['course_codes']) > 0]
skipped_entries = [entry for entry in data if not (entry.get('course_codes') and len(entry['course_codes']) > 0)]

# Build unique course list - ONLY USE FIRST COURSE CODE
course_codes = []
code_to_idx = {}
for entry in valid_data:
    # Only use the first course code for each entry
    primary_code = entry['course_codes'][0]
    if primary_code not in code_to_idx and not any(code in primary_code for code in out):
        code_to_idx[primary_code] = len(course_codes)
        course_codes.append(primary_code)

n = len(course_codes)
sim_matrix = np.zeros((n, n))

# Fill similarity matrix
for entry in valid_data:
    # Use only the first course code
    primary_code = entry['course_codes'][0]
    if primary_code not in code_to_idx:
        continue
    idxA = code_to_idx[primary_code]
    
    for comp in entry.get('compared_courses', []):
        if not comp.get('course_codes') or len(comp['course_codes']) == 0:
            print(f"Warning: Empty course_codes in compared_courses: {comp}")
            skipped_entries.append(comp)
            continue
        
        # Use only the first course code for compared course
        comp_code = comp['course_codes'][0]
        idxB = code_to_idx.get(comp_code)
        
        if idxB is None:
            continue
            
        sim_matrix[idxA, idxB] = comp['similarity_score']
        sim_matrix[idxB, idxA] = comp['similarity_score']  # Ensure symmetry

# Set diagonal to 1.0 (each course is perfectly similar to itself)
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
perplexity = min(30, max(5, n//3))  # Ensure perplexity is appropriate for dataset size
tsne = TSNE(
    n_components=2, 
    metric='precomputed', 
    random_state=42, 
    perplexity=perplexity, 
    init='random'
)
coords = tsne.fit_transform(dist_matrix)

# Save coordinates and course codes
output = []
for entry in valid_data:
    # Get all course codes for this entry
    codes = entry['course_codes']
    # Find the index of the primary code in the similarity matrix
    primary_code = codes[0]
    if primary_code not in code_to_idx:
        continue
    idx = code_to_idx[primary_code]
    x, y = coords[idx]
    # Create an entry with all course codes
    output.append({
        'codes': codes,  # Store all codes
        'x': float(x),
        'y': float(y)
    })

# Save results
with open('precomputed_tsne_coords.json', 'w') as f:
    json.dump(output, f, indent=2)

if skipped_entries:
    with open('skipped_entries.json', 'w') as f:
        json.dump(skipped_entries, f, indent=2)
    print(f"Skipped {len(skipped_entries)} entries with empty course_codes. See skipped_entries.json for details.")
else:
    print("No entries with empty course_codes were skipped.")

print(f'Saved t-SNE coordinates for {n} unique courses to precomputed_tsne_coords.json')

# Optional: Add metadata to the output
course_metadata = {}
for entry in valid_data:
    primary_code = entry['course_codes'][0]
    if primary_code in course_codes:
        # Store additional metadata if available
        metadata = {
            'code': primary_code,
            'title': entry.get('title', ''),
            'description': entry.get('description', ''),
            'department': entry.get('department', '')
        }
        course_metadata[primary_code] = metadata

if course_metadata:
    with open('course_metadata.json', 'w') as f:
        json.dump(course_metadata, f, indent=2)
    print('Saved course metadata to course_metadata.json')