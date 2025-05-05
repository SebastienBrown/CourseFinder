import json
import re

def process_courses(input_file, output_file):
    with open(input_file, 'r') as file:
        courses = json.load(file)
    
    # List to store courses that did not contain either "limited" or "spring semester"
    courses_without_limited_or_spring = []

    for course in courses:
        description = course.get("description", "")
        additional_data = ""

        # Search for the text "limited" first
        if "limited" in description.lower():
            # Extract the additional data starting from "limited"
            match = re.search(r"limited.*", description, re.IGNORECASE)
            if match:
                additional_data = match.group(0)
                course["description"] = description[:match.start()].strip()
        
        # If "limited" is not found, check for "spring semester"
        if not additional_data and "spring semester" in description.lower():
            match = re.search(r"spring semester.*", description, re.IGNORECASE)
            if match:
                additional_data = match.group(0)
                course["description"] = description[:match.start()].strip()

        # If "limited" and "spring semester" both fail, check for "how to handle"
        if not additional_data and "how to handle" in description.lower():
            match = re.search(r"how to handle.*", description, re.IGNORECASE)
            if match:
                additional_data = match.group(0)
                course["description"] = description[:match.start()].strip()

        # If we found any additional data (limited, spring semester, or how to handle)
        if additional_data:
            course["additional_data"] = additional_data
        else:
            # If no additional data was found, add to the failed list
            courses_without_limited_or_spring.append(course)

    # Write the updated courses to the new JSON file
    with open(output_file, 'w') as outfile:
        json.dump(courses, outfile, indent=4)

    # Print courses without either "limited", "spring semester", or "how to handle"
    if courses_without_limited_or_spring:
        print(f"Courses without 'limited', 'spring semester', or 'how to handle' in description: {len(courses_without_limited_or_spring)}")
        for course in courses_without_limited_or_spring:
            print(course['course_title'])
    else:
        print("All courses had 'limited', 'spring semester', or 'how to handle'.")

# Specify your input and output file paths
input_file = 'scraped/amherst_courses_2324S.json'  # Replace with your input file name if different
output_file = 'processed_courses.json'  # Output file with added "additional_data"

# Run the processing function
process_courses(input_file, output_file)
