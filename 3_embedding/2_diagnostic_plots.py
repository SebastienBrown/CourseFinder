import torch
import torch.nn as nn
import torch.nn.functional as F
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from transformers import AutoTokenizer, AutoModel
import random
import json
import pandas as pd
import glob
import numpy as np
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.backends.backend_pdf import PdfPages
load_dotenv()

# ========================================
# Configuration 
# ========================================
dropbox = os.environ["DROPBOX"]
code = os.environ["CODE"]

json_path = os.environ["CONTRASTIVE_JSON_PATH"]
embeddings_path = os.environ["EMBEDDINGS_PATH"]
diagnostics_path = os.environ["CONTRASTIVE_DIAGNOSTICS_PATH"]

model = os.environ["MODEL"]
mode = os.environ["MODE"]
pdf_path = os.environ["DIAGNOSTIC_PLOTS_PDF"]

random_seed = int(os.environ["CONTRASTIVE_RANDOM_SEED"])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Set random seed for reproducibility
random.seed(random_seed)
np.random.seed(random_seed)
torch.manual_seed(random_seed)

# ========================================
# Prepare embeddings
# ========================================
# Load embeddings
print("Loading embeddings...")
embeddings_map = {}

# Load from multiple files in directory
embedding_files = [f for f in glob.glob(os.path.join(embeddings_path, "output_embeddings_*.json"))
                  if len(f.split('_')[-1].replace('.json', '')) == 5 and 
                  f.split('_')[-1].replace('.json', '')[:4].isdigit() and 
                  f.split('_')[-1].replace('.json', '')[4].isalpha()]
print(f"Found {len(embedding_files)} embedding files")

for file_path in embedding_files:
    # Extract semester from filename
    filename = os.path.basename(file_path)
    semester = filename.replace("output_embeddings_", "").replace(".json", "")
    print(f"Loading embeddings for semester: {semester}")
    
    with open(file_path, 'r') as f:
        embeddings_data = json.load(f)
    
    # Create a mapping from (semester, course_code) to embedding
    for course in embeddings_data:
        course_codes = course.get('course_codes', [])
        if isinstance(course_codes, str):
            course_codes = [course_codes]
        
        embedding = course.get('embedding', [])
        if embedding:
            for course_code in course_codes:
                embeddings_map[(semester, course_code)] = embedding

print(f"Loaded {len(embeddings_map)} embeddings")

# ========================================
# Load course data for title lookup
# ========================================
print("Loading course data...")
with open(json_path, 'r') as f:
    course_data = json.load(f)

# ========================================
# Prepare diagnostics data
# ========================================
# Get testing rows from diagnostics CSV (same logic as in contrastive learning)
df = pd.read_csv(diagnostics_path)
print(f"Loaded diagnostics dataset with {len(df)} rows")

# Parse course information from each row of the diagnostics data
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

# Use all rows instead of just testing set
all_rows = all_courses
print(f"Using all {len(all_rows)} rows")

# ========================================
# Generate Plots
# ========================================
# Create a single PDF with multiple pages
successful_plots = 0
plots_per_page = 4

with PdfPages(pdf_path) as pdf:
    for i, row_data in enumerate(all_rows):
        print(f"Processing row {i + 1}/{len(all_rows)}...")
        
        # Extract course info
        courses = ['A', 'B', 'C', 'D']
        course_infos = [row_data[j]['full_info'] for j in range(4)]
        
        # Get embeddings for each course
        embeddings_list = []
        course_labels = []
        course_titles = []
        
        for j, course_info in enumerate(course_infos):
            semester, course_code = course_info.split(', ')
            embedding = embeddings_map.get((semester, course_code))
            
            if embedding is None:
                print(f"Warning: No embedding found for {course_info}")
                break
            
            embeddings_list.append(embedding)
            
            # Get course title for labeling
            title = course_code  # Default to course code
            for course in course_data:
                if course.get('semester') == semester:
                    course_codes = course.get('course_codes', [])
                    if isinstance(course_codes, str):
                        course_codes = [course_codes]
                    if course_code in course_codes:
                        title = course.get('course_title', course_code)
                        break
            course_labels.append(f"{courses[j]}: {course_code}\n{semester}")
            # Store titles separately for legend
            course_titles.append(title)
        
        if len(embeddings_list) != 4:
            continue
        
        # Transform embeddings to 2D using PCA and transform so C and D span horizontal axis
        if len(embeddings_list) != 4:
            print(f"Error: Expected 4 embeddings, got {len(embeddings_list)}")
            continue
        
        # Stack embeddings
        embeddings_array = np.array(embeddings_list)
        
        # Apply PCA to get 2D projection
        pca = PCA(n_components=2)
        projected = pca.fit_transform(embeddings_array)
        
        # Transform so that courses C and D (indices 2 and 3) span the horizontal axis
        # Get the vector from C to D
        c_to_d = projected[3] - projected[2]  # D - C
        c_to_d_normalized = c_to_d / np.linalg.norm(c_to_d)
        
        # Create rotation matrix to align C-D with horizontal axis
        # The angle to rotate is the angle between c_to_d and the positive x-axis
        angle = np.arctan2(c_to_d_normalized[1], c_to_d_normalized[0])
        rotation_matrix = np.array([
            [np.cos(-angle), -np.sin(-angle)],
            [np.sin(-angle), np.cos(-angle)]
        ])
        
        # Apply rotation
        transformed_2d = projected @ rotation_matrix.T
        
        # Create subplot position (2x2 grid)
        plot_position = successful_plots % plots_per_page
        
        # Create new page if needed
        if plot_position == 0:
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))  # Landscape layout
            fig.suptitle(f'{model.upper()}, {mode.replace("_", " ").title()} - Page {(successful_plots // plots_per_page) + 1}', fontsize=16)
            axes = axes.flatten()  # Flatten to 1D array for easier indexing
        
        ax = axes[plot_position]
        
        # Remove top and right spines (box around figure)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Make the plot square
        ax.set_aspect('equal')
        
        # Plot points
        colors = ['red', 'blue', 'green', 'orange']
        for j, (point, label, color) in enumerate(zip(transformed_2d, course_labels, colors)):
            ax.scatter(point[0], point[1], c=color, s=80, alpha=0.7)
            ax.annotate(label, (point[0], point[1]), 
                       xytext=(3, 3), textcoords='offset points',
                       fontsize=8, ha='left', va='bottom')
        
        # Add connecting lines between C and D (horizontal axis)
        ax.plot([transformed_2d[2][0], transformed_2d[3][0]], 
                [transformed_2d[2][1], transformed_2d[3][1]], 
                'k--', alpha=0.5, linewidth=1.5)
        
        # Make x and y axes span the same distance
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        x_range = x_max - x_min
        y_range = y_max - y_min
        max_range = max(x_range, y_range)
        
        # Center the ranges and set equal spans
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        ax.set_xlim(x_center - max_range/2, x_center + max_range/2)
        ax.set_ylim(y_center - max_range/2, y_center + max_range/2)
        
        # Add grid and labels
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('PC1 (C-D aligned)', fontsize=9)
        ax.set_ylabel('PC2', fontsize=9)
        ax.set_title(f'Row {i + 1}', fontsize=10)
        
        # Add custom legend below each individual subplot
        legend_elements_titles = [plt.Line2D([0], [0], marker='o', color='w', 
                                           markerfacecolor=color, markersize=8, label=title)
                                for color, title in zip(colors, course_titles)]
        
        # Position legend below the individual subplot
        ax.legend(handles=legend_elements_titles, fontsize=7, 
                 loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=1, 
                 frameon=False)
        
        successful_plots += 1
        
        # Save page if it's full or if it's the last plot
        if plot_position == plots_per_page - 1 or i == len(all_rows) - 1:
            # Keep unused subplots visible but empty to maintain consistent page size
            if i == len(all_rows) - 1 and plot_position < plots_per_page - 1:
                for unused_pos in range(plot_position + 1, plots_per_page):
                    # Make the subplot completely empty but keep it in the layout
                    axes[unused_pos].set_xticks([])
                    axes[unused_pos].set_yticks([])
                    axes[unused_pos].set_frame_on(False)
                    axes[unused_pos].text(0.5, 0.5, '', ha='center', va='center', transform=axes[unused_pos].transAxes)
            
            plt.tight_layout(rect=[0, 0.35, 1, 0.95])  # Leave space at bottom for individual legends
            # Save without bbox_inches='tight' to maintain consistent page size
            pdf.savefig(fig, dpi=300)
            plt.close()

print(f"\nGenerated {successful_plots} diagnostic plots in single PDF")
print(f"PDF saved to: {pdf_path}")
