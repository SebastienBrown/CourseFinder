import requests
import json
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Set up environment variables for Azure OpenAI
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
api_key= os.environ["AZURE_OPENAI_API_KEY"]

if not endpoint or not api_key:
    raise ValueError("Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables")

def azure_openai_generate_embeddings(text, deployment_name):
    """
    Generate embeddings using Azure OpenAI service.
    
    Args:
        text (str): The text to generate embeddings for.
        deployment_name (str): The name of your Azure OpenAI deployment.
        api_version (str): API version to use.
        
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


def process_courses(input_file, output_file, deployment_name):
    try:
        # Debug: Read the file as text and print its contents
        with open(input_file, 'r') as file:
            file_content = file.read()
            print("File content read successfully. Checking content...")
            print(file_content[:200])  # Print the first 200 characters for inspection
            
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

    for course in courses:
        description = course.get("description", "")
        
        if description:
            embedding = azure_openai_generate_embeddings(description, deployment_name)  # Get the embedding for the description
            if embedding:
                course["embedding"] = embedding  # Add the embedding to the course dictionary
            else:
                print(f"Failed to get embedding for course: {course.get('course_title')}")
        else:
            print(f"No description found for course: {course.get('course_title')}")
        
        updated_courses.append(course)  # Add the processed course to the updated list

    # Save the updated courses with embeddings to the output file
    try:
        with open(output_file, 'w') as file:
            json.dump(updated_courses, file, indent=4)
        print(f"Updated courses saved to {output_file}")
    except Exception as e:
        print(f"Error saving updated courses: {e}")


# Input and output file paths
# semesters = ['0910F', '0910S', '1011F', '1011S', '1112F', '1112S', '1213F', '1213S', '1314F', '1314S', '1415F', '1415S', '1516F', '1516S', '1617F', '1617S', '1718F', '1718S', '1819F', '1819S', '1920F', '1920S', '2021F', '2021J', '2021S', '2122F', '2122J', '2122S']
llm_cleaned_dir = Path('llm_cleaned')
json_files = list(llm_cleaned_dir.glob('amherst_courses_*.json'))

for file_path in json_files:
    # Extract semester from filename (e.g., "amherst_courses_2324F.json" -> "2324F")
    semester = file_path.stem.split('_')[-1]
    input_file = str(file_path)
    output_file = f'embeddings/output_embeddings_{semester}.json'  # Output file
    deployment_name = "text-embedding-3-small"  # Replace with your actual deployment name

    # Process courses and generate embeddings
    process_courses(input_file, output_file, deployment_name)
