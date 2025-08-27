#!/bin/bash
#SBATCH --job-name=create_graph
#SBATCH --partition=sched_mit_econ
#SBATCH --cpus-per-task=4
#SBATCH --ntasks=1
#SBATCH --time=08:00:00
#SBATCH --mem=280G

#SBATCH --output=/orcd/home/002/hnaka24/CourseFinder/logs/6_create_graph_%j.txt
#SBATCH --mail-user=hnakazawa@povertyactionlab.org
#SBATCH --mail-type=all

source /orcd/software/core/001/centos7/pkg/miniforge/24.3.0-0/etc/profile.d/conda.sh
conda activate course_venv
pip install -r requirements.txt
module load python/3.9.4

# Change to your code directory
cd /orcd/home/002/hnaka24/CourseFinder/6_graph

# -----------------------------
# Configuration and Environment Variables
# -----------------------------
# HPC paths
export DROPBOX='/orcd/pool/003/hnaka24/CourseFinder'
export CODE='/orcd/home/002/hnaka24/CourseFinder'

# Set all the environment variables your Python scripts need
export INPUT_JSON="${DROPBOX}/data/2_intermediate/3_similarity/gpt_off_the_shelf/output_similarity_all.json"
export OUTPUT_GRAPH_UNFIL="${DROPBOX}/output/6_scores/graph_all_unfiltered.gexf"

export MIN_SIM='0.75'
export KEEP_TOP_K='None'

# Create necessary directories
mkdir -p "${DROPBOX}/data/2_intermediate/5_scores/"
mkdir -p "${DROPBOX}/output/6_scores/"
mkdir -p logs

# Print job information
echo "==============================================="
echo "Creating graph..."
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Date: $FILEDATE"
echo "==============================================="


# -----------------------------
# Create unfiltered graph
# -----------------------------
python create_graph.py
if [ $? -ne 0 ]; then
    echo "✗ Graph generation failed"
    exit 1
fi
echo "✓ Graph generation completed"