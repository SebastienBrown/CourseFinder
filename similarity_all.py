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

        # Filter out courses without embeddings
        courses_with_embeddings = [course for course in courses if 'embedding' in course]
        if len(courses_with_embeddings) < len(courses):
            print(f"Warning: {len(courses) - len(courses_with_embeddings)} courses were skipped due to missing embeddings")

        if not courses_with_embeddings:
            print(f"Error: No courses with embeddings found in {input_file}")
            return

        # Compute the similarity matrix
        result = compute_similarity_matrix(courses_with_embeddings) # Note: this function will be modified below to handle the combined list
        print("done")

        # Save the result to the output file
        with open(output_file, 'w') as file:
            json.dump(result, file, indent=4)
            print(f"Similarity results saved to {output_file}")

    except Exception as e:
        print(f"Error processing courses: {e}")

# --- Main execution block for similarity_all.py ---
# Input file paths for all semesters
semesters = ['0910F', '0910S', '1011F', '1011S', '1112F', '1112S', '1213F', '1213S', '1314F', '1314S', '1415F', '1415S', '1516F', '1516S', '1617F', '1617S', '1718F', '1718S', '1819F', '1819S', '1920F', '1920S', '2021F', '2021J', '2021S', '2122F', '2122J', '2122S', '2223F', '2223S', '2324F', '2324S', '2425F', '2425S', '2526F', '2526S']
all_courses = []

print("Loading data from all semesters...")
for semester in semesters:
    input_file = f'embeddings/output_embeddings_{semester}.json'
    try:
        with open(input_file, 'r') as f:
            courses = json.load(f)
            # Add semester information to each course
            for course in courses:
                course['semester'] = semester # Add the semester here
            all_courses.extend(courses)
        print(f"Loaded {len(courses)} courses from {input_file}")
    except FileNotFoundError:
        print(f"Warning: {input_file} not found. Skipping.")
    except Exception as e:
        print(f"Error loading {input_file}: {e}")

if not all_courses:
    print("Error: No course data loaded from any semester.")
else:
    print(f"Successfully loaded a total of {len(all_courses)} courses from all semesters.")

    # Filter out courses without embeddings from the combined list
    courses_with_embeddings = [course for course in all_courses if 'embedding' in course]
    if len(courses_with_embeddings) < len(all_courses):
        print(f"Warning: {len(all_courses) - len(courses_with_embeddings)} courses were skipped due to missing embeddings")

    if not courses_with_embeddings:
        print("Error: No courses with embeddings found in the combined data.")
    else:
        # Compute the similarity matrix for all courses
        print("Computing similarity matrix for all courses...")
        result = compute_similarity_matrix(courses_with_embeddings) # Pass the combined list
        print("done")

        # Output file path for the combined similarity data
        output_file = 'similarity/output_similarity_all.json'

        # Save the result to the output file
        try:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=4)
            print(f"Combined similarity results saved to {output_file}")
        except Exception as e:
            print(f"Error saving {output_file}: {e}")
