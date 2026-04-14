import sys
import json
from schedule import app

client = app.test_client()

def print_results(title, resp):
    print(f"\n--- {title} ---")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json
        for i, course in enumerate(data):
            print(f"{i+1}. {course.get('course_codes')} - {course.get('course_title')} ({course.get('semester', 'UNKNOWN_SEM')}) [Sim: {course.get('similarity'):.4f}]")
    else:
        print("Error:", resp.text)

# Test 1: Single Semester
resp1 = client.post('/semantic_course_search', json={
    "query": "introduction to philosophy and ethics",
    "allSemesterSearch": False,
    "currentSemester": "2425S"
})
print_results("TEST 1: Single Semester (2425S)", resp1)

# Test 2: Multi Semester
resp2 = client.post('/semantic_course_search', json={
    "query": "introduction to philosophy and ethics",
    "allSemesterSearch": True,
    "currentSemester": "2425S"
})
print_results("TEST 2: All Semesters", resp2)
