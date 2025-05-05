import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def compute_cosine_similarity(embedding1, embedding2):
    """
    Compute the cosine similarity between two embeddings.
    
    Args:
        embedding1 (list): The first embedding vector.
        embedding2 (list): The second embedding vector.
    
    Returns:
        float: The cosine similarity score between 0 and 1.
    """
    # Convert embeddings to numpy arrays
    embedding1 = np.array(embedding1).reshape(1, -1)
    embedding2 = np.array(embedding2).reshape(1, -1)
    
    # Compute cosine similarity
    similarity = cosine_similarity(embedding1, embedding2)[0][0]
    
    # Ensure similarity is between 0 and 1 (cosine similarity can be negative in some cases)
    return (similarity + 1) / 2  # Normalize to [0, 1]

def compute_similarity_matrix(courses):
    """
    Compute a similarity matrix for the courses based on their embeddings.
    
    Args:
        courses (list): A list of course dictionaries, each with an embedding.
    
    Returns:
        dict: A dictionary where each course has a list of other courses it was compared against, with similarity scores.
    """
    course_codes = [course['course_codes'] for course in courses]
    embeddings = [course['embedding'] for course in courses]
    
    # Create a similarity matrix
    similarity_matrix = cosine_similarity(embeddings)
    
    # Prepare the result format
    result = []
    for idx, course in enumerate(courses):
        course_code = course['course_codes']
        comparisons = []
        
        # Compare with every other course
        for jdx, other_course in enumerate(courses):
            if idx != jdx:  # Skip comparing a course with itself
                other_course_code = other_course['course_codes']
                similarity_score = similarity_matrix[idx][jdx]
                # Normalize to range [0, 1]
                similarity_score = (similarity_score + 1) / 2  # Ensure similarity is between 0 and 1
                comparisons.append({
                    "course_codes": other_course_code,
                    "similarity_score": similarity_score
                })
        
        result.append({
            "course_codes": course_code,
            "compared_courses": comparisons
        })
    
    return result

def process_and_compute_similarities(input_file, output_file):
    """
    Process courses from input file, compute cosine similarities, and save results to output file.
    
    Args:
        input_file (str): Path to input file containing courses with embeddings.
        output_file (str): Path to output file where results will be saved.
    """
    try:
        # Read the input file
        with open(input_file, 'r') as file:
            courses = json.load(file)
            print("Courses loaded successfully.")
        
        # Compute the similarity matrix
        result = compute_similarity_matrix(courses)
        print("done")
        
        # Save the result to the output file
        with open(output_file, 'w') as file:
            json.dump(result, file, indent=4)
            print(f"Similarity results saved to {output_file}")
    
    except Exception as e:
        print(f"Error processing courses: {e}")

# Input and output file paths
input_file = 'output_courses_with_embeddings.json'  # Replace with your actual input file
output_file = 'output_courses_similarity.json'  # Output file

# Process courses and compute similarities
process_and_compute_similarities(input_file, output_file)
