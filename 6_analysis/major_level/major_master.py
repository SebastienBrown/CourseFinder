import os
import subprocess
import sys

# -----------------------------
# Configuration
# -----------------------------
filedate = '20250820'

# User-specific paths
if os.getenv('USER') == 'hnaka24':
    # Main directories
    dropbox = '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/'
    code = '/Users/hnaka24/Desktop/code/CourseFinder/'

    INPUT_JSON = f'{dropbox}data/2_intermediate/3_similarity/gpt_off_the_shelf/output_similarity_all.json'
    INPUT_PATH = f"{dropbox}data/1_raw/user_courses/user_courses_{filedate}.csv"
    OUTPUT_GRAPH_UNFIL = f"{dropbox}/output/6_scores/graph_all_unfiltered.gexf"
    OUTPUT_STUDENT_DATA = f"{dropbox}/data/2_intermediate/5_scores/student_scores_${filedate}.csv"
    OUTPUT_MAJOR_DATA = f"{dropbox}/data/2_intermediate/5_scores/major_scores_panel.csv"
    OUTPUT_PLOT = f"{dropbox}output/6_scores/student_scores_scatter_{filedate}.pdf"

    LOG_PATH = f"{code}logs/6_master.txt"

    # Output directories
    output_dir = f"{dropbox}data/2_intermediate/5_scores/"
    plot_dir = f"{dropbox}output/6_scores/"

    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(plot_dir, exist_ok=True)

else:
    dropbox = './data/'
    code = './'

# Set environment variables for all scripts
os.environ['FILEDATE'] = filedate
os.environ['INPUT_JSON'] = INPUT_JSON
os.environ['INPUT_PATH'] = INPUT_PATH
os.environ['OUTPUT_GRAPH_UNFIL'] = OUTPUT_GRAPH_UNFIL
os.environ['OUTPUT_STUDENT_DATA'] = OUTPUT_STUDENT_DATA
os.environ['OUTPUT_MAJOR_DATA'] = OUTPUT_MAJOR_DATA
os.environ['OUTPUT_PLOT'] = OUTPUT_PLOT
os.environ['MIN_SIM'] = '0.75'
os.environ['KEEP_TOP_K'] = 'None'  # Use 'None' string, will be handled in individual scripts

print("Starting master analysis pipeline...")
print(f"User: {os.getenv('USER')}")
print(f"Date: {filedate}")

# -----------------------------
# Step 1: Calculate discrete measures for students
# -----------------------------
print("\n" + "="*50)
print("Running diversity score calculation...")
print("="*50)

result = subprocess.run([sys.executable, '1_discrete_scores.py'])

if result.returncode == 0:
    print("✓ Diversity score calculation completed")
else:
    print(f"✗ Diversity score calculation failed with return code {result.returncode}")
    sys.exit(1)

# -----------------------------
# Step 2: Graph analysis
# -----------------------------
print("\n" + "="*50)
print("Running graph analysis...")
print("="*50)

# Students
result = subprocess.run([sys.executable, '2_student_graph.py'])

if result.returncode == 0:
    print("✓ Student-level graph analysis completed")
else:
    print(f"✗ Student-level graph analysis failed with return code {result.returncode}")
    sys.exit(1)

# -----------------------------
# Step 3: Scatter plots
# -----------------------------
print("\n" + "="*50)
print("Running scatter plot generation...")
print("="*50)

result = subprocess.run([sys.executable, '3_scatter_plot.py'])

if result.returncode == 0:
    print("✓ Scatter plot generation completed")
else:
    print(f"✗ Scatter plot generation failed with return code {result.returncode}")
    sys.exit(1)

print("\n" + "="*50)
print("🎉 Master analysis pipeline completed successfully!")
print("="*50)
