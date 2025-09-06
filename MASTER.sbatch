#!/bin/bash
#SBATCH --job-name=courses
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4

#SBATCH --mem=200GB
#SBATCH --time=30:00:00
#SBATCH --partition=sched_mit_econ

#SBATCH --mail-type=all
#SBATCH --mail-user=hnakazawa@povertyactionlab.org
#SBATCH --output=logs/MASTER_%A.txt

source /orcd/software/core/001/centos7/pkg/miniforge/24.3.0-0/etc/profile.d/conda.sh
conda activate course_venv

# Change to your code directory
cd /orcd/home/002/hnaka24/CourseFinder

# -----------------------------
# Configuration and Environment Variables
# -----------------------------
# HPC paths
export DROPBOX='/orcd/pool/003/hnaka24/CourseFinder'
export CODE='/orcd/home/002/hnaka24/CourseFinder'

# Annotated Diagnostics Dataset
export FILEDATE='20250830'
export CONTRASTIVE_DIAGNOSTICS_PATH="${DROPBOX}/data/1_raw/diagnostics/diagnostics_${FILEDATE}.csv"

# Configuration: (model, mode, contrastive_alpha)
MODEL_CONFIGS=(
    "gpt:off_the_shelf:"
    "sbert:off_the_shelf:"
    "sbert:by_major:0.0"
    "sbert:manual:0.3"
)

# Export MODEL_CONFIGS as space-separated string for Python script
export MODEL_CONFIGS_STR="${MODEL_CONFIGS[*]}"

# Model names
export GPT_MODEL_NAME="text-embedding-3-small"
export SBERT_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2"

# Contrastive learning configuration
export CONTRASTIVE_JSON_PATH="${DROPBOX}/data/2_intermediate/1_llm_cleaned/amherst_courses_all.json"

export CONTRASTIVE_DROPOUT_RATE="0.1"
export CONTRASTIVE_MAX_SELF_SUPERVISED="10000"  # Cap how many course descriptions to use
export CONTRASTIVE_NUM_EPOCHS="25"
export CONTRASTIVE_LR="1e-5"
export CONTRASTIVE_RANDOM_SEED="42"  # Random seed for reproducible splits

# Semester list
export SEMESTERS="0910F,0910S,1011F,1011S,1112F,1112S,1213F,1213S,1314F,1314S,1415F,1415S,1516F,1516S,1617F,1617S,1718F,1718S,1819F,1819S,1920F,1920S,2021F,2021J,2021S,2122F,2122J,2122S,2223F,2223S,2324F,2324S,2425F,2425S,2526F,2526S"

# Common file paths
export LLM_CLEANED_DIR="${DROPBOX}/data/2_intermediate/1_llm_cleaned"
export DIAGNOSTIC_PLOTS_SUBDIR="${DROPBOX}/output/3_embedding/diagnostic_plots/"
export SIMILARITY_DENSITY_SUBDIR="${DROPBOX}/output/3_embedding/similarity_density/"
export COMBINED_PDF="${DROPBOX}/output/3_embedding/embedding_plots_all.pdf"

# Create necessary directories
mkdir -p "${DIAGNOSTIC_PLOTS_SUBDIR}"
mkdir -p "${SIMILARITY_DENSITY_SUBDIR}"

# Loop through model configurations
for i in "${!MODEL_CONFIGS[@]}"; do
    CONFIG="${MODEL_CONFIGS[$i]}"
    # Parse the configuration string using parameter expansion
    MODEL=$(echo "$CONFIG" | cut -d: -f1)
    MODE=$(echo "$CONFIG" | cut -d: -f2)
    ALPHA=$(echo "$CONFIG" | cut -d: -f3)
    
    echo ""
    echo "==============================================="
    echo "Processing model: $MODEL, mode: $MODE, alpha: $ALPHA"
    echo "==============================================="
    
    # Set model-specific environment variables
    export MODEL="$MODEL"
    export MODE="$MODE"
    
    # Set model directory based on MODEL and MODE
    export CONTRASTIVE_SAVE_DIR="${CODE}/3_embedding/model/${MODEL}_${MODE}/"
    mkdir -p "${CONTRASTIVE_SAVE_DIR}"
    
    # Only set CONTRASTIVE_ALPHA if it's not empty (relevant for contrastive learning modes)
    if [ -n "$ALPHA" ]; then
        export CONTRASTIVE_ALPHA="$ALPHA"
    fi
    
    # Update file paths based on current model and mode
    export EMBEDDINGS_PATH="${DROPBOX}/data/2_intermediate/2_embeddings/${MODEL}_${MODE}/"
    export SIMILARITY_OUTPUT_FILE="${DROPBOX}/data/2_intermediate/3_similarity/${MODEL}_${MODE}/output_similarity_all.json"
    export SIMILARITY_DENSITY_PDF="${SIMILARITY_DENSITY_SUBDIR}/similarity_density_${MODEL}_${MODE}.pdf"
    export DIAGNOSTIC_PLOTS_PDF="${DIAGNOSTIC_PLOTS_SUBDIR}/diagnostic_plots_${MODEL}_${MODE}_all.pdf"
    
    # Create necessary directories for current model
    mkdir -p "${EMBEDDINGS_PATH}"
    mkdir -p "${DROPBOX}/data/2_intermediate/3_similarity/${MODEL}_${MODE}/"
    mkdir -p "${DROPBOX}/output/4_similarity/"
    
    # Print job information
    echo "==============================================="
    echo "Starting embedding and similarity pipeline..."
    echo "Job ID: $SLURM_JOB_ID"
    echo "Node: $SLURMD_NODENAME"
    echo "Embedding Model: $MODEL"
    echo "Mode: $MODE"
    echo "==============================================="

    # -----------------------------
    # Compute Embeddings
    # -----------------------------
    # Step 0: Contrastive Learning (Optional)
    # if [ "$MODE" != "off_the_shelf" ]; then
    #     echo ""
    #     echo "==== Running contrastive learning... ===="
    #     python "3_embedding/0_contrastive_learning.py"
    #     if [ $? -ne 0 ]; then
    #         echo "✗ Contrastive learning failed"
    #         exit 1
    #     fi
    #     echo "✓ Contrastive learning completed"
    # else
    #     echo ""
    #     echo "==== Skipping contrastive learning (MODE=off_the_shelf) ===="
    # fi

    # # Step 1: Compute embeddings for courses
    # echo ""
    # echo "==== Computing embeddings for courses... ===="
    # python "3_embedding/1_embedding.py"
    # if [ $? -ne 0 ]; then
    #     echo "✗ Embedding computation failed"
    #     exit 1
    # fi
    # echo "✓ Embedding computation completed"

    # Step 2: Generate diagnostic plots
    echo ""
    echo "==== Generating diagnostic plots... ===="
    python "3_embedding/2_diagnostic_plots.py"
    if [ $? -ne 0 ]; then
        echo "✗ Diagnostic plots generation failed"
        exit 1
    fi
    echo "✓ Diagnostic plots generation completed"


    # -----------------------------
    # Compute Similarity Scores
    # -----------------------------
    # Step 1: Compute similarity scores for courses
    # echo ""
    # echo "==== Computing similarity scores for courses... ===="
    # python "4_similarity/1_similarity_all.py"
    # if [ $? -ne 0 ]; then
    #     echo "✗ Similarity computation failed"
    #     exit 1
    # fi
    # echo "✓ Similarity computation completed"

    # Step 2: Create density plot of similarity scores
    echo ""
    echo "==== Creating density plot of similarity scores... ===="
    python "4_similarity/2_similarity_density.py"
    if [ $? -ne 0 ]; then
        echo "✗ Density plot creation failed"
        exit 1
    fi
    echo "✓ Density plot creation completed"


    # -----------------------------
    # Compute Coordinates and Similar Courses
    # -----------------------------
    # Step 1: Compute coordinates
    # echo ""
    # echo "==== Computing coordinates... ===="
    # python "5_webapp/1_tsne_coords.py"
    # if [ $? -ne 0 ]; then
    #     echo "✗ Coordinates computation failed"
    #     exit 1
    # fi
    # echo "✓ Coordinates computation completed"

    # # Step 2: Append similar courses
    # echo ""
    # echo "==== Appending similar courses... ===="
    # python "5_webapp/2_append_similar_courses.py"
    # if [ $? -ne 0 ]; then
    #     echo "✗ Appending similar courses failed"
    #     exit 1
    # fi
    # echo "✓ Appending similar courses completed"


    # -----------------------------
    echo ""
    echo "🎉 Processing completed for model: $MODEL"
    echo "==============================================="
    
done

# -----------------------------
# Concatenate PDFs
# -----------------------------
echo ""
echo "==== Concatenating PDFs... ===="

# Create concatenated PDFs using Python script
echo "Creating combined embedding plots PDF..."
echo "Note: This will concatenate PDFs from all model-mode combinations"
python concatenate_pdfs.py
if [ $? -ne 0 ]; then
    echo "✗ PDF concatenation failed"
    exit 1
fi

echo "✓ PDF concatenation completed"
echo "Combined embedding plots: ${COMBINED_PDF}"

echo ""
echo "🎉 Embedding and similarity pipeline completed successfully for all models!"