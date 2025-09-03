from pathlib import Path
import pandas as pd
import numpy as np
import json, ast, re
import os
import matplotlib.pyplot as plt

# -----------------------------
# Paths
# -----------------------------
filedate = os.getenv('FILEDATE', '20250813')
INPUT_PATH = os.getenv('INPUT_PATH', f"/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/raw/user_courses/user_courses_{filedate}.csv")
OUTPUT_STUDENT_DATA = os.getenv('OUTPUT_STUDENT_DATA', f"/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/5_scores/student_scores_{filedate}.csv")
OUTPUT_PLOT = os.getenv('OUTPUT_PLOT', f"/Users/hnaka24/Dropbox (Personal)/AmherstCourses/output/6_scores/student_scores_scatter_{filedate}.pdf")

# -----------------------------
# Config
# -----------------------------
major_codes = [
    "AMST","ANTH","SOCI","ARCH","ARHA","AAPI","ASLC","BCBP","BIOL","BLST","CHEM",
    "CLAS","COSC","ECON","EDST","ENGL","ENST","EUST","FAMS","FYSE","FREN","GERM",
    "GEOL","HIST","LLAS","LJST","MATH","MUSI","NEUR","PHIL","PHYS","ASTR","POSC",
    "PSYC","RELI","RUSS","SWAG","SPAN","THDA"
]
remove_numbers = {"290","390","490","498","499"}
entropy_base = "e"  # use "2" for bits

# Semester pattern for detecting semester columns
pat_sem = re.compile(r"^(\d{4})([A-Z])$")  # semester like 2223F / 2021S / 0910F

# -----------------------------
# Helpers
# -----------------------------
def _safe_list_from_cell(cell):
    """Parse a cell into a Python list; return [] if not parseable."""
    if not isinstance(cell, str):
        return []
    s = cell.strip()
    if not s:
        return []
    try:  # fast path: JSON lists like '["COSC-211","ECON-361"]'
        val = json.loads(s)
        return val if isinstance(val, list) else []
    except Exception:
        pass
    try:  # fallback: Python literal
        val = ast.literal_eval(s)
        return val if isinstance(val, list) else []
    except (ValueError, SyntaxError):
        return []

def parse_courses_row(row):
    """Flatten all semester cells into one list of course strings (chronological)."""
    out = []
    for cell in row:  # preserve column order
        out.extend(_safe_list_from_cell(cell))
    return [str(p).strip() for p in out]

def filter_courses(courses):
    """Remove unwanted course numbers and any COLQ courses."""
    out = []
    for c in courses:
        # Skip if COLQ prefix
        if c.startswith("COLQ"):
            continue
        # Skip if course number is in remove_numbers
        m = re.search(r'\b(\d{3})\b', c)
        if m and m.group(1) in remove_numbers:
            continue
        out.append(c)
    return out

def get_disciplines(course):
    """
    Return list of disciplines for a course code.
    Supports cross-listings like 'AMST/ENGL-221' (split evenly).
    """
    #remove course header prior to hyphen: e.g. AMST/ENGL-221 -> AMST/ENGL
    prefix = course.split("-", 1)[0].strip()
    #split AMST/ENGL into AMST, ENGL
    prefixes = [p.strip() for p in prefix.split("/")]
    #Return a list of valid major codes corresponding to the course in question
    return [p for p in prefixes if p in major_codes]

def _discipline_probs(courses):
    """Return dict of {discipline: probability} for a student's course list."""
    contrib = {}
    #loop through all courses in a student's course list
    for course in courses:
        #generate the majors a course belongs to
        dlist = get_disciplines(course)
        if not dlist:
            continue
        #Each individual discipline a course is in contributes to the total weight, which is 1.
        #For instance, if a course is just a math course, it has a weight of 1 in math
        #If a course is crosslisted under three departments (AMST, ASLC, RUSS), then it has
        #a weight of 1/3 in AMST, 1/3 in ASLC, and 1/3 in RUSS.
        #The point of doing this is to allow us to parse crosslisted courses.
        #"Crosslisted courses" don't really exist in ecology, so Shannon diversity can't handle such situations
        #That would be like an organism belonging to multiple species/categories simultaneously.
        w = 1.0 / len(dlist)
        #At this step you update the dictionary with the weights for each major.
        #Let's say the dictionary looks like contrib = {"AMST": 0.5, "ENGL": 0.5}.
        #If you add in "ENGL-101", then since ENGL would have weight 1.0, 
        #the dictionary contrib would be updated to {"AMST": 0.5, "ENGL": 1.5}.
        for d in dlist:
            contrib[d] = contrib.get(d, 0.0) + w
    total = sum(contrib.values())
    if total <= 0:
        return {}
        #converts weights into probabilities by dviding by the sum of all weights "total"
    return {d: v / total for d, v in contrib.items() if v > 0}

def shannon_entropy(probs, base="e"):
    """Unnormalized Shannon entropy from a dict/list of probabilities."""
    #vals can handle probabilities in a dictionary or a list of probabilities
    vals = list(probs.values()) if isinstance(probs, dict) else list(probs)
    #filtering out zero probabilities since log(0) is undefined 
    vals = [p for p in vals if p > 0]
    if not vals:
        #if no positive probabilities throw an undefined
        return np.nan
    #set the base of the logarithm
    logf = np.log2 if base == "2" else np.log
    #calculate Shannon entropy
    #H = -\sum_{i} p_i \log_b(p_i)
    return -sum(p * logf(p) for p in vals)

def normalized_entropy(probs, base="e"):
    """
    posterior::entropy equivalent: -sum p log p / log(n),
    where n = number of categories with p>0. Returns 0..1.
    """
    vals = list(probs.values()) if isinstance(probs, dict) else list(probs)
    vals = [p for p in vals if p > 0]
    n = len(vals)
    if n <= 1:
        return 0.0
    logf = np.log2 if base == "2" else np.log
    H = -sum(p * logf(p) for p in vals)
    return float(H / logf(n))

def hhi_index(probs):
    """
    Herfindahl–Hirschman Index (HHI) = sum(p^2).
    Higher = more concentrated (less diverse).
    """
    vals = list(probs.values()) if isinstance(probs, dict) else list(probs)
    vals = [p for p in vals if p > 0]
    if not vals:
        return np.nan
    return sum(p ** 2 for p in vals)

# -----------------------------
# Load and process
# -----------------------------
df = pd.read_csv(INPUT_PATH)

# Drop obvious metadata columns if present
course_df = df.drop(columns=["created_at", "id"], errors="ignore")

results = []
for original_idx, row in course_df.iterrows():
    courses = parse_courses_row(row)

    # Return dict of {discipline: probability} (here, just to get list of departments)
    depts = _discipline_probs(courses)

    # Filter courses and skip if row has no valid courses left
    filtered_courses = filter_courses(courses)
    if not filtered_courses:
        continue

    # Return dict of {discipline: probability}
    probs = _discipline_probs(filtered_courses)
    if not probs:
        continue

    # Compute breadth metrics
    H = shannon_entropy(probs, base=entropy_base)
    H_norm = normalized_entropy(probs, base=entropy_base)
    HHI = hhi_index(probs)    # 0..1, higher = less diverse

    # Average course difficulty
    lvls = []
    for c in courses:
        m = re.search(r"-(\d{3})", str(c))  # Extract the hundreds level from the code, e.g. 'MATH-211' -> 200
        lvl = (int(m.group(1)) // 100) * 100 if m else None
        if lvl is not None:
            lvls.append(lvl)  # Add the level (int like 100/200/300/400) to our list
    avg_diff = float(np.mean(lvls)) if lvls else float("nan") # compute the arithmetic mean

    # Create result dict with semester columns preserved
    result_dict = {
        "StudentID": original_idx + 1,
        "NumCourses": len(courses),
        "NumDisciplines": len(depts),
        "EntropyScore": H,
        "EntropyNormalized": H_norm,
        "HHIIndex": HHI,
        "avg_course_difficulty": avg_diff
    }
    
    # Add all original semester columns from the row
    for col in row.index:
        result_dict[col] = row[col]
    
    results.append(result_dict)

results_df = pd.DataFrame(results)

# -----------------------------
# Save output csv
# -----------------------------
# Sort by normalized entropy (desc), then raw entropy, then StudentID
if not results_df.empty:
    results_df = results_df.sort_values(
        by=["EntropyNormalized", "EntropyScore", "StudentID"],
        ascending=[False, False, True],
        kind="mergesort"
    ).reset_index(drop=True)

results_df.to_csv(OUTPUT_STUDENT_DATA, index=False)
print("Student-level discrete breadth scores saved to csv.")