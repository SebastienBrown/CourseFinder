import sys
import os
from PyPDF2 import PdfMerger

# ========================================
# Configuration
# ========================================
# Get output directory and build file paths dynamically
dropbox = os.environ.get("DROPBOX")
output_pdf = os.environ.get("COMBINED_PDF")

if not dropbox or not output_pdf:
    print("Error: DROPBOX or COMBINED_PDF environment variable not set")
    sys.exit(1)

# Get model configurations from environment variable (same as MASTER.sbatch)
model_configs_str = os.environ.get("MODEL_CONFIGS_STR")
if not model_configs_str:
    print("Error: MODEL_CONFIGS_STR environment variable not set")
    sys.exit(1)

# Parse the MODEL_CONFIGS string into a list of tuples
model_configs = []
for config in model_configs_str.split():
    if ':' in config:
        parts = config.split(':')
        if len(parts) >= 2:
            model = parts[0]
            mode = parts[1]
            model_configs.append((model, mode))
        else:
            print(f"Warning: Invalid config format: {config}")
    else:
        print(f"Warning: Invalid config format: {config}")

if not model_configs:
    print("Error: No valid model configurations found")
    sys.exit(1)

print(f"Found {len(model_configs)} model configurations: {model_configs}")

# ========================================
# Functions
# ========================================
def concatenate_pdfs(input_files, output_file):
    """
    Concatenate multiple PDF files into a single PDF
    
    Args:
        input_files (list): List of input PDF file paths
        output_file (str): Output PDF file path
    """
    merger = PdfMerger()
    
    try:
        # Add each PDF to the merger
        for pdf_file in input_files:
            if os.path.exists(pdf_file):
                print(f"Adding: {pdf_file}")
                merger.append(pdf_file)
            else:
                print(f"Warning: File not found: {pdf_file}")
        
        # Write the combined PDF
        print(f"Creating combined PDF: {output_file}")
        merger.write(output_file)
        merger.close()
        print("✓ PDF concatenation completed successfully!")
        
    except Exception as e:
        print(f"Error concatenating PDFs: {e}")
        sys.exit(1)

# ========================================
# Build input files dynamically
# ========================================
input_files = []
for model, mode in model_configs:
    # Add diagnostic plots
    diagnostic_path = f"{dropbox}/output/3_embedding/diagnostic_plots/diagnostic_plots_{model}_{mode}_all.pdf"
    if os.path.exists(diagnostic_path):
        input_files.append(diagnostic_path)
        print(f"Found diagnostic plots: {diagnostic_path}")
    else:
        print(f"Warning: Diagnostic plots not found: {diagnostic_path}")
    
    # Add similarity density plots
    similarity_path = f"{dropbox}/output/3_embedding/similarity_density/similarity_density_{model}_{mode}.pdf"
    if os.path.exists(similarity_path):
        input_files.append(similarity_path)
        print(f"Found similarity density: {similarity_path}")
    else:
        print(f"Warning: Similarity density not found: {similarity_path}")

if not input_files:
    print("Error: No PDF files found to concatenate")
    sys.exit(1)

print(f"Found {len(input_files)} PDF files to concatenate")

# ========================================
# Main Script
# ========================================
concatenate_pdfs(input_files, output_pdf)
