from pathlib import Path
import pandas as pd
import numpy as np
import json, ast, re
import matplotlib.pyplot as plt

# -----------------------------
# Paths
# -----------------------------
filedate = '20250720'
INPUT_PATH  = Path(f"6_analysis/data/raw/user_courses_{filedate}.csv")
# OUTPUT_PATH = Path("./student_entropy_scores.csv")

dropbox = '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/'
OUTPUT_PATH = Path(dropbox + f'data/2_intermediate/5_scores/student_entropy_scores_{filedate}.csv')
output_plot = dropbox + f'output/6_scores/student_scores_scatter_{filedate}.pdf'

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

    # Return matrix of pairwise distance for the student
    

    # Compute diversity metrics
    H = shannon_entropy(probs, base=entropy_base)
    H_norm = normalized_entropy(probs, base=entropy_base)
    HHI = hhi_index(probs)    # 0..1, higher = less diverse

    results.append({
        "StudentID": original_idx + 1,
        "NumCourses": len(courses),
        "NumDisciplines": len(depts),
        "EntropyScore": H,
        "EntropyNormalized": H_norm,
        "HHIIndex": HHI,
        "CoursesChronological": courses
    })

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

results_df.to_csv(OUTPUT_PATH, index=False)

# -----------------------------
# Export scatter plot
# -----------------------------
print(f"Wrote {len(results_df)} rows to {OUTPUT_PATH.resolve()}")
print(results_df.head(10))

# Select the columns you want to include in the pairwise scatter plot
plot_vars = ["NumDisciplines", "EntropyNormalized", "HHIIndex"]

n_vars = len(plot_vars)
fig, axes = plt.subplots(n_vars, n_vars, figsize=(4 * n_vars, 4 * n_vars))

for i in range(n_vars):
    for j in range(n_vars):
        ax = axes[i, j]
        if i == j:
            # Diagonal: histogram
            ax.hist(results_df[plot_vars[i]], bins=20, color="skyblue", edgecolor="black")
        elif i > j:
            # Lower triangle: scatter with best-fit line
            x = results_df[plot_vars[j]]
            y = results_df[plot_vars[i]]
            ax.scatter(x, y, alpha=0.6, edgecolors="w", s=40)

            # Fit and plot regression line
            m, b = np.polyfit(x, y, deg=1)
            ax.plot(x, m * x + b, color="red", linewidth=2)
        else:
            # Upper triangle: leave blank
            ax.axis("off")

        # Axis labels
        if i == n_vars - 1:
            ax.set_xlabel(plot_vars[j], fontsize=14)
        else:
            ax.set_xlabel("")
        if j == 0:
            ax.set_ylabel(plot_vars[i], fontsize=14)
        else:
            ax.set_ylabel("")

plt.tight_layout()
plt.savefig(output_plot, format="pdf")
plt.close()

print(f"Saved pairwise scatter plot to {output_plot}")
