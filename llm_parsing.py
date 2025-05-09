import os
import json
import re
from llm_client import llm
from langchain_core.prompts import PromptTemplate

os.chdir("/orcd/home/002/hnaka24/CourseFinder/")
input_folder = "scraped_test"
output_folder = "llm_cleaned"
os.makedirs(output_folder, exist_ok=True)

prompt = PromptTemplate.from_template("""
You are a precise cleaner of college course descriptions.

Only remove any non-academic information, including:
- professor names or titles
- semester offering (e.g., "Fall semester", "Spring semester", "January term")
- course codes (e.g., "(Offered as ...)")
- prerequisites, enrollment limits, or course requirements
- teaching format (e.g., "discussion-based", "lectures", "conducted in person")
- any logistical information (e.g., location, sections, costs)
- information about not open to certain students (e.g., who have taken other courses, first year students, certain majors)


Do not paraphrase, reword, or summarize.
Do not add new information.
Do not change sentence structure or wording.
Return only a **verbatim subset** of the input text with unwanted content removed.

Return a single valid JSON object with no markdown:
{{ 
  "clean_description": "..." 
}}

Course description:
{description}
""")

def clean_description(raw_description):
    formatted_prompt = prompt.format(description=raw_description)
    response = llm.invoke(formatted_prompt)

    try:
        content = response.content if hasattr(response, "content") else response
        parsed = json.loads(content)
        cleaned = parsed.get("clean_description", raw_description)

        # 🐛 Debug output
        print("\n🟡 Original Description:\n" + raw_description.strip())
        print("\n✅ Cleaned Description:\n" + cleaned.strip())
        print("—" * 80)

        return cleaned

    except Exception as e:
        print("❌ JSON parse failed:", e)
        return raw_description


errors = []
for filename in os.listdir(input_folder):
    if not (filename.startswith("amherst") and filename.endswith(".json")):
        continue

    with open(os.path.join(input_folder, filename), "rb") as f:
        raw = f.read()

    text = raw.decode("utf-8", errors="ignore")  # Skip invalid characters
    courses = json.loads(text)

    # with open(os.path.join(input_folder, filename)) as f:
    #     courses = json.load(f)

    for course in courses:
        if "description" in course:
            try: 
                course["description"] = clean_description(course["description"])
            except:
                errors.append((course.get('semester'), course.get('course_title')))

    with open(os.path.join(output_folder, filename), "w") as f:
        json.dump(courses, f, indent=2)

print("Descriptions cleaned and saved to 'llm_cleaned/'")

print("\n\nCourses that caused errors:")
for err in errors:
    print(err)