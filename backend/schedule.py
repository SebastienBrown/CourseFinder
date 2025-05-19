from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

with open('data/amherst_courses_2324S.json') as f:
    amherst_data = json.load(f)

with open('data/precomputed_tsne_coords.json') as f:
    coords_data = json.load(f)

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

    taken_schedule = extract_schedule(taken_course_codes)
    conflicted_courses = []

    for entry in coords_data:
        code = entry["code"]
        if code in taken_course_codes:
            continue  # don't include the user's own courses

        course_times = []
        for course in amherst_data:
            if code in course.get("course_codes", []):
                times_and_locations = course.get("times_and_locations", {})
                for section in times_and_locations.values():
                    for meetings in section.values():
                        for meeting in meetings:
                            parsed = parse_time_range(meeting["time"])
                            if parsed:
                                course_times.append((meeting["day"], *parsed))

        if not course_times:
            continue  # no times to compare

        if has_conflict(course_times, taken_schedule):
            conflicted_courses.append(code)

    print("Taken:", taken_course_codes)
    print("Conflicted:", conflicted_courses[:5])  # sample output


    return jsonify({"conflicted_courses": conflicted_courses})

