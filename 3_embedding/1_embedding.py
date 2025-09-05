import requests
import json
import os
from dotenv import load_dotenv
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

load_dotenv()

# ========================================
# Configuration
# ========================================
# Model configuration (set by MASTER.sbatch)
model = os.environ["MODEL"]
mode = os.environ["MODE"]
gpt_model_name = os.environ["GPT_MODEL_NAME"]
sbert_model_name = os.environ["SBERT_MODEL_NAME"]
sbert_model_dir = os.environ["CONTRASTIVE_SAVE_DIR"]

# File paths (set by MASTER.sbatch)
llm_cleaned_dir = Path(os.environ["LLM_CLEANED_DIR"])
embeddings_path = os.environ["EMBEDDINGS_PATH"]

# Prepare JSON file list
json_files = sorted([f for f in llm_cleaned_dir.glob('amherst_courses_*.json') 
                    if len(f.stem.split('_')[-1]) == 5 and 
                    f.stem.split('_')[-1][:4].isdigit() and 
                    f.stem.split('_')[-1][4].isalpha()]) # exclude _all.json

# ========================================
# Prepare Models
# ========================================
# Azure OpenAI Configuration (only used if model = "gpt")
if model == "gpt":
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    
    if not endpoint or not api_key:
        raise ValueError("Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables")

# SBERT setup (only used if model = "sbert")
if model == "sbert":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load tokenizer and model
    if mode != "off_the_shelf":
        print(f"Loading fine-tuned SBERT model from: {sbert_model_dir}")
        tokenizer = AutoTokenizer.from_pretrained(sbert_model_dir)
        base_model = AutoModel.from_pretrained(sbert_model_dir)
    else:
        print(f"Loading off-the-shelf SBERT model: {sbert_model_name}")
        tokenizer = AutoTokenizer.from_pretrained(sbert_model_name)
        base_model = AutoModel.from_pretrained(sbert_model_name)
    
    def mean_pooling(token_embeddings, attention_mask):
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return (token_embeddings * input_mask_expanded).sum(1) / input_mask_expanded.sum(1)
    
    class InferenceModel(torch.nn.Module):
        def __init__(self, encoder):
            super().__init__()
            self.encoder = encoder
    
        def forward(self, **kwargs):
            outputs = self.encoder(**kwargs)
            token_embeddings = outputs.last_hidden_state
            return mean_pooling(token_embeddings, kwargs["attention_mask"])
    
    sbert_model = InferenceModel(base_model).to(device)
    sbert_model.eval()

# ========================================
# Functions to generate embeddings
# ========================================
def gpt_generate_embeddings(text, gpt_model_name):
    """
    Generate embeddings using Azure OpenAI service.
    
    Args:
        text (str): The text to generate embeddings for.
        gpt_model_name (str): The name of your Azure OpenAI deployment.
        
    Returns:
        list: The embedding vector.
    """
    
    # Set up headers
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    # Set up the request payload for embedding generation
    payload = {
        "input": [text],
    }
    
    # Make the API call
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for non-200 status codes
        return response.json()["data"][0]["embedding"]
    except requests.exceptions.RequestException as e:
        print(f"Error making API call: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None

def sbert_generate_embeddings_batch(texts):
    """
    Generate embeddings using SBERT model for a batch of texts.
    
    Args:
        texts (list): List of texts to generate embeddings for.
        
    Returns:
        list: List of embedding vectors.
    """
    batch_size = 64
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        encoded_inputs = tokenizer(batch_texts, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
        
        with torch.no_grad():
            embeddings = sbert_model(**encoded_inputs)
        
        all_embeddings.append(embeddings.cpu())
    
    all_embeddings = torch.cat(all_embeddings, dim=0)
    return all_embeddings.tolist()

def process_courses(input_file, output_file, gpt_model_name):
    try:
        # Debug: Read the file as text and print its contents
        with open(input_file, 'r') as file:
            file_content = file.read()
            print("File content read successfully.")
            
            # Attempt to load the JSON content
            courses = json.loads(file_content)
        
    except json.JSONDecodeError as e:
        print(f"Error loading JSON: {e}")
        print("This might be due to an empty or malformed JSON file.")
        return
    except FileNotFoundError:
        print(f"The file {input_file} was not found.")
        return

    updated_courses = []

    if model == "gpt":
        # Process courses one by one for Azure OpenAI
        for course in courses:
            description = course.get("description", "")
            
            if description:
                embedding = gpt_generate_embeddings(description, gpt_model_name)
                if embedding:
                    course["embedding"] = embedding
                else:
                    print(f"Failed to get embedding for course: {course.get('course_title')}")
            else:
                print(f"No description found for course: {course.get('course_title')}")
            
            updated_courses.append(course)
    
    elif model == "sbert":
        # Process courses in batches for SBERT
        descriptions = []
        valid_indices = []
        
        for i, course in enumerate(courses):
            desc = course.get("description", "")
            if desc:
                descriptions.append(desc)
                valid_indices.append(i)
            else:
                print(f"No description found for course: {course.get('course_title')}")
        
        if descriptions:
            print(f"Generating embeddings for {len(descriptions)} courses using SBERT...")
            embeddings = sbert_generate_embeddings_batch(descriptions)
            
            # Add embeddings back to courses
            for emb_idx, course_idx in enumerate(valid_indices):
                emb_list = embeddings[emb_idx]
                # Optionally round floats for compactness
                emb_list_rounded = [round(x, 8) for x in emb_list]
                courses[course_idx]['embedding'] = emb_list_rounded
        
        updated_courses = courses

    # Save the updated courses with embeddings to the output file
    try:
        with open(output_file, 'w') as file:
            json.dump(updated_courses, file, indent=4)
        print(f"Updated courses saved to {output_file}")
    except Exception as e:
        print(f"Error saving updated courses: {e}")

# ========================================
# Main Script
# ========================================

for file_path in json_files:
    # Extract semester from filename (e.g., "amherst_courses_2324F.json" -> "2324F")
    semester = file_path.stem.split('_')[-1]
    input_file = str(file_path)
    output_file = f'{embeddings_path}output_embeddings_{semester}.json'  # Output file

    # Process courses and generate embeddings
    process_courses(input_file, output_file, gpt_model_name)
