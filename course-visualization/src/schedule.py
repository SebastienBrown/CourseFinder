import json
from datetime import datetime

# Load course and coordinate data
with open('data/amherst_courses_2324S.json') as f:
    amherst_data = json.load(f)

with open('data/precomputed_tsne_coords.json') as f:
    coords_data = json.load(f)

# Sample input: list of course names the student is already taking
taken_course_codes = ["ARHA-324","ARHA-357","HIST-428"]

# --- Helper functions ---

# Helper to convert time string to (start, end) datetime.time objects
def parse_time_range(time_str):
    start_str, end_str = time_str.split(" - ")
    fmt = "%I:%M %p"
    return (datetime.strptime(start_str, fmt).time(), datetime.strptime(end_str, fmt).time())

# Extract scheduled time slots for taken courses
taken_schedule = []

for course in amherst_data:
    for code in course["course_codes"]:
        if code in taken_course_codes:
            times_and_locations = course.get("times_and_locations", {})
            for section in times_and_locations.values():
                for meetings in section.values():
                    for meeting in meetings:
                        day = meeting["day"]
                        time_range = parse_time_range(meeting["time"])
                        taken_schedule.append((day, *time_range))

# Helper to check for time overlap
def has_conflict(course_times):
    for day, start, end in course_times:
        for t_day, t_start, t_end in taken_schedule:
            if day == t_day:
                # Check if time intervals overlap
                if not (end <= t_start or start >= t_end):
                    return True
    return False

# Build conflict-free courses from coords_data
eligible_courses = []

for entry in coords_data:
    code = entry["code"]
    if code in taken_course_codes:
        continue

    # Search course times by code in Amherst data
    course_times = []
    for course in amherst_data:
        if code in course["course_codes"]:
            times_and_locations = course.get("times_and_locations", {})
            for section in times_and_locations.values():
                for meetings in section.values():
                    for meeting in meetings:
                        day = meeting["day"]
                        time_range = parse_time_range(meeting["time"])
                        course_times.append((day, *time_range))

    if not course_times:
        continue  # skip if no times listed

    if not has_conflict(course_times):
        eligible_courses.append({
            "code": code,
            "x": entry["x"],
            "y": entry["y"]
        })

# Save result
with open("conflict_free_courses.json", "w") as f:
    json.dump(eligible_courses, f, indent=2)