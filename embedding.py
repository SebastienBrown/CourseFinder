import requests
import json
import os
from dotenv import load_dotenv

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
semesters = ['2223F', '2223S', '2324F', '2324S']

for semester in semesters:
    input_file = f"llm_cleaned/amherst_courses_{semester}.json"  # Replace with your actual input file
    output_file = f'embeddings/output_embeddings_{semester}.json'  # Output file
    deployment_name = "text-embedding-3-small"  # Replace with your actual deployment name

    # Process courses and generate embeddings
    process_courses(input_file, output_file, deployment_name)
