import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import pandas as pd

# ========================================
# Configuration
# ========================================
dropbox = os.environ.get("DROPBOX", '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/')
code = os.environ.get("CODE", '/Users/hnaka24/Desktop/code/CourseFinder/')
model = os.environ.get("MODEL", "sbert")
mode = os.environ.get("MODE", "off_the_shelf")

similarity_file = os.environ.get("SIMILARITY_OUTPUT_FILE", dropbox + f'data/2_intermediate/3_similarity/{model}_{mode}/output_similarity_all.json')
diagnostics_file = os.environ.get("CONTRASTIVE_DIAGNOSTICS_PATH", dropbox + 'data/1_raw/diagnostics/diagnostics_20250827.csv')
output_pdf = os.environ.get("OUTPUT_PDF", dropbox + f'output/4_similarity/similarity_density_{model}_{mode}.pdf')

# ========================================
# Functions
# ========================================
def get_departments(course_codes):
    """Extract departments from course codes (first 4 characters)"""
    departments = set()
    for code in course_codes:
        if len(code) >= 4:
            departments.add(code[:4])
    return departments

def courses_same_department(main_codes, comp_codes):
    """Check if any department is shared between two sets of course codes"""
    main_depts = get_departments(main_codes)
    comp_depts = get_departments(comp_codes)
    return bool(main_depts.intersection(comp_depts))

def find_course_description(course_info, course_data):
    """Find course description by matching course code"""
    semester, course_code = course_info.split(', ')
    
    for course in course_data:
        # Check if semester matches
        if course.get('semester') != semester:
            continue
            
        # Handle case where course_codes might be a string or list
        course_codes = course.get('course_codes', [])
        if isinstance(course_codes, str):
            course_codes = [course_codes]
        
        if course_code in course_codes:
            return course.get('description', '')
    
    return ''

# ========================================
# Load Data
# ========================================
# Load the similarity data
with open(similarity_file, 'r') as f:
    data = json.load(f)

# Debug: Print sample similarity data format
print("Sample similarity data format:")
if data:
    sample_course = data[0]
    print(f"  Course: {sample_course.get('course_codes', 'N/A')} from {sample_course.get('semester', 'N/A')}")
    if sample_course.get('compared_courses'):
        sample_comp = sample_course['compared_courses'][0]
        print(f"  Compared to: {sample_comp.get('course_codes', 'N/A')} from {sample_comp.get('semester', 'N/A')}")
        print(f"  Similarity score: {sample_comp.get('similarity_score', 'N/A')}")

# Load diagnostics data
df = pd.read_csv(diagnostics_file)
print(f"Loaded diagnostics dataset with {len(df)} rows")

# ========================================
# By Annotated Positive and Negative Pairs
# ========================================
# Parse course information from diagnostics
all_courses = []
for idx, row in df.iterrows():
    row_courses = []
    for col in ['A', 'B', 'C', 'D']:
        course_info = row[col].strip('"')  # Remove quotes
        semester, course_code = course_info.split(', ')
        row_courses.append({
            'semester': semester,
            'course_code': course_code,
            'full_info': course_info
        })
    all_courses.append(row_courses)

# Create positive and negative pairs from diagnostics
diagnostics_pos_pairs = []
diagnostics_neg_pairs = []

for row in all_courses:
    # Extract courses A, B, C, D
    course_a_info = row[0]['full_info']
    course_b_info = row[1]['full_info']
    course_c_info = row[2]['full_info']
    course_d_info = row[3]['full_info']
    
    # Positive pairs: A-B, A-C, B-D, C-D
    diagnostics_pos_pairs.extend([
        (course_a_info, course_b_info),
        (course_a_info, course_c_info),
        (course_b_info, course_d_info),
        (course_c_info, course_d_info)
    ])
    
    # Negative pairs: A-D, B-C
    diagnostics_neg_pairs.extend([
        (course_a_info, course_d_info),
        (course_b_info, course_c_info)
    ])

print(f"Created {len(diagnostics_pos_pairs)} diagnostics positive pairs and {len(diagnostics_neg_pairs)} negative pairs")

# Debug: Print a few examples of diagnostics pairs
print("Sample diagnostics positive pairs:")
for i, pair in enumerate(diagnostics_pos_pairs[:3]):
    print(f"  {pair[0]} <-> {pair[1]}")
print("Sample diagnostics negative pairs:")
for i, pair in enumerate(diagnostics_neg_pairs[:3]):
    print(f"  {pair[0]} <-> {pair[1]}")

# Extract similarity scores for diagnostics pairs
diagnostics_pos_scores = []
diagnostics_neg_scores = []
seen_pairs = set()

for course in data:
    main_codes = course.get('course_codes', [])
    main_semester = course.get('semester', None)
    
    for comp in course.get('compared_courses', []):
        comp_codes = comp.get('course_codes', [])
        comp_semester = comp.get('semester', None)
        
        # Create course info strings for comparison
        main_codes_list = main_codes if isinstance(main_codes, list) else [main_codes]
        comp_codes_list = comp_codes if isinstance(comp_codes, list) else [comp_codes]
        
        # Debug: Print course codes format
        if len(diagnostics_pos_scores) + len(diagnostics_neg_scores) < 3:
            print(f"Main codes: {main_codes_list}, Comp codes: {comp_codes_list}")
        
        # Check all combinations of course codes
        for main_code in main_codes_list:
            for comp_code in comp_codes_list:
                main_info = f"{main_semester}, {main_code}"
                comp_info = f"{comp_semester}, {comp_code}"
                
                # Create a unique, order-independent key for the pair
                pair_key = tuple(sorted([main_info, comp_info]))
                
                if pair_key not in seen_pairs:
                    score = comp.get('similarity_score')
                    if score is not None:
                        # Debug: Print a few examples of course info strings being compared
                        if len(diagnostics_pos_scores) + len(diagnostics_neg_scores) < 5:
                            print(f"Checking pair: {main_info} <-> {comp_info}")
                            print(f"  In pos pairs: {(main_info, comp_info) in diagnostics_pos_pairs or (comp_info, main_info) in diagnostics_pos_pairs}")
                            print(f"  In neg pairs: {(main_info, comp_info) in diagnostics_neg_pairs or (comp_info, main_info) in diagnostics_neg_pairs}")
                        
                        # Check if this pair is in diagnostics positive or negative pairs
                        if (main_info, comp_info) in diagnostics_pos_pairs or (comp_info, main_info) in diagnostics_pos_pairs:
                            diagnostics_pos_scores.append(score)
                        elif (main_info, comp_info) in diagnostics_neg_pairs or (comp_info, main_info) in diagnostics_neg_pairs:
                            diagnostics_neg_scores.append(score)
                    seen_pairs.add(pair_key)

print(f"Found {len(diagnostics_pos_scores)} diagnostics positive scores and {len(diagnostics_neg_scores)} negative scores")

# ========================================
# By Department
# ========================================
# Extract similarity scores, separating by department
same_dept_scores = []
diff_dept_scores = []
seen_pairs = set()

for course in data:
    main_codes = course.get('course_codes', [])
    main_semester = course.get('semester', None)
    
    for comp in course.get('compared_courses', []):
        comp_codes = comp.get('course_codes', [])
        comp_semester = comp.get('semester', None)
        
        # Create a unique, order-independent key for the pair (including semester)
        pair_key = tuple(sorted([(main_semester, tuple(main_codes)), (comp_semester, tuple(comp_codes))]))
        
        if pair_key not in seen_pairs:
            score = comp.get('similarity_score')
            if score is not None:
                # Check if courses are in the same department
                if courses_same_department(main_codes, comp_codes):
                    same_dept_scores.append(score)
                else:
                    diff_dept_scores.append(score)
            seen_pairs.add(pair_key)

# ========================================
# Plot
# ========================================
# Create side-by-side plots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle(f'{model.upper()}, {mode.replace("_", " ").title()}', fontsize=16)

# Plot 1: Within vs Across Department
if same_dept_scores:
    sns.kdeplot(same_dept_scores, fill=False, bw_adjust=0.2, color='blue', alpha=0.6, 
                label=f'Within Department (n={len(same_dept_scores)})', ax=ax1)

if diff_dept_scores:
    sns.kdeplot(diff_dept_scores, fill=False, bw_adjust=0.2, color='pink', alpha=0.6, 
                label=f'Across Departments (n={len(diff_dept_scores)})', ax=ax1)

ax1.set_title('Similarity Scores by Department')
ax1.set_xlabel('Similarity Score')
ax1.set_ylabel('Density')
ax1.legend()
ax1.set_xlim(0, 1)
ax1.set_xticks(np.arange(0, 1.1, 0.1))

# Plot 2: Diagnostics Positive vs Negative Pairs
if diagnostics_pos_scores:
    sns.kdeplot(diagnostics_pos_scores, fill=False, bw_adjust=0.2, color='blue', alpha=0.6, 
                label=f'Diagnostics Positive (n={len(diagnostics_pos_scores)})', ax=ax2)

if diagnostics_neg_scores:
    sns.kdeplot(diagnostics_neg_scores, fill=False, bw_adjust=0.2, color='pink', alpha=0.6, 
                label=f'Diagnostics Negative (n={len(diagnostics_neg_scores)})', ax=ax2)

ax2.set_title('Similarity Scores by Diagnostics Pairs')
ax2.set_xlabel('Similarity Score')
ax2.set_ylabel('Density')
ax2.legend()
ax2.set_xlim(0, 1)
ax2.set_xticks(np.arange(0, 1.1, 0.1))

plt.tight_layout(rect=[0, 0, 1, 0.95])  # Leave room for the title
plt.savefig(output_pdf, bbox_inches='tight', dpi=300)
print(f"Density plots saved to {output_pdf}")
print(f"Same department pairs: {len(same_dept_scores)}")
print(f"Different department pairs: {len(diff_dept_scores)}")
print(f"Diagnostics positive pairs: {len(diagnostics_pos_scores)}")
print(f"Diagnostics negative pairs: {len(diagnostics_neg_scores)}") 