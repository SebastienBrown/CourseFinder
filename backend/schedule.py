from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
from flask_cors import CORS
import requests
from dotenv import load_dotenv
from config import PORT
from transcript_scrape import extract_courses_from_transcript
import openai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
from functools import wraps
import time
from datetime import datetime
from query_validation import QueryValidator
import jwt


# Load env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create global validator instance
validator = QueryValidator()

#supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SUPABASE_TABLE_URL = f"{SUPABASE_URL}/rest/v1/user_courses"  # Example table path

# Azure OpenAI Configuration from .env
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = "2023-05-15"


client = openai.AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION
)


app = Flask(__name__)

# Load allowed origins from environment variables
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

# Configure CORS with specific origins
CORS(app, origins=ALLOWED_ORIGINS, 
     methods=['GET', 'POST'],
     allow_headers=['Content-Type', 'Authorization'])

#CORS(app)

# Get Supabase JWT Secret (NOT JWKS!)
# Find this in: Settings → Configuration → Data API
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET environment variable is required")

print("Using Supabase JWT Secret for HS256 verification")

def jwt_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]
        #print("Token received:", token[:20] + "...")  # Only print first 20 chars for security

        try:

            # First, decode without verification to see the audience claim
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            audience = unverified_payload.get("aud")
            #print(f"Token audience: {audience}")

            # Decode JWT using HS256 algorithm with Supabase JWT secret
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],  # Supabase uses HS256, not RS256!
                audience=audience,  # Use the audience from the token
                options={
                    "verify_exp": True,  # Verify expiration
                    "verify_iat": True,  # Verify issued at
                    "verify_signature": True
                }
            )
            
            #print("JWT payload verified successfully")
            #print(f"User ID: {payload.get('sub')}")
            #print(f"Email: {payload.get('email')}")
            
            # Add user info to kwargs
            kwargs["payload"] = payload
            kwargs["user_id"] = payload.get("sub")
            kwargs["user_email"] = payload.get("email")
            
        except jwt.ExpiredSignatureError:
            print("JWT verification error: Token has expired")
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidSignatureError:
            print("JWT verification error: Invalid signature")
            return jsonify({"error": "Invalid token signature"}), 401
        except jwt.DecodeError:
            print("JWT verification error: Token decode failed")
            return jsonify({"error": "Invalid token format"}), 401
        except Exception as e:
            #print(f"JWT verification error: {str(e)}")
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

        return f(*args, **kwargs)
    return wrapper

def get_openai_embedding(text):
    """Get embedding from Azure OpenAI using full 1536 dimensions."""
    response = client.embeddings.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        input=text,
        encoding_format="float" 
    )

    #print(f'Azure open ai deployment name: {AZURE_OPENAI_DEPLOYMENT}')


    embedding = np.array(response.data[0].embedding, dtype=np.float32)  # Ensure FAISS-compatible float32 format

    #take out this statement later
    assert embedding.shape[0] == 1536, f"Unexpected embedding dimension: {embedding.shape[0]}"

    return embedding.reshape(1, -1)  


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

with open('./data/precomputed_tsne_coords_all_v3.json') as f:
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
    
def extract_schedule(course_codes, current_semester):
    # Extract scheduled time slots for taken courses in the current semester only
    taken_schedule = []
    for course in amherst_data:
        # Only process courses from the current semester
        if course.get("semester") != current_semester:
            continue
            
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
    taken_courses_in_semester = set()
    for course in semester_courses:
        for code in course.get("course_codes", []):
            if code in taken_course_codes:
                taken_courses_in_semester.add(code)

    taken_courses_in_semester = list(taken_courses_in_semester)  # Convert back to list if needed

    if not taken_courses_in_semester:
        return jsonify({"conflicted_courses": []})

    taken_schedule = extract_schedule(taken_courses_in_semester, current_semester)
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
            #print("Course",course,"has a conflict with these times ",course_times)
            conflicted_courses.extend(codes)  # Add all codes for this course
            #print("Course",codes,"conflicts with ",course_times)

    #print("Taken schedule is ",taken_schedule)
    #print("Current Semester:", current_semester)
    #print("Taken courses in semester:", taken_courses_in_semester)
    #print("Conflicted:", conflicted_courses)  # sample output

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



@app.route("/semantic_course_search", methods=["POST"])
def semantic_search():
    data=request.json
    print("Incoming semantic input data: ",data)

    query=data.get("query")
    print(query)

    # Check if query is safe to use
    is_valid, error = validator.validate(query)
    
    if not is_valid:
        # Don't process bad input
        print("invalid query")
        return jsonify({"error": error}), 400

    query_embedding=get_openai_embedding(query)
    print(query_embedding)

    # Input and output paths
    file1_path = "data/gpt_off_the_shelf/output_embeddings_2526F.json"
    file2_path = "data/gpt_off_the_shelf/output_embeddings_2526S.json"
    output_path = "combined.json"

    # Load both JSON lists
    with open(file1_path, 'r', encoding='utf-8') as f1:
        list1 = json.load(f1)

    with open(file2_path, 'r', encoding='utf-8') as f2:
        list2 = json.load(f2)

    # Ensure both are lists
    if not isinstance(list1, list) or not isinstance(list2, list):
        raise ValueError("Both JSON files must contain lists.")

    # Concatenate lists
    combined_list = list1 + list2

    seen_titles = set()
    deduped = []
    for course in combined_list:
        title = course.get("course_title", "").strip().lower()
        if title and title not in seen_titles:
            deduped.append(course)
            seen_titles.add(title)

    combined_list = deduped

        # Extract all course names
    course_names = [course["course_title"] for course in combined_list]

    # Count frequencies
    name_counts = Counter(course_names)

    # Print frequencies
    for name, count in name_counts.items():
        print(f"{name}: {count}")

    # Step 2: Prepare course embeddings matrix
    course_embeddings = np.array([course["embedding"] for course in combined_list])
    print(course_embeddings)

    # Step 3: Compute cosine similarity
    similarities = cosine_similarity(query_embedding, course_embeddings)[0]  # [0] to flatten

    # Step 4: Assign similarity scores and rank courses
    for course, sim in zip(combined_list, similarities):
        course["similarity"] = sim

    ranked_courses = sorted(combined_list, key=lambda x: x["similarity"], reverse=True)

    # Print only the course codes
    #print("RANKED COURSE CODES:")
    #for course in ranked_courses:
        #print(course["course_codes"])

    # Step 5: Print top 5
    for course in ranked_courses[:5]:
        print(f"{course['course_codes']} - {course['course_title']} (similarity: {course['similarity']:.4f})")

    return ranked_courses[:5]


@app.route("/submit_courses", methods=["POST"])
@jwt_required
def submit_courses(payload=None, user_id=None, user_email=None):
    data = request.json
    #print("Incoming request data:", data)

    user_id = payload["sub"]  # trusted Supabase user ID
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

    # Note — POST to table endpoint, no ?id filter
    response = requests.post(SUPABASE_TABLE_URL, json=[row_data], headers=headers)

    print("Supabase response:", response.status_code, response.text)

    if response.status_code in [200, 201, 204]:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"error": "Failed to write to Supabase", "details": response.text}), 500
    

@app.route("/retrieve_courses", methods=["POST"])
@jwt_required
def retrieve_courses(payload=None, user_id=None, user_email=None):
    data = request.json
    print("Incoming request data:", data)

    user_id = payload["sub"]  # trusted Supabase user ID
    print("USER ID IS: ",user_id)
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


@app.route("/transcript_parsing", methods=["POST"])
def transcript_parsing():
    if "transcript" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    pdf_file = request.files["transcript"]
    
    if pdf_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        # Pass the file-like object directly
        result = extract_courses_from_transcript(pdf_file)
        print(result)
        return jsonify(result), 200
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500
    
@app.route('/health')
def health_check():
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "service": "course-finder-backend"
    })
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", PORT)))
