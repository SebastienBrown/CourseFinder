import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ==== Configuration ====
dropbox = '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/'
code = '/Users/hnaka24/Desktop/code/CourseFinder/'
model = "sbert"
mode = "off_the_shelf"

SIMILARITY_FILE = dropbox + f'data/2_intermediate/3_similarity/{model}_{mode}/output_similarity_2324S.json'
OUTPUT_PDF = dropbox + 'output/4_similarity/similarity_density_sbert_offshelf.pdf'

# ==== Script ====
# Load the similarity data
with open(SIMILARITY_FILE, 'r') as f:
    data = json.load(f)

# Extract all similarity scores, avoiding double-counting
similarity_scores = []
seen_pairs = set()
for course in data:
    main_codes = tuple(course.get('course_codes', []))
    main_semester = course.get('semester', None)
    for comp in course.get('compared_courses', []):
        comp_codes = tuple(comp.get('course_codes', []))
        comp_semester = comp.get('semester', None)
        # Create a unique, order-independent key for the pair (including semester)
        pair_key = tuple(sorted([(main_semester, main_codes), (comp_semester, comp_codes)]))
        if pair_key not in seen_pairs:
            score = comp.get('similarity_score')
            if score is not None:
                similarity_scores.append(score)
            seen_pairs.add(pair_key)

# Plot density
plt.figure(figsize=(8, 5))
sns.kdeplot(similarity_scores, fill=True, bw_adjust=0.2)
plt.title('Density of Similarity Scores (No Double Counting)')
plt.xlabel('Similarity Score')
plt.ylabel('Density')

# Set x-axis to span 0 to 1 with labels at every 0.1
plt.xlim(0, 1)
plt.xticks(np.arange(0, 1.1, 0.1))

plt.tight_layout()
plt.savefig(OUTPUT_PDF)
print(f"Density plot saved to {OUTPUT_PDF}") 