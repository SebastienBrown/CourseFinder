#!/bin/bash
#SBATCH --job-name=score_calc
#SBATCH --partition=sched_mit_econ
#SBATCH --cpus-per-task=1
#SBATCH --ntasks=1
#SBATCH --time=08:00:00
#SBATCH --mem=160G

#SBATCH --output=/orcd/home/002/hnaka24/CourseFinder/logs/6_master_%j.txt
#SBATCH --mail-user=hnakazawa@povertyactionlab.org
#SBATCH --mail-type=all

source /orcd/software/core/001/centos7/pkg/miniforge/24.3.0-0/etc/profile.d/conda.sh
conda activate course_venv
pip install -r requirements.txt
module load python/3.9.4

# Change to your code directory
cd /orcd/home/002/hnaka24/CourseFinder/diversity_score_analysis

# -----------------------------
# Configuration and Environment Variables
# -----------------------------
export FILEDATE='20250820'

# HPC paths
export DROPBOX='/orcd/pool/003/hnaka24/CourseFinder'
export CODE='/orcd/home/002/hnaka24/CourseFinder'

# Set all the environment variables your Python scripts need
export INPUT_JSON="${DROPBOX}/data/2_intermediate/3_similarity/gpt_off_the_shelf/output_similarity_all.json"
export INPUT_PATH="${DROPBOX}/data/1_raw/user_courses/user_courses_${FILEDATE}.csv"
export OUTPUT_GRAPH_UNFIL="${DROPBOX}/output/6_scores/graph_all_unfiltered.gexf"
export OUTPUT_MAJOR_DATA="${DROPBOX}/data/2_intermediate/5_scores/major_scores_panel.csv"
export OUTPUT_PLOT="${DROPBOX}/output/6_scores/major_scores_scatter.pdf"
export MIN_SIM='0.75'
export KEEP_TOP_K='None'

# Create necessary directories
mkdir -p "${DROPBOX}/data/2_intermediate/5_scores/"
mkdir -p "${DROPBOX}/output/6_scores/"
mkdir -p logs

# Print job information
echo "==============================================="
echo "Starting master analysis pipeline..."
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Date: $FILEDATE"
echo "==============================================="


# -----------------------------
# Step 1: Graph analysis
# -----------------------------
echo ""
echo "==== Running graph analysis... ===="

# Students
python 1_major_graph.py
if [ $? -ne 0 ]; then
    echo "✗ Major-level graph analysis failed"
    exit 1
fi
echo "✓ Major-level graph analysis completed"

# -----------------------------
# Step 2: Scatter plots
# -----------------------------
echo ""

echo "==== Running scatter plot generation... ===="

python 2_scatter_plot.py
if [ $? -ne 0 ]; then
    echo "✗ Scatter plot generation failed"
    exit 1
fi
echo "✓ Scatter plot generation completed"

echo ""
echo "🎉 Master analysis pipeline completed successfully!"
