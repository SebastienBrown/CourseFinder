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
SUPABASE_TABLE_URL_EXTRA=f"{SUPABASE_URL}/rest/v1/user_courses_test"

# --- Azure OpenAI: use TWO clients (different resources) ---

# Chat resource (matches AZURE_CHATOPENAI_* in your .env)
AZURE_CHATOPENAI_API_KEY = os.getenv("AZURE_CHATOPENAI_API_KEY")
AZURE_CHATOPENAI_ENDPOINT = os.getenv("AZURE_CHATOPENAI_ENDPOINT")
AZURE_CHATOPENAI_DEPLOYMENT = os.getenv("AZURE_CHATOPENAI_DEPLOYMENT")  # e.g., gpt-4o-mini
CHATOPENAI_API_VERSION = os.getenv("CHATOPENAI_API_VERSION", "2025-01-01-preview")

# Embeddings resource (matches AZURE_OPENAI_* in your .env)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")    # e.g., text-embedding-3-small
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

# Create two distinct clients
client_chat = openai.AzureOpenAI(
    api_key=AZURE_CHATOPENAI_API_KEY,
    azure_endpoint=AZURE_CHATOPENAI_ENDPOINT,
    api_version=CHATOPENAI_API_VERSION,
)

client_embed = openai.AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)

app = Flask(__name__)

# Load allowed origins from environment variables
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000' ).split(',')

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
    response = client_embed.embeddings.create(
        model=AZURE_OPENAI_EMBED_DEPLOYMENT,
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
def catalog_semesters_in_data():
    """Return SEMESTER_COLUMNS that actually appear in amherst_data, in chronological order."""
    present = {c.get("semester") for c in amherst_data if c.get("semester")}
    return [s for s in SEMESTER_COLUMNS if s in present]

def latest_semesters_in_catalog(k=1):
    ordered = catalog_semesters_in_data()
    return ordered[-k:] if ordered else []


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
    print(semester_courses)

    if not user_id or not semester_courses:
        return jsonify({"error": "Missing user_id or semester_courses"}), 400

    # Prepare row for Supabase
    row_data = {"id": user_id}

    for semester in SEMESTER_COLUMNS:
        if semester in semester_courses:
            courses_list = semester_courses[semester]
            #if courses_list:  # Only include if non-empty list
            row_data[semester] = courses_list

    #print("Prepared row data:", row_data)

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

# --- Accept Terms endpoint ---
@app.route("/accept-terms", methods=["POST"])
@jwt_required
def accept_terms(payload=None, user_id=None, user_email=None):
    """Insert or update termsAccepted=True for the authenticated user"""
    try:

        # Extract user_id from JWT payload (trusted)
        user_id = payload["sub"]

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"  # This makes it an upsert
        }

        upsert_url =  SUPABASE_TABLE_URL
        upsert_payload = {
            "id": user_id,
            "terms_accepted": True
        }

        response = requests.post(upsert_url, headers=headers, json=[upsert_payload])
        print(response)

        if response.status_code not in [200, 201]:
            print("Supabase error:", response.text)
            return jsonify({"error": "Failed to upsert user"}), 500

        return jsonify({"message": "Terms accepted successfully"}), 200

    except Exception as e:
        print("Error in accept_terms:", e)
        return jsonify({"error": str(e)}), 500
    

# --- Check Terms endpoint ---
@app.route("/check-terms", methods=["GET"])
@jwt_required
def check_terms(payload=None, user_id=None, user_email=None):
    """Insert or update termsAccepted=True for the authenticated user"""
    try:

        # Extract user_id from JWT payload (trusted)
        user_id = payload["sub"]

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"  # This makes it an upsert
        }

        # Add query parameter to filter by user_id
        url = f"{SUPABASE_TABLE_URL}?id=eq.{user_id}"
        payload = {
            "id": user_id
        }

        response = requests.get(url, headers=headers)
        print(response)

        if response.status_code not in [200, 201]:
            print("Supabase error:", response.text)
            return jsonify({"error": "Failed to upsert user"}), 500

        data = response.json()
        accepted = False
        if data and len(data) > 0:
            accepted = data[0].get("terms_accepted") or False  # <-- this line changed
        return jsonify({"accepted": accepted})

    except Exception as e:
        print("Error in accept_terms:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/add_course", methods=["POST"])
@jwt_required
def add_course(payload=None, user_id=None, user_email=None):
    data = request.json

    user_id = payload["sub"]  # trusted Supabase user ID
    new_course = data.get("course_to_add")
    course_semester=data.get("semester")
    print(new_course)
    print(course_semester)

    if not user_id or not new_course:
        return jsonify({"error": "Missing user_id or semester_courses"}), 400

    # First, fetch the existing row (if any)
    fetch_url = f"{SUPABASE_TABLE_URL}?id=eq.{user_id}"

    # Send upsert to Supabase REST API
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    fetch_response = requests.get(fetch_url, headers=headers)
    if fetch_response.status_code != 200:
        return jsonify({"error": "Failed to fetch user row", "details": fetch_response.text}), 500

    existing_rows = fetch_response.json()
    print("existing rows are ",existing_rows)

    if not existing_rows:
        # Row does not exist, create a blank one with just the ID
        row_data = {"id": user_id, course_semester: [new_course]}
        insert_response = requests.post(
            SUPABASE_TABLE_URL,
            json=[row_data],
            headers={**headers, "Prefer": "resolution=merge-duplicates"}
        )
        if insert_response.status_code not in [200, 201, 204]:
            return jsonify({"error": "Failed to create new row", "details": insert_response.text}), 500
    else:
        # Row exists → append the course to the matching semester column
        existing_row = existing_rows[0]
        current_courses = existing_row.get(course_semester, []) or []
        if new_course not in current_courses:
            current_courses.append(new_course)
        print("current courses are now ",current_courses)

        update_data = {course_semester: current_courses}
        update_url = f"{SUPABASE_TABLE_URL}?id=eq.{user_id}"
        update_response = requests.patch(update_url, json=update_data, headers=headers)
        print("succesful response")

        if update_response.status_code not in [200, 201, 204]:
            return jsonify({"error": "Failed to update existing row", "details": update_response.text}), 500

    return jsonify({"status": "success"}), 200


@app.route("/remove_course", methods=["POST"])
@jwt_required
def remove_course(payload=None, user_id=None, user_email=None):
    data = request.json

    user_id = payload["sub"]  # trusted Supabase user ID
    new_course = data.get("course_to_add")
    course_semester=data.get("semester")
    print(new_course)
    print(course_semester)

    if not user_id or not new_course:
        return jsonify({"error": "Missing user_id or semester_courses"}), 400

    # First, fetch the existing row (if any)
    fetch_url = f"{SUPABASE_TABLE_URL}?id=eq.{user_id}"

    # Send upsert to Supabase REST API
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    fetch_response = requests.get(fetch_url, headers=headers)
    if fetch_response.status_code != 200:
        return jsonify({"error": "Failed to fetch user row", "details": fetch_response.text}), 500

    existing_rows = fetch_response.json()

    # Row exists → append the course to the matching semester column
    existing_row = existing_rows[0]
    current_courses = existing_row.get(course_semester, []) or []
    if new_course in current_courses:
        current_courses.remove(new_course)

    update_data = {course_semester: current_courses}
    update_url = f"{SUPABASE_TABLE_URL}?id=eq.{user_id}"
    update_response = requests.patch(update_url, json=update_data, headers=headers)

    if update_response.status_code not in [200, 201, 204]:
        return jsonify({"error": "Failed to update existing row", "details": update_response.text}), 500

    return jsonify({"status": "success"}), 200
    
    
@app.route("/surprise_recommendation", methods=["POST"])
@jwt_required
def surprise_recommendation(payload=None, user_id=None, user_email=None):
    """Recommend ONE course from the latest semester only, with a surprising but meaningful connection to the user's history."""
    try:
        user_id = payload["sub"]

        body = request.get_json(silent=True) or {}
        client_exclude = body.get("exclude_codes", [])
        exclude_codes = {str(c).strip().upper() for c in client_exclude if isinstance(c, str)}


        # --- fetch user's course history from Supabase ---
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        get_url = f"{SUPABASE_TABLE_URL}?id=eq.{user_id}"
        resp = requests.get(get_url, headers=headers)
        if resp.status_code != 200:
            return jsonify({"error": "Could not retrieve course history"}), 500

        user_data = resp.json()
        if not user_data:
            return jsonify({"error": "No course history found. Please add your courses first."}), 400

        # --- build user's history across ALL semesters (past + current) ---
        user_courses: list[str] = []
        user_departments: set[str] = set()
        for semester in SEMESTER_COLUMNS:
            if semester in user_data[0] and user_data[0][semester]:
                for code in user_data[0][semester]:
                    user_courses.append(code)
                    if "-" in code:
                        user_departments.add(code.split("-")[0])

        if not user_courses:
            return jsonify({"error": "No courses found in your history"}), 400

        # --- find the latest semester that actually exists in amherst_data ---
        present_terms = {c.get("semester") for c in amherst_data if c.get("semester")}
        latest_semester = next((s for s in reversed(SEMESTER_COLUMNS) if s in present_terms), None)
        if not latest_semester:
            return jsonify({"error": "No semesters available in catalog"}), 500

        # --- candidates: ONLY courses from latest_semester, not taken, from new departments ---
        # --- candidates: ONLY courses from latest_semester, not taken, from new departments, NOT SEEN THIS SESSION ---
        candidate_courses = []
        for course in amherst_data:
            if course.get("semester") != latest_semester:
                continue
            course_codes = course.get("course_codes", []) or []
            if not course_codes:
                continue

            # Normalize codes once
            norm_codes = [str(code).strip().upper() for code in course_codes]

            # Skip if course was already recommended in this browser session
            if any(c in exclude_codes for c in norm_codes):
                continue

            # departments for this course
            course_departments = {code.split("-")[0] for code in course_codes if "-" in code}

            # skip user's usual departments; skip courses they've taken
            if course_departments & user_departments:
                continue
            if any(code in user_courses for code in course_codes):
                continue

            candidate_courses.append(course)

        if not candidate_courses:
            return jsonify({"error": f"No unseen surprising courses found in {latest_semester}."}), 400

            # --- build helpers to create text for similarity ---
        def course_text(c: dict) -> str:
            title = (c.get("course_title") or "").strip()
            desc = (c.get("description") or "").strip()
            return f"{title}. {desc}".strip()

        code_to_course = {}
        for c in amherst_data:
            for code in c.get("course_codes", []) or []:
                code_to_course[code] = c

        # user profile text from their history (titles+descriptions)
        user_profile_texts = []
        for code in user_courses:
            c = code_to_course.get(code)
            if c:
                t = course_text(c)
                if t:
                    user_profile_texts.append(t)
        user_profile = " ".join(user_profile_texts).strip() or " ".join(user_courses)

        # --- rank latest-semester candidates by TF-IDF similarity to user profile ---
        from sklearn.feature_extraction.text import TfidfVectorizer  # local import to keep global deps minimal

        cand_texts = [course_text(c) for c in candidate_courses]
        pairs = [(c, t) for c, t in zip(candidate_courses, cand_texts) if t]

        if pairs:
            docs = [user_profile] + [t for _, t in pairs]
            vect = TfidfVectorizer(stop_words="english", max_features=8000)
            X = vect.fit_transform(docs)
            sims = cosine_similarity(X[0:1], X[1:]).ravel()

            ranked = [c for (c, _s) in sorted(zip([c for c, _ in pairs], sims),
                                              key=lambda x: x[1], reverse=True)]

            # tiny diversity: sample from the top pool deterministically per user
            import random
            rng = random.Random(user_id)
            pool = ranked[:200] if len(ranked) > 200 else ranked
            rng.shuffle(pool)
            shortlist = pool[:50] if len(pool) > 50 else pool
        else:
            # fallback: if we had no text, at least avoid A/B bias with a deterministic shuffle
            import random
            rng = random.Random(user_id)
            shortlist = candidate_courses[:]
            rng.shuffle(shortlist)
            shortlist = shortlist[:50]

        if not shortlist:
            return jsonify({"error": f"No candidate courses available in {latest_semester}."}), 400

        # --- build LLM prompt using ONLY latest-semester shortlist ---
        user_courses_str = ", ".join(user_courses[:40])
        prompt = f"""
You are a course recommendation system. A student has taken these courses: {user_courses_str}

From the course offerings in {latest_semester}, choose ONE course from departments they haven't typically explored that
has a surprising but meaningful connection to their past coursework (skills, methods, themes, or perspectives).
Explain the connection briefly and concretely.

Candidate courses (select ONE):
""".strip()

        for i, course in enumerate(shortlist, start=1):
            codes = "/".join(course.get("course_codes", []))
            title = course.get("course_title", "") or ""
            description = (course.get("description", "") or "")[:300]
            prompt += f"\n{i}. {codes} - {title}: {description}"

        prompt += """
        
Respond with ONLY this JSON:
{
  "recommended_course_index": <1-based index>,
  "surprise_connection": "<2-3 sentences referencing specific themes or skills>"
}
""".rstrip()

        # --- call chat model ---
        response = client_chat.chat.completions.create(
            model=AZURE_CHATOPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful academic advisor who finds surprising interdisciplinary connections between courses."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        llm_response = response.choices[0].message.content.strip()

        # --- parse LLM JSON; safe fallback ---
        try:
            import json
            llm_json = json.loads(llm_response)
            recommended_index = int(llm_json["recommended_course_index"]) - 1
            surprise_connection = llm_json["surprise_connection"]
            if recommended_index < 0 or recommended_index >= len(shortlist):
                raise ValueError("Index out of range")
        except Exception as e:
            print(f"Error parsing LLM response: {e}\nLLM Response: {llm_response!r}")
            import random
            rng = random.Random(user_id)
            recommended_index = rng.randrange(len(shortlist))
            surprise_connection = (
                "This course lies outside your usual departments but connects to your prior work in a surprising way."
            )

        recommended_course = shortlist[recommended_index]

        recommendation = {
            "course_codes": recommended_course.get("course_codes", []),
            "course_title": recommended_course.get("course_title", ""),
            "description": recommended_course.get("description", ""),
            "department": recommended_course.get("department", ""),
            "semester": latest_semester,
            "surprise_connection": surprise_connection,
        }
        return jsonify(recommendation), 200

    except Exception as e:
        print(f"Error in surprise_recommendation: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health_check():
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "service": "course-finder-backend"
    })
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", PORT)))
