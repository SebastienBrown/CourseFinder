import json
import os

# List of semesters to process
semesters = ['0910F', '0910S', '1011F', '1011S', '1112F', '1112S', '1213F', '1213S', '1314F', '1314S', '1415F', '1415S', '1516F', '1516S', '1617F', '1617S', '1718F', '1718S', '1819F', '1819S', '1920F', '1920S', '2021F', '2021J', '2021S', '2122F', '2122J', '2122S', '2223F', '2223S', '2324F', '2324S', '2425F', '2425S', '2526F', '2526S']

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

# Write the combined data to the output file
os.makedirs('course-visualization/public', exist_ok=True)
output_file = 'course-visualization/public/amherst_courses_all.json'
with open(output_file, 'w') as f:
    json.dump(all_courses, f, indent=2)

# Also write to backend/data with the same filename
os.makedirs('backend/data', exist_ok=True)
backend_output_file = 'backend/data/amherst_courses_all.json'
with open(backend_output_file, 'w') as f:
    json.dump(all_courses, f, indent=2)

print(f"Successfully combined {len(all_courses)} courses from {len(semesters)} semesters")
print(f"Output written to {output_file}") 