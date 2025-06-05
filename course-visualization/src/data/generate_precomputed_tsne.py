import json
import numpy as np
from sklearn.manifold import TSNE

def separate_overlapping_points(coords, similarity_matrix, course_codes, min_dist=1.0, step_size=0.1, num_iterations=100):
    """
    Iteratively separates points that are closer than min_dist, except for exact duplicates across different semesters.
    Args:
        coords: numpy array of shape (n, 2) containing the coordinates
        similarity_matrix: numpy array of shape (n, n) containing similarity scores
        course_codes: list of (semester, code) tuples corresponding to each point
        min_dist: minimum distance between points (in t-SNE coordinate space)
        step_size: how much to move points in each iteration
        num_iterations: maximum number of iterations to perform
    """
    n = coords.shape[0]
    for _ in range(num_iterations):
        displacements = np.zeros_like(coords)
        for i in range(n):
            for j in range(i + 1, n):
                vec = coords[j] - coords[i]
                dist = np.linalg.norm(vec)
                
                # If points are exact duplicates (similarity = 1) AND from different semesters, keep them together
                if similarity_matrix[i, j] >= 0.99 and course_codes[i][0] != course_codes[j][0]:  # Using 0.99 to account for floating point imprecision
                    continue
                    
                if dist < min_dist and dist > 1e-6:  # Avoid division by zero
                    # Calculate separation based on similarity
                    # Less similar points should be separated more
                    similarity = similarity_matrix[i, j]
                    separation_factor = 1.0 - similarity  # 0 for identical, 1 for completely different
                    overlap = (min_dist - dist) * (1.0 + separation_factor)  # More separation for less similar points
                    
                    direction = vec / dist
                    # Move both points away from each other
                    displacements[i] -= direction * overlap * 0.5 * step_size
                    displacements[j] += direction * overlap * 0.5 * step_size
        coords += displacements
    return coords

# Load your similarity data
with open(f'../../../similarity/output_similarity_2324S.json', 'r') as f:
    data = json.load(f)

out = ['499', '498', '496', '490', '390', '290', '210F', '111F']

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

# Build unique course list using (semester, course_code) as key
course_codes = []
code_to_idx = {}
for entry in valid_data:
    # Only use the first course code for each entry
    primary_code = entry['course_codes'][0]
    semester = entry.get('semester', 'unknown')  # Use 'unknown' as fallback
    unique_key = (semester, primary_code)
    if unique_key not in code_to_idx and not any(code in primary_code for code in out):
        code_to_idx[unique_key] = len(course_codes)
        course_codes.append(unique_key)

n = len(course_codes)
sim_matrix = np.zeros((n, n))

# Fill similarity matrix
for entry in valid_data:
    # Use only the first course code
    primary_code = entry['course_codes'][0]
    semester = entry.get('semester', 'unknown')
    unique_key = (semester, primary_code)
    if unique_key not in code_to_idx:
        continue
    idxA = code_to_idx[unique_key]
    
    for comp in entry.get('compared_courses', []):
        if not comp.get('course_codes') or len(comp['course_codes']) == 0:
            print(f"Warning: Empty course_codes in compared_courses: {comp}")
            skipped_entries.append(comp)
            continue
        
        # Use only the first course code for compared course
        comp_code = comp['course_codes'][0]
        comp_semester = comp.get('semester', 'unknown')
        comp_unique_key = (comp_semester, comp_code)
        idxB = code_to_idx.get(comp_unique_key)
        
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
perplexity = 200  # Ensure perplexity is appropriate for dataset size
tsne = TSNE(
    n_components=2, 
    metric='precomputed', 
    random_state=42, 
    perplexity=perplexity, 
    init='random'
)
coords = tsne.fit_transform(dist_matrix)

# Separate overlapping points
print(f'Separating overlapping points with min_dist={1.0}...')
# coords = separate_overlapping_points(coords, sim_matrix, course_codes, min_dist=1.0)

# Save coordinates and course codes
output = []
for entry in valid_data:
    # Get all course codes for this entry
    codes = entry['course_codes']
    semester = entry.get('semester', 'unknown')
    # Find the index of the primary code in the similarity matrix
    primary_code = codes[0]
    unique_key = (semester, primary_code)
    if unique_key not in code_to_idx:
        continue
    idx = code_to_idx[unique_key]
    x, y = coords[idx]
    # Create an entry with all course codes
    output.append({
        'codes': codes,  # Store all codes
        'semester': semester,
        'x': float(x),
        'y': float(y)
    })

# Save results
with open(f'../../public/precomputed_tsne_coords_2324S_200_overlap.json', 'w') as f:
    json.dump(output, f, indent=2)
with open(f'../../../backend/data/precomputed_tsne_coords_2324S_200_overlap.json', 'w') as f:
    json.dump(output, f, indent=2)

# if skipped_entries:
#     # Save skipped entries to the 'skipped' directory at the workspace root
#     with open(f'../../../skipped/skipped_entries_all.json', 'w') as f:
#         json.dump(skipped_entries, f, indent=2)
#     print(f"Skipped {len(skipped_entries)} entries with empty course_codes. See skipped/skipped_entries_all.json for details.")
# else:
#     print("No entries with empty course_codes were skipped.")

print(f'Saved t-SNE coordinates for {n} unique courses to precomputed_tsne_coords.json')

# # Optional: Add metadata to the output (commented out atm)
# course_metadata = {}
# for entry in valid_data:
#     primary_code = entry['course_codes'][0]
#     if primary_code in course_codes:
#         # Store additional metadata if available
#         metadata = {
#             'code': primary_code,
#             'title': entry.get('title', ''),
#             'description': entry.get('description', ''),
#             'department': entry.get('department', '')
#         }
#         course_metadata[primary_code] = metadata

# if course_metadata:
#     # Save course metadata to the 'course_metadata' directory at the workspace root
#     with open(f'../../../course_metadata/course_metadata_all.json', 'w') as f:
#         json.dump(course_metadata, f, indent=2)
#     print(f'Saved course metadata to course_metadata/all.json')