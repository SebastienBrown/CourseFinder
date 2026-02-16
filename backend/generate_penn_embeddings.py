import json
import os
import openai
import numpy as np
from dotenv import load_dotenv

# Load env variables
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(env_path, override=True)

# Azure OpenAI Configuration (matching schedule.py)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

if not AZURE_OPENAI_API_KEY:
    raise ValueError("Missing AZURE_OPENAI_API_KEY in .env")

# Initialize client
client_embed = openai.AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)

def get_openai_embedding(text):
    """Get embedding from Azure OpenAI using full 1536 dimensions."""
    try:
        response = client_embed.embeddings.create(
            model=AZURE_OPENAI_EMBED_DEPLOYMENT,
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error embedding text: {e}")
        return None

def generate_embeddings(input_path, output_path):
    print(f"Reading courses from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        courses = json.load(f)
        
    print(f"Generating embeddings for {len(courses)} courses...")
    
    courses_with_embeddings = []
    
    for i, course in enumerate(courses):
        # Combine title and description for embedding
        text_to_embed = f"{course['course_title']}: {course['description']}"
        embedding = get_openai_embedding(text_to_embed)
        
        if embedding:
            course["embedding"] = embedding
            courses_with_embeddings.append(course)
        else:
            print(f"Skipping course due to embedding error: {course['course_title']}")
            
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(courses)} courses...")
            
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(courses_with_embeddings, f, indent=2, ensure_ascii=False)
        
    print(f"Saved {len(courses_with_embeddings)} courses with embeddings to {output_path}")

if __name__ == "__main__":
    INPUT_FILE = "backend/data/upenn/courses.json"
    OUTPUT_FILE = "backend/data/upenn/embeddings_2024F.json" # Using 2024F as default for UPenn
    
    generate_embeddings(INPUT_FILE, OUTPUT_FILE)
