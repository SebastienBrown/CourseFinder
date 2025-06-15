import json
from collections import defaultdict

# Constants for file paths
COORDINATES_FILE = 'precomputed_tsne_coords_all_v4.json'

def get_top_similar_courses(similarity_data, num_similar=3):
    """
    For each course, find the top N most similar courses within the same semester.
    Returns a dictionary mapping (semester, course_code) to a list of (course_code, similarity_score) tuples.
    """
    # Group courses by semester
    semester_courses = defaultdict(list)
    for entry in similarity_data:
        semester = entry.get('semester', 'unknown')
        for code in entry['course_codes']:
            semester_courses[semester].append((code, entry))
    
    # For each course, find top similar courses within same semester
    top_similar = {}
    
    for semester, courses in semester_courses.items():
        for code, entry in courses:
            # Get all compared courses from the same semester
            similar_courses = []
            for comp in entry.get('compared_courses', []):
                comp_semester = comp.get('semester', 'unknown')
                if comp_semester == semester and comp.get('course_codes'):
                    for comp_code in comp['course_codes']:
                        similar_courses.append((comp_code, comp['similarity_score']))
            
            # Sort by similarity score and take top N
            similar_courses.sort(key=lambda x: x[1], reverse=True)
            top_similar[(semester, code)] = similar_courses[:num_similar]
    
    return top_similar

def append_similar_courses_to_tsne():
    # Load similarity data
    with open('../../../similarity/output_similarity_all.json', 'r') as f:
        similarity_data = json.load(f)
    
    # Load t-SNE coordinates
    with open(f'../../public/{COORDINATES_FILE}', 'r') as f:
        tsne_data = json.load(f)
    
    # Get top similar courses
    top_similar = get_top_similar_courses(similarity_data)
    
    # Add similar_courses field to each entry
    for entry in tsne_data:
        semester = entry['semester']
        for code in entry['codes']:
            key = (semester, code)
            if key in top_similar:
                # Only add the similar_courses field, preserving all other data
                entry['similar_courses'] = [
                    {'code': code, 'similarity': score}
                    for code, score in top_similar[key]
                ]
                break  # Only add similar courses for the first code in the list
    
    # Save updated data back to the same file
    with open(f'../../public/{COORDINATES_FILE}', 'w') as f:
        json.dump(tsne_data, f, indent=2)
    with open(f'../../../backend/data/{COORDINATES_FILE}', 'w') as f:
        json.dump(tsne_data, f, indent=2)
    
    print(f"Successfully added similar_courses field to {len(tsne_data)} entries")

if __name__ == "__main__":
    append_similar_courses_to_tsne() 