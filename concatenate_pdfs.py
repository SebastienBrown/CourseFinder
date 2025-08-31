#!/usr/bin/env python3
"""
Simple PDF concatenation script using PyPDF2
"""

import sys
import os
from PyPDF2 import PdfMerger

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

# Get environment variables
dropbox = os.environ.get("DROPBOX")
mode = os.environ.get("MODE", "off_the_shelf")

if not dropbox:
    print("Error: DROPBOX environment variable not set")
    sys.exit(1)

# Get file paths from environment variables
gpt_diagnostic_pdf = os.environ.get("GPT_DIAGNOSTIC_PDF")
sbert_diagnostic_pdf = os.environ.get("SBERT_DIAGNOSTIC_PDF")
gpt_similarity_pdf = os.environ.get("GPT_SIMILARITY_PDF")
sbert_similarity_pdf = os.environ.get("SBERT_SIMILARITY_PDF")
output_pdf = os.environ.get("COMBINED_PDF")

# Check if all required environment variables are set
required_vars = {
    "GPT_DIAGNOSTIC_PDF": gpt_diagnostic_pdf,
    "SBERT_DIAGNOSTIC_PDF": sbert_diagnostic_pdf,
    "GPT_SIMILARITY_PDF": gpt_similarity_pdf,
    "SBERT_SIMILARITY_PDF": sbert_similarity_pdf,
    "COMBINED_PDF": output_pdf
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Define input files from environment variables
input_files = [
    gpt_diagnostic_pdf,
    sbert_diagnostic_pdf,
    gpt_similarity_pdf,
    sbert_similarity_pdf
]

# Create output directory if it doesn't exist
os.makedirs(os.path.dirname(output_pdf), exist_ok=True)

# Concatenate PDFs
concatenate_pdfs(input_files, output_pdf)
