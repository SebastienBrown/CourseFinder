from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
from flask_cors import CORS


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


@app.route("/api/conflicted_courses", methods=["POST"])
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
    print("Conflicted:", conflicted_courses[:5])  # sample output

    return jsonify({"conflicted_courses": conflicted_courses})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
