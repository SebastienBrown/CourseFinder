from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# -----------------------------
# Paths
# -----------------------------
filedate = os.environ['FILEDATE']
OUTPUT_STUDENT_DATA = Path(os.environ['OUTPUT_STUDENT_DATA'])
OUTPUT_PLOT = os.environ['OUTPUT_PLOT']

# -----------------------------
# Load data
# -----------------------------
print(f"Loading data from {OUTPUT_STUDENT_DATA}")
results_df = pd.read_csv(OUTPUT_STUDENT_DATA)

# -----------------------------
# Export scatter plot
# -----------------------------
print(f"Loaded {len(results_df)} rows from {OUTPUT_STUDENT_DATA.resolve()}")
print(results_df.head(10))

# Select the columns you want to include in the pairwise scatter plot
plot_vars = ["NumCourses", "NumDisciplines", "EntropyNormalized", "HHIIndex", "n_components", "avg_distance", "max_distance"]

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
plt.savefig(OUTPUT_PLOT, format="pdf")
plt.close()

print(f"Saved pairwise scatter plot to {OUTPUT_PLOT}")
