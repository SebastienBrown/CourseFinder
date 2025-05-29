import json
import os

# List of semesters to process
semesters = ['2223F', '2223S', '2324F', '2324S']

# Initialize empty list to store all courses
all_courses = []

# Process each semester
for semester in semesters:
    # Construct input file path
    input_file = f'llm_cleaned/amherst_courses_{semester}.json'
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Warning: File {input_file} not found, skipping...")
        continue
    
    # Read the JSON file
    with open(input_file, 'r') as f:
        courses = json.load(f)
    
    # Process each course
    for course in courses:
        # Remove the 'semester' key if it exists
        if 'semester' in course:
            del course['semester']
        
        # Add semester_code
        course['semester'] = semester
    
    # Add processed courses to the main list
    all_courses.extend(courses)

# Create output directory if it doesn't exist
os.makedirs('course-visualization/public', exist_ok=True)

# Write the combined data to the output file
output_file = 'course-visualization/public/amherst_courses_all.json'
with open(output_file, 'w') as f:
    json.dump(all_courses, f, indent=2)

print(f"Successfully combined {len(all_courses)} courses from {len(semesters)} semesters")
print(f"Output written to {output_file}") 