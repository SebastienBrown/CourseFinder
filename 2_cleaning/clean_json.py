import json
import re
import os
from pathlib import Path

def clean_html_tags(text):
    """Remove <i> and </i> tags from text."""
    if isinstance(text, str):
        return text.replace('<i>', '').replace('</i>', '')
    return text

def clean_course_data(course):
    """Clean HTML tags from all string fields in a course."""
    for key, value in course.items():
        if isinstance(value, str):
            course[key] = clean_html_tags(value)
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, str):
                    value[subkey] = clean_html_tags(subvalue)
                elif isinstance(subvalue, list):
                    for i, item in enumerate(subvalue):
                        if isinstance(item, str):
                            subvalue[i] = clean_html_tags(item)
                        elif isinstance(item, dict):
                            for subsubkey, subsubvalue in item.items():
                                if isinstance(subsubvalue, str):
                                    item[subsubkey] = clean_html_tags(subsubvalue)
    return course

def make_hashable(obj):
    """Convert an object to a hashable type."""
    if isinstance(obj, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
    elif isinstance(obj, list):
        return tuple(make_hashable(x) for x in obj)
    else:
        return obj

def remove_duplicates(courses):
    """Remove duplicate course entries."""
    # Convert each course to a tuple of its items for hashing
    seen = set()
    unique_courses = []
    duplicates_removed = 0
    
    for course in courses:
        # Convert course dict to a hashable tuple
        course_tuple = make_hashable(course)
        if course_tuple not in seen:
            seen.add(course_tuple)
            unique_courses.append(course)
        else:
            duplicates_removed += 1
            # Find the original course that matches this duplicate
            original_course = next(c for c in unique_courses if make_hashable(c) == course_tuple)
            print("\nFound duplicate entries:")
            print("Original entry:")
            print(json.dumps(original_course, indent=2))
            print("Duplicate entry:")
            print(json.dumps(course, indent=2))
            print("-" * 80)
    
    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate entries")
    
    return unique_courses

def extract_course_code(text):
    """Extract course code from text using regex."""
    # Look for space-separated format (e.g., "FYSE 104")
    matches = re.findall(r'\b([A-Z]{2,})\s+(\d+[A-Z]?)\b', text)
    if matches:
        # Convert to dash format (e.g., "FYSE-104")
        return f"{matches[0][0]}-{matches[0][1]}"
    # Fallback to original pattern for dash format
    matches = re.findall(r'\b([A-Z]{2,}-\d+[A-Z]?)\b', text)
    return matches[0] if matches else None

def process_json_file(file_path):
    """Process a single JSON file and update course codes."""
    print(f"Processing {file_path}...")
    
    # Read the JSON file
    with open(file_path, 'r') as f:
        courses = json.load(f)
    
    original_count = len(courses)
    modified = False
    
    # Clean HTML tags and update course codes
    for course in courses:
        # Clean HTML tags from course data
        course = clean_course_data(course)
        modified = True  # Always mark as modified since we're cleaning HTML tags
        
        # Check if course_codes is empty
        if not course.get('course_codes'):
            # Get the first key from times_and_locations
            if course.get('times_and_locations'):
                first_key = next(iter(course['times_and_locations']))
                # Extract course code from the key
                course_code = extract_course_code(first_key)
                if course_code:
                    course['course_codes'] = [course_code]
                    print(f"Updated course code for: {course.get('course_title', 'Unknown')} -> {course_code}")
    
    # Remove duplicates
    courses = remove_duplicates(courses)
    if len(courses) < original_count:
        modified = True
    
    # Save the file if modifications were made
    if modified:
        with open(file_path, 'w') as f:
            json.dump(courses, f, indent=2)
        print(f"Saved updates to {file_path}")
        print(f"Original count: {original_count}, Final count: {len(courses)}")
    else:
        print(f"No updates needed for {file_path}")

def main():
    # Get all JSON files in llm_cleaned directory
    llm_cleaned_dir = Path('llm_cleaned')
    json_files = list(llm_cleaned_dir.glob('amherst_courses_*.json'))
    
    print(f"Found {len(json_files)} JSON files to process")
    
    # Process each file
    for file_path in json_files:
        process_json_file(file_path)

if __name__ == "__main__":
    main() 