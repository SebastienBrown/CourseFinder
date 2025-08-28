import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ==== Configuration ====
dropbox = '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/'
code = '/Users/hnaka24/Desktop/code/CourseFinder/'
model = "sbert"
mode = "off_the_shelf"

input_path = dropbox + 'data/2_intermediate/4_coordinates/tsne_coords_2324S_sbert_offshelf.json'
output_path = dropbox + 'output/4_similarity/tsne_map_2324S_sbert_offshelf.pdf'

# === Tranche shapes mapping (matplotlib markers) ===
TRANCHE_SHAPES = {
    "Arts": "o",            # circle
    "Humanities": "s",      # square
    "Sciences": "^",        # triangle up
    "Social Sciences": "*", # star
    "First Year Seminar": "D",  # diamond (closest to doubleCircle)
}

# === Tranches to major prefixes ===
TRANCHES = {
    "Arts": ["ARCH", "ARHA", "MUSI", "MUSL", "THDA"],
    "Humanities": [
        "AAPI", "AMST", "ARAB", "ASLC", "BLST", "CHIN", "CLAS", "COLQ",
        "EDST", "ENGL", "ENST", "EUST", "FAMS", "FREN", "GERM", "GREE",
        "HIST", "JAPA", "LATI", "LJST", "LLAS", "PHIL", "RELI", "RUSS",
        "SPAN", "SWAG", "WAGS",
    ],
    "Sciences": [
        "ASTR", "BCBP", "BIOL", "CHEM", "COSC", "GEOL", "MATH", "NEUR", "PHYS", "STAT",
    ],
    "Social Sciences": ["ANTH", "ECON", "POSC", "PSYC", "SOCI"],
    "First Year Seminar": ["FYSE"],
}

def get_tranche(major_code):
    for tranche, majors in TRANCHES.items():
        if major_code in majors:
            return tranche
    return "Unknown"

def extract_major_code(codes):
    # first 4 chars of first code or "UNK"
    if codes and len(codes) > 0 and len(codes[0]) >= 4:
        return codes[0][:4]
    return "UNK"

# Load your JSON file
with open(input_path) as f:
    data = json.load(f)

# Get unique majors for coloring
unique_majors = sorted({extract_major_code(d["codes"]) for d in data})

# Use a pastel discrete palette cycling through:
PASTEL_COLORS = [
    "#AEC6CF", "#FFDAB9", "#77DD77", "#F49AC2", "#B39EB5", 
    "#FFB347", "#CFCFC4", "#FDFD96", "#C23B22", "#8ED1FC",
    "#FF6961", "#CB99C9", "#F8B195", "#6C5B7B", "#355C7D"
]
# Cycle through colors for majors
color_cycle = (PASTEL_COLORS * ((len(unique_majors) // len(PASTEL_COLORS)) + 1))[:len(unique_majors)]
major_color_map = {major: color for major, color in zip(unique_majors, color_cycle)}

# Create figure in landscape (A4)
fig, ax = plt.subplots(figsize=(11.7, 8.3))  # width > height

for obj in data:
    x, y = obj["x"], obj["y"]
    major_code = extract_major_code(obj["codes"])
    tranche = get_tranche(major_code)
    marker = TRANCHE_SHAPES.get(tranche, "o")
    color = major_color_map.get(major_code, "#000000")
    ax.scatter(x, y, marker=marker, color=color, s=80, edgecolor='k', linewidth=0.5)
    label = obj["codes"][0] if obj["codes"] else "N/A"
    ax.text(x, y, label, fontsize=6, ha='right', va='bottom')  # smaller font size

# Legend for shapes (Tranches)
shape_legend = [plt.Line2D([0], [0], marker=m, color='w', label=t,
                          markerfacecolor='gray', markersize=10, markeredgecolor='k')
                for t, m in TRANCHE_SHAPES.items()]

# Legend for colors (Majors)
color_legend = [mpatches.Patch(color=major_color_map[m], label=m) for m in unique_majors]

# Place legends on the LEFT in 3 columns
from matplotlib.legend import Legend

# Create empty placeholder axis on left side for legends
fig.subplots_adjust(left=0.3, right=0.95)  # Leave room on left for legend

# Create a dedicated axis for the legend on the left side (off plot)
legend_ax = fig.add_axes([0.01, 0.05, 0.25, 0.9])  # [left, bottom, width, height]
legend_ax.axis('off')

# Combine legends in one legend box with two sections:
# First shapes (tranches)
legend1 = Legend(legend_ax, handles=shape_legend, labels=[t for t in TRANCHE_SHAPES.keys()],
                 title="Tranche (Shape)", loc="upper left", frameon=False)

# Add to axis
legend_ax.add_artist(legend1)

# Then color legend, placed below shape legend with 3 columns
legend2 = Legend(legend_ax, handles=color_legend, labels=[m for m in unique_majors],
                 title="Majors (Color)", loc="lower left", frameon=False, ncol=3)

legend_ax.add_artist(legend2)

# Axis labels and title
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_title("Course Coordinates: Colors by Major, Shapes by Tranche")
ax.grid(True)

# Save to PDF
plt.savefig(output_path, bbox_inches='tight')
plt.close()

print(f"Map saved to {output_path}") 