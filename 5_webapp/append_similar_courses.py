import json
from collections import defaultdict

# Constants for file paths
COORDINATES_FILE = 'precomputed_tsne_coords_all_v4.json'

# Load similarity data
with open('similarity/output_similarity_all.json', 'r') as f:
    similarity_data = json.load(f)

# Remove senior honors courses and special topics
out = ['499', '498', '490', '390', '290', '210F', '111F', '-77', '-78', '-77D']

# Filter out courses with course codes
filtered_courses = []
for course in similarity_data:
    # Handle course_codes whether it's a string or a list
    course_codes = course.get('course_codes', [])
    if isinstance(course_codes, str):
        course_codes = [course_codes]
    elif not isinstance(course_codes, list):
        course_codes = []
        
    # Check if any of the main course codes contain the excluded numbers
    if any(any(code.endswith(excluded) for excluded in out) for code in course_codes):
        continue
        
    # Filter out specific comparisons that contain excluded numbers
    filtered_compared = []
    for comp in course.get('compared_courses', []):
        comp_codes = comp.get('course_codes', [])
        if isinstance(comp_codes, str):
            comp_codes = [comp_codes]
        elif not isinstance(comp_codes, list):
            comp_codes = []
            
        # Only keep this comparison if none of its codes end with excluded numbers
        if not any(any(code.endswith(excluded) for excluded in out) for code in comp_codes):
            filtered_compared.append(comp)
    
    # Update the course with filtered comparisons
    course['compared_courses'] = filtered_compared
    filtered_courses.append(course)

print(f"Filtered out {len(similarity_data) - len(filtered_courses)} courses with course codes containing {out}.")
similarity_data = filtered_courses

# Get top similar courses for each course
top_similar = {}
for entry in similarity_data:
    course_codes = entry['course_codes']
    semester = entry['semester']
    
    # Skip if no compared courses
    if not entry.get('compared_courses'):
        continue
        
    # First filter courses by semester, then sort by similarity score
    same_semester_courses = [
        course for course in entry['compared_courses']
        if course['semester'] == semester
    ]
    
    # Filter out self-comparisons (where a course is compared with its own other codes)
    filtered_courses = []
    seen_courses = set()  # Keep track of courses we've already seen
    for course in same_semester_courses:
        # Skip if any of the compared course codes are in the original course's codes
        if not any(code in course_codes for code in course['course_codes']):
            # Create a unique identifier for this course using its first code
            course_id = course['course_codes'][0]
            if course_id not in seen_courses:
                seen_courses.add(course_id)
                filtered_courses.append(course)
    
    # Sort filtered courses by similarity score
    sorted_courses = sorted(
        filtered_courses,
        key=lambda x: x['similarity_score'],
        reverse=True
    )
    
    # Take top 3 similar courses
    similar_courses = []
    for course in sorted_courses[:3]:
        similar_courses.append({
            'code': course['course_codes'],
            'similarity': course['similarity_score']
        })
    
    # Store the similar courses under the course codes list and semester
    top_similar[(tuple(course_codes), semester)] = similar_courses

# Load t-SNE coordinates
with open(f'course-visualization/public/{COORDINATES_FILE}', 'r') as f:
    tsne_data = json.load(f)

# Remove any existing similar_courses field
for entry in tsne_data:
    if 'similar_courses' in entry:
        del entry['similar_courses']

# Add similar_courses field to each entry
for entry in tsne_data:
    course_codes = tuple(entry['codes'])  # Convert to tuple for dictionary lookup
    semester = entry['semester']
    key = (course_codes, semester)
    if key in top_similar:
        entry['similar_courses'] = top_similar[key]
    else:
        entry['similar_courses'] = []

# Save updated data back to the same file
with open(f'course-visualization/public/{COORDINATES_FILE}', 'w') as f:
    json.dump(tsne_data, f, indent=2)
with open(f'backend/data/{COORDINATES_FILE}', 'w') as f:
    json.dump(tsne_data, f, indent=2)

print(f"Successfully added similar_courses field to {len(tsne_data)} entries") 