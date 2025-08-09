import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Path to the similarity data
SIMILARITY_FILE = 'similarity/output_similarity_all.json'
OUTPUT_PDF = '4_similarity/similarity_density.pdf'

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