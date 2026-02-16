import json
import os

def transform_gse_data(input_path, output_path, target_semester="2024F"):
    """
    Transforms GSE_Map data (penn_educ_courses.json) to CourseFinder format.
    
    Source Schema (GSE):
    {
        "course_code": "EDUC 1000",
        "course_title": "Foundations...",
        "description": "..."
    }

    Target Schema (CourseFinder):
    {
        "course_title": "Foundations...",
        "course_codes": ["EDUC-1000"],
        "faculty": {},
        "description": "...",
        "times_and_locations": {},
        "semester": "2024F"
    }
    """
    
    print(f"Reading from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        gse_data = json.load(f)
    
    transformed_data = []
    
    for course in gse_data:
        # Normalize code: "EDUC 1000" -> "EDUC-1000"
        raw_code = course.get("course_code", "")
        normalized_code = raw_code.replace(" ", "-")
        
        entry = {
            "course_title": course.get("course_title", ""),
            "course_codes": [normalized_code],
            "faculty": {}, # Missing in source
            "description": course.get("description", ""),
            "times_and_locations": {}, # Missing in source
            "semester": target_semester
        }
        transformed_data.append(entry)
        
    print(f"Transformed {len(transformed_data)} courses.")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, indent=2, ensure_ascii=False)
        
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    # Input: The file we cloned earlier
    INPUT_FILE = "temp_analysis/GSE_Map/penn_educ_courses.json"
    # Output: Where CourseFinder expects data (we'll use a new file for now)
    OUTPUT_FILE = "backend/data/upenn/courses.json"
    
    transform_gse_data(INPUT_FILE, OUTPUT_FILE)
