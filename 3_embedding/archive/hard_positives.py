import json
import random

# Load course data
with open("amherst_courses_all.json", "r") as f:
    data = json.load(f)

# Extract texts (adjust key if needed)
texts = [entry["description"] if isinstance(entry, dict) else entry for entry in data]

# Number of triplets to sample
num_triplets = 300  # You can change this

# Set random seed for reproducibility
random.seed(42)

# Sample triplets
triplets = []
for _ in range(num_triplets):
    triplet = random.sample(texts, 3)
    triplets.append(triplet)

# Optionally save to file for manual annotation
with open("triplets_to_annotate.json", "w") as f:
    json.dump(triplets, f, indent=2)

print(f"Saved {num_triplets} random triplets for annotation.")
