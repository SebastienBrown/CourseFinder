import json
import os
import pandas as pd
from collections import defaultdict
from utils import normalize_codes

# -----------------------------
# Config
# -----------------------------
INPUT_ALL_COURSES = os.getenv('INPUT_ALL_COURSES', '/orcd/home/002/hnaka24/CourseFinder/backend/data/amherst_courses_all.json')
OUTPUT_MAJOR_DATA = os.getenv('OUTPUT_MAJOR_DATA', f'/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/5_scores/major_scores_panel.csv')

# -----------------------------
# Load the JSON data
# -----------------------------
with open(INPUT_ALL_COURSES, 'r') as f:
    courses = json.load(f)

# Create a dictionary to store counts by semester and major
counts = defaultdict(lambda: defaultdict(int))

# Process each course
for course in courses:
    semester = course.get('semester', 'unknown')
    course_title = course.get('course_title', 'unknown')
    
    # Handle course_codes whether it's a string or a list
    course_codes = course.get('course_codes', [])
    if isinstance(course_codes, str):
        course_codes = [course_codes]
    
    # Normalize major codes
    course_codes = normalize_codes(course_codes)
    
    # Count mixed courses (those with multiple course codes)
    if len(course_codes) > 1:
        counts[semester]['MIXD'] += 1
    
    # Get all course codes and extract majors
    for code in course_codes:
        # Extract major code - handle cases where code is shorter than 4 chars
        if not code:  # Skip empty codes
            continue
        # Split on '-' and take the first part
        major = code.split('-')[0] if '-' in code else code
        # If major is shorter than 4 chars, pad with spaces
        major = major.ljust(4)
        counts[semester][major] += 1

# Convert to DataFrame
# First, create a list of (semester, major, count) tuples
data = []
for semester in counts:
    # Extract year from semester (first 4 characters)
    year = semester[:4] if semester != 'unknown' else 'unknown'
    for major in counts[semester]:
        data.append({
            'semester': semester,
            'year': year,
            'major': major,
            'n_courses': counts[semester][major]
        })

# Create DataFrame and set multi-index
df = pd.DataFrame(data)

# --- 1. Total courses per major across all semesters ---
df_major_totals = df.groupby('major', as_index=False)['n_courses'].sum()
df_major_totals['semester'] = 'ALL'
df_major_totals['year'] = 'ALL'

# --- 2. Total courses per semester across all majors ---
df_semester_totals = df.groupby('semester', as_index=False)['n_courses'].sum()
df_semester_totals['major'] = 'ALL'
df_semester_totals['year'] = df_semester_totals['semester'].apply(lambda s: s[:4] if s != 'unknown' else 'unknown')

# --- Combine with original ---
df_full = pd.concat([df, df_major_totals, df_semester_totals], ignore_index=True, sort=False)

# Sort the index
df = df.set_index(['semester', 'year', 'major'])
df = df.sort_index()

# -----------------------------
# Merge to major panel
# -----------------------------
# Load the existing dataset
df_existing = pd.read_csv(OUTPUT_MAJOR_DATA)

# Merge on semester and major
df_merged = pd.merge(
    df_existing,
    df,
    on=["semester", "major"],
    how="outer"
)

# Save back
df_merged.to_csv(OUTPUT_MAJOR_DATA, index=False)
print("Done!")