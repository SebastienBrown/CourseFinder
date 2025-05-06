#!/bin/bash
#SBATCH --job-name=courses
#SBATCH --ntasks=1                              # number of scripts that can be run simultaneously
#SBATCH --cpus-per-task=4                       # Each script gets 16 CPU cores

#SBATCH --mem=32GB                              # Total memory allocation
#SBATCH --time=10:00:00                          # Adjust time as needed
#SBATCH --partition=sched_mit_econ

#SBATCH --mail-type=all                         # send email on job start, end and fault
#SBATCH --mail-user=hnakazawa@povertyactionlab.org
#SBATCH --output=CourseFinder/logs/llm_parsing_%A.txt

source /orcd/software/core/001/centos7/pkg/miniforge/24.3.0-0/etc/profile.d/conda.sh
conda activate course_venv

echo "Parsing course json files to separate separate description from requirements:"
python "CourseFinder/llm_parsing.py"