import re
import os
import json

folder_path = "/orcd/home/002/hnaka24/CourseFinder/scraped/"
output_path = "/orcd/home/002/hnaka24/CourseFinder/cleaned/"

i = 0
j = 0
keywords = [
    'Requisite', 'Requisites', 'Limited to', 'How to handle overenrollment:', 
    'A student may not receive credit', 'Admission with consent', 'Not open to', 
    'Required of', 'Professor', 'Professors', 'Visiting Professor', 'Lecturer', 
    'Senior Lecturer', 'Fall semester', 'Spring semester', 'Fall and spring semesters', "Students who have taken", "Advanced enrollment", "Offered in", "Two group meetings", "In 2020-21", "This course will be conducted primarily in person", "Placement into"
]
    
for filename in os.listdir(folder_path):
    if filename.endswith(".json") and filename.startswith("amherst_courses"):

      # Assuming your data is loaded as a list of dicts, like:
      with open(f"{folder_path}{filename}", 'r') as f:
            courses = json.load(f)

      # Now split description
      for course in courses:
            desc = course.get('description', '')

            # Normalize spaces
            desc = re.sub(r'\s+', ' ', desc)
            
            # Step 0: Try to find requirement info
            match = re.search(r'\b(Requisite|Requisites|Prerequisite|No prerequisites|No prior|Limited to|How to handle overenrollment:|A student may not receive credit|Admission with consent|Not open to|Required of|Enrollment|Advanced enrollment|Offered in|In 2020-21|January-term|This course will be conducted primarily in person|Placement into|Students who have taken|A half course.|The course will be taught|A full course.|Pending Faculty Approval|The course will be taught|The class will meet synchronously|Fulfills either|The requirements are|In addition to the expected use of Zoom|This intensive course will meet|January term|STUDENTS WHO HAVE TAKEN)\b', desc)

            # # Step 1: Try to find class hours
            if not match:
                  match = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b.*?\b(hours|class hours|hours of class|group meetings|class|three-hour)\b', desc, flags=re.IGNORECASE)


            # # Step 2: If not found, try "Professor" or "Professors"
            if not match:
                  match = re.search(
                        r'\s*('  # Allow spaces before the keyword
                        r'Professor|Professors|Visiting Professor|Lecturer|Senior Lecturer|Visiting Assistant Professor|'
                        r'Fall\s*semester|Spring\s*semester|Fall\s*and\s*spring\s*semesters|'
                        r'Fall\s*semester\.|Spring\s*semester\.|Fall\s*and\s*spring\s*semesters\.'
                        r')\s*',  # Allow spaces after the keyword
                        desc
                  )

            # Split
            if match:
                  i += 1
                  split_point = match.start()
                  course['requirements'] = desc[split_point:].strip()
                  course['description'] = desc[:split_point].strip()
            else:
                  # Loop through each keyword and split
                  blank = True
                  for keyword in keywords:
                        parts = desc.split(keyword)
                        if len(parts) > 1:  # If the keyword exists in the description
                              print(f"Found '{keyword}' in the description!")
                              course['requirements'] = parts[1]
                              course['description'] = parts[0]
                              i += 1
                              blank = False
                              break
            
                  # If none of these keywords in description, leave as is and requirements empty
                  if blank == True:
                        course['requirements'] = ''
                        if desc != "": j += 1

      # Now `courses` is updated; you can save it back if needed:
      with open(f'{output_path}{filename}', 'w') as f:
            json.dump(courses, f, indent=4)

print(f"Number of matches: {i} \nNumber of non-matches: {j}")

# Loop through output path to find courses with requirement field blank
for filename in os.listdir(output_path):
    if filename.endswith(".json") and filename.startswith("amherst_courses"):

      # Assuming your data is loaded as a list of dicts, like:
      with open(f"{output_path}{filename}", 'r') as f:
            courses = json.load(f)

      # Now split description
      for course in courses:
            requirement = course.get('requirements', '')
            desc = course.get('description', '')
            if requirement == "" and desc != "":
                 print(filename)
                 print(f"{course['description']}\n\n")