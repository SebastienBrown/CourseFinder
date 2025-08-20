import json
import pandas as pd
from collections import defaultdict

# Load the JSON data
with open('../backend/data/amherst_courses_all.json', 'r') as f:
    courses = json.load(f)

# Create a dictionary to store counts by semester and department
counts = defaultdict(lambda: defaultdict(int))

# Process each course
for course in courses:
    semester = course.get('semester', 'unknown')
    course_title = course.get('course_title', 'unknown')
    
    # Handle course_codes whether it's a string or a list
    course_codes = course.get('course_codes', [])
    if isinstance(course_codes, str):
        course_codes = [course_codes]
    elif not isinstance(course_codes, list):
        course_codes = []
    
    # Count mixed courses (those with multiple course codes)
    if len(course_codes) > 1:
        counts[semester]['MIXD'] += 1
    
    # Get all course codes and extract departments
    for code in course_codes:
        # Extract department code - handle cases where code is shorter than 4 chars
        if not code:  # Skip empty codes
            continue
        # Split on '-' and take the first part
        dept = code.split('-')[0] if '-' in code else code
        # If department is shorter than 4 chars, pad with spaces
        dept = dept.ljust(4)
        counts[semester][dept] += 1

# Convert to DataFrame
# First, create a list of (semester, dept, count) tuples
data = []
for semester in counts:
    # Extract year from semester (first 4 characters)
    year = semester[:4] if semester != 'unknown' else 'unknown'
    for dept in counts[semester]:
        data.append({
            'semester': semester,
            'year': year,
            'dept': dept,
            'course_count': counts[semester][dept]
        })

# Create DataFrame and set multi-index
df = pd.DataFrame(data)
df = df.set_index(['semester', 'year', 'dept'])

# Sort the index
df = df.sort_index()

# Save to CSV
df.to_csv('../data/course_counts_by_semester_dept.csv')
print("Done!")