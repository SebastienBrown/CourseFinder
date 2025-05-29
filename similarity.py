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
        courses (list): A list of course dictionaries, each with an embedding and 'semester' key.

    Returns:
        list: A list of dictionaries where each entry includes the main course's details (including semester) and a list of other courses it was compared against (including their semesters).
    """
    # Create a mapping from course code (and potentially semester for uniqueness if needed) to its index in the embeddings list
    # For this specific output format request, we'll map based on the primary course code for consistency with the output structure.
    # However, the embeddings and similarity matrix are based on the unique course objects in the 'courses' list which retain semester.
    code_to_idx = {course['course_codes'][0]: i for i, course in enumerate(courses) if course.get('course_codes') and len(course['course_codes']) > 0}
    valid_courses = [course for course in courses if course.get('course_codes') and len(course['course_codes']) > 0 and course['course_codes'][0] in code_to_idx]

    # Re-index embeddings based on valid_courses
    embeddings = [course['embedding'] for course in valid_courses]
    course_codes = [course['course_codes'] for course in valid_courses]
    semesters = [course['semester'] for course in valid_courses]

    # Create a similarity matrix using embeddings of valid courses
    similarity_matrix = cosine_similarity(embeddings)

    # Prepare the result format
    result = []
    for idx, course in enumerate(valid_courses):
        # Main course details
        main_course_codes = course['course_codes']
        main_course_semester = course['semester']
        comparisons = []

        # Compare with every other course in the valid_courses list
        for jdx, other_course in enumerate(valid_courses):
            if idx != jdx:  # Skip comparing a course with itself
                other_course_codes = other_course['course_codes']
                other_course_semester = other_course['semester']
                similarity_score = similarity_matrix[idx][jdx]
                # Normalize to range [0, 1]
                similarity_score = (similarity_score + 1) / 2  # Ensure similarity is between 0 and 1
                comparisons.append({
                    "course_codes": other_course_codes,
                    "semester": other_course_semester, # Include semester of compared course
                    "similarity_score": similarity_score
                })

        result.append({
            "course_codes": main_course_codes,
            "semester": main_course_semester, # Include semester of main course
            "compared_courses": comparisons
        })

    return result

def process_and_compute_similarities(input_file, output_file, semester):
    """
    Process courses from input file, compute cosine similarities, and save results to output file.
    Includes semester information in the output.

    Args:
        input_file (str): Path to input file containing courses with embeddings.
        output_file (str): Path to output file where results will be saved.
        semester (str): The semester associated with the data.
    """
    try:
        print(f"Processing {input_file} for semester {semester}...")
        # Read the input file
        with open(input_file, 'r') as file:
            courses = json.load(file)
            print("Courses loaded successfully.")

        # Add semester information to each course dictionary
        for course in courses:
            course['semester'] = semester

        # Filter out courses without embeddings
        courses_with_embeddings = [course for course in courses if 'embedding' in course]
        if len(courses_with_embeddings) < len(courses):
            print(f"Warning: {len(courses) - len(courses_with_embeddings)} courses were skipped due to missing embeddings")

        if not courses_with_embeddings:
            print(f"Error: No courses with embeddings found in {input_file}")
            return

        # Compute the similarity matrix
        result = compute_similarity_matrix(courses_with_embeddings)
        print("done")

        # Save the result to the output file
        with open(output_file, 'w') as file:
            json.dump(result, file, indent=4)
            print(f"Similarity results saved to {output_file}")

    except Exception as e:
        print(f"Error processing courses: {e}")

# Input and output file paths
semesters = ['2223F', '2223S', '2324F', '2324S']

for semester in semesters:
    input_file = f'embeddings/output_embeddings_{semester}.json'  # Replace with your actual input file
    output_file = f'similarity/output_similarity_{semester}.json'  # Output file

    # Process courses and compute similarities
    process_and_compute_similarities(input_file, output_file, semester)
