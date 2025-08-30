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
load_dotenv()

# ========================================
# Configuration 
# ========================================
dropbox = os.environ.get("DROPBOX", '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/')
code = os.environ.get("CODE", '/Users/hnaka24/Desktop/code/CourseFinder/')

json_path = os.environ.get("CONTRASTIVE_JSON_PATH", dropbox + 'data/2_intermediate/1_llm_cleaned/amherst_courses_2324S.json')
embeddings_path = os.environ.get("EMBEDDINGS_PATH", dropbox + 'data/2_intermediate/2_embeddings/amherst_courses_2324S.json')
diagnostics_path = os.environ.get("CONTRASTIVE_DIAGNOSTICS_PATH", dropbox + 'data/1_raw/diagnostics/diagnostics_20250827.csv')
output_dir = os.environ.get("DIAGNOSTIC_PLOTS_DIR", dropbox + 'output/3_embedding/')
os.makedirs(output_dir, exist_ok=True)

model = os.environ.get("MODEL", "gpt")
mode = os.environ.get("MODE", "off_the_shelf")

model_name = os.environ.get("CONTRASTIVE_MODEL_NAME", 'sentence-transformers/all-MiniLM-L6-v2')
sbert_mode = os.environ.get("SBERT_MODE", "off_the_shelf")
sbert_model_dir = os.environ.get("SBERT_MODEL_DIR", code + "3_embedding/sbert_contrastive_model")
random_seed = int(os.environ.get("CONTRASTIVE_RANDOM_SEED", "42"))

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
embedding_files = glob.glob(os.path.join(embeddings_path, "output_embeddings_*.json"))
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

# Split data using same logic as contrastive learning (80/20 split)
n_total = len(all_courses)
n_train = int(n_total * 0.8)  # 80% for training

# Shuffle and split
indices = list(range(n_total))
random.shuffle(indices)

# Testing rows are the validation rows (last 20%)
test_indices = indices[n_train:]
test_rows = [all_courses[i] for i in test_indices]

print(f"Extracted {len(test_rows)} testing rows")

# ========================================
# Generate Plots
# ========================================
successful_plots = 0
for i, row_data in enumerate(test_rows):
    print(f"Processing row {i + 1}/{len(test_rows)}...")
    
    # Extract course info
    courses = ['A', 'B', 'C', 'D']
    course_infos = [row_data[j]['full_info'] for j in range(4)]
    
    # Get embeddings for each course
    embeddings_list = []
    course_labels = []
    
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
                    title = course.get('title', course_code)
                    break
        course_labels.append(f"{course_code}\n{semester}\n{title}")
    
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
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot points
    colors = ['red', 'blue', 'green', 'orange']
    for j, (point, label, color) in enumerate(zip(transformed_2d, course_labels, colors)):
        ax.scatter(point[0], point[1], c=color, s=100, alpha=0.7)
        ax.annotate(label, (point[0], point[1]), 
                   xytext=(5, 5), textcoords='offset points',
                   fontsize=10, ha='left', va='bottom',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # Add connecting lines between C and D (horizontal axis)
    ax.plot([transformed_2d[2][0], transformed_2d[3][0]], 
            [transformed_2d[2][1], transformed_2d[3][1]], 
            'k--', alpha=0.5, linewidth=2)
    
    # Add grid and labels
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Principal Component 1 (C-D aligned)')
    ax.set_ylabel('Principal Component 2')
    ax.set_title(f'Diagnostic Row {i + 1}: Course Embeddings Projection')
    
    # Add legend
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                 markerfacecolor=color, markersize=10, label=courses[j])
                      for j, color in enumerate(colors)]
    ax.legend(handles=legend_elements, title='Courses')
    
    # Save plot
    plt.tight_layout()
    plt.savefig(f'{output_dir}diagnostic_plots_{model}_{mode}_{i+1}.pdf', dpi=300, bbox_inches='tight')
    plt.close()
    
    successful_plots += 1

print(f"\nGenerated {successful_plots}/{len(test_rows)} diagnostic plots")
print(f"Plots saved to: {output_dir}")
