from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
from flask_cors import CORS
import requests
from dotenv import load_dotenv
from config import PORT

# Load env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print(SUPABASE_KEY)
print(SUPABASE_URL)

SUPABASE_TABLE_URL = f"{SUPABASE_URL}/rest/v1/user_courses"  # Example table path


app = Flask(__name__)
CORS(app)

with open('./data/amherst_courses_all.json') as f:
    try:
        amherst_data = json.load(f)
        if not isinstance(amherst_data, list):
            raise ValueError("amherst_data must be a list")
        print(f"Successfully loaded amherst_data with {len(amherst_data)} entries")
    except json.JSONDecodeError as e:
        print(f"Error loading amherst_courses_all.json: {e}")
        amherst_data = []
    except Exception as e:
        print(f"Unexpected error loading amherst_courses_all.json: {e}")
        amherst_data = []

with open('./data/precomputed_tsne_coords_all.json') as f:
    try:
        coords_data = json.load(f)
        if not isinstance(coords_data, list):
            raise ValueError("coords_data must be a list")
        print(f"Successfully loaded coords_data with {len(coords_data)} entries")
        # Validate first few entries
        for i, entry in enumerate(coords_data[:5]):
            if not isinstance(entry, dict):
                print(f"Warning: Entry {i} is not a dictionary: {entry}")
            if "codes" not in entry:
                print(f"Warning: Entry {i} missing 'codes' field: {entry}")
    except json.JSONDecodeError as e:
        print(f"Error loading precomputed_tsne_coords_all.json: {e}")
        coords_data = []
    except Exception as e:
        print(f"Unexpected error loading precomputed_tsne_coords_all.json: {e}")
        coords_data = []

# Sample input: list of course names the student is already taking
#taken_course_codes = ["ARHA-324","ARHA-357","HIST-428"]

# --- Helper functions ---

# Helper to convert time string to (start, end) datetime.time objects
def parse_time_range(time_str):
    try:
        start_str, end_str = time_str.split(" - ")
        fmt = "%I:%M %p"
        return (datetime.strptime(start_str, fmt).time(), datetime.strptime(end_str, fmt).time())
    except Exception:
        return None
    
def extract_schedule(course_codes):
    # Extract scheduled time slots for taken courses
    taken_schedule = []
    for course in amherst_data:
        for code in course.get("course_codes", []):
            if code in course_codes:
                times_and_locations = course.get("times_and_locations", {})
                for section in times_and_locations.values():
                    for meetings in section.values():
                        for meeting in meetings:
                            parsed = parse_time_range(meeting["time"])
                            if parsed:
                                taken_schedule.append((meeting["day"], *parsed))
    return taken_schedule

# Helper to check for time overlap
def has_conflict(course_times, taken_schedule):
    for day, start, end in course_times:
        for t_day, t_start, t_end in taken_schedule:
            if day == t_day and not (end <= t_start or start >= t_end):
                return True
    return False


@app.route("/")
def home():
    return "Flask backend is running!"


@app.route("/conflicted_courses", methods=["POST"])
def conflicted_courses():
    data = request.get_json()
    taken_course_codes = data.get("taken_courses", [])
    current_semester = data.get("semester")  # Get the current semester from the frontend
    
    if not current_semester:
        return jsonify({"error": "No semester specified"}), 400

    # Filter amherst_data to only include courses from the current semester
    semester_courses = [course for course in amherst_data if course.get("semester") == current_semester]
    print(f"Found {len(semester_courses)} courses in semester {current_semester}")

    # Find the taken courses in the current semester
    taken_courses_in_semester = []
    for course in semester_courses:
        if any(code in course.get("course_codes", []) for code in taken_course_codes):
            taken_courses_in_semester.extend(course.get("course_codes", []))

    if not taken_courses_in_semester:
        return jsonify({"conflicted_courses": []})

    taken_schedule = extract_schedule(taken_courses_in_semester)
    conflicted_courses = []

    for entry in coords_data:
        # Only check courses from the current semester
        if entry.get("semester") != current_semester:
            continue

        codes = entry.get("codes", [])
        if any(code in taken_courses_in_semester for code in codes):
            continue  # don't include the user's own courses

        course_times = []
        for course in semester_courses:  # Use filtered semester_courses
            if any(code in course.get("course_codes", []) for code in codes):
                times_and_locations = course.get("times_and_locations", {})
                # Skip if times_and_locations is not a dictionary
                if not isinstance(times_and_locations, dict):
                    print(f"Warning: times_and_locations is not a dict for course {course.get('course_codes')} in semester {course.get('semester')}: {times_and_locations}")
                    continue
                    
                try:
                    for course_section in times_and_locations.values():
                        if not isinstance(course_section, dict):
                            print(f"Warning: course_section is not a dict: {course_section}")
                            continue
                            
                        for section_meetings in course_section.values():
                            if not isinstance(section_meetings, list):
                                print(f"Warning: section_meetings is not a list: {section_meetings}")
                                continue
                                
                            for meeting in section_meetings:
                                if isinstance(meeting, dict) and "time" in meeting:
                                    parsed = parse_time_range(meeting["time"])
                                    if parsed:
                                        course_times.append((meeting.get("day", ""), *parsed))
                except AttributeError as e:
                    print(f"Error processing times_and_locations for course {course.get('course_codes')}: {e}")
                    continue

        if not course_times:
            continue  # no times to compare

        if has_conflict(course_times, taken_schedule):
            conflicted_courses.extend(codes)  # Add all codes for this course

    print("Current Semester:", current_semester)
    print("Taken courses in semester:", taken_courses_in_semester)
    print("Conflicted:", conflicted_courses)  # sample output

    return jsonify({"conflicted_courses": conflicted_courses})


# List of allowed semester columns
SEMESTER_COLUMNS = [
    "0910F",
    "0910S",
    "1011F",
    "1011S",
    "1112F",
    "1112S",
    "1213F",
    "1213S",
    "1314F",
    "1314S",
    "1415F",
    "1415S",
    "1516F",
    "1516S",
    "1617F",
    "1617S",
    "1718F",
    "1718S",
    "1819F",
    "1819S",
    "1920F",
    "1920S",
    "2021F",
    "2021J",
    "2021S",
    "2122F",
    "2122J",
    "2122S",
    "2223F",
    "2223S",
    "2324F",
    "2324S",
    "2425F",
    "2425S"
]

@app.route("/submit_courses", methods=["POST"])
def submit_courses():
    data = request.json
    print("Incoming request data:", data)

    user_id = data.get("user_id")
    semester_courses = data.get("semester_courses")

    if not user_id or not semester_courses:
        return jsonify({"error": "Missing user_id or semester_courses"}), 400

    # Prepare row for Supabase
    row_data = {"id": user_id}

    for semester in SEMESTER_COLUMNS:
        if semester in semester_courses:
            courses_list = semester_courses[semester]
            if courses_list:  # Only include if non-empty list
                row_data[semester] = courses_list

    print("Prepared row data:", row_data)

    # Send upsert to Supabase REST API
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # enables upsert
    }

    response = requests.post(SUPABASE_TABLE_URL, json=[row_data], headers=headers)

    print("Supabase response:", response.status_code, response.text)

    if response.status_code in [200, 201, 204]:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"error": "Failed to write to Supabase", "details": response.text}), 500
    

@app.route("/retrieve_courses", methods=["POST"])
def retrieve_courses():
    data = request.json
    print("Incoming request data:", data)

    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Build GET URL with filter to retrieve row by user id
    get_url = f"{SUPABASE_TABLE_URL}?id=eq.{user_id}"
    
    try:
        response = requests.get(get_url, headers=headers)
        print("Supabase response:", response.status_code, response.text)

        if response.status_code == 200:
            data = response.json()
            if data:
                # Create a list of courses with their semester information
                courses_with_semesters = []
                for semester in SEMESTER_COLUMNS:
                    if semester in data[0] and data[0][semester] is not None:
                        for course in data[0][semester]:
                            courses_with_semesters.append({
                                "course_code": course,
                                "semester": semester
                            })
                return jsonify(courses_with_semesters)
            else:
                return jsonify([])  # No data found
        else:
            return jsonify({"error": "Failed to retrieve from Supabase", "details": response.text}), 500
            
    except Exception as e:
        print("Error retrieving courses:", str(e))
        return jsonify({"error": str(e)}), 500
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", PORT)))
