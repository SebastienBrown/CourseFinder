import os
from dotenv import load_dotenv

# Load env from parent directory (project root)
# Doing this BEFORE local imports so config.py sees the correct environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '..', '.env')
load_dotenv(env_path, override=True)

# School Configuration
SCHOOL_ID = os.getenv("SCHOOL_ID", "AMHERST").upper()

# Base directory (backend/)

# Data Paths & Supabase Tables Configuration
DATA_CONFIG = {
    "AMHERST": {
        "courses_file": os.path.join(BASE_DIR, "data/amherst_courses_all.json"),
        "embeddings_file": os.path.join(BASE_DIR, "data/gpt_off_the_shelf/output_embeddings_{semester}.json"), # Format string for semester
        "tsne_file": os.path.join(BASE_DIR, "data/precomputed_tsne_coords_all_v3.json"),
        "supabase_table": "user_courses", 
        "supabase_table_extra": "user_courses_test", # Keeping original names
        "supabase_feedback_table": "questions",
         "validation_semester": "2324S", # Default semester for validation
         "semester_columns": ["0910F", "0910S", "1011F", "1011S", "1112F", "1112S", "1213F", "1213S", "1314F", "1314S", "1415F", "1415S", "1516F", "1516S", "1617F", "1617S", "1718F", "1718S", "1819F", "1819S", "1920F", "1920S", "2021F", "2021J", "2021S", "2122F", "2122J", "2122S", "2223F", "2223S", "2324F", "2324S", "2425F", "2425S"]
    },
    "UPENN": {
        "courses_file": os.path.join(BASE_DIR, "data/upenn/courses.json"),
        "embeddings_file": os.path.join(BASE_DIR, "data/upenn/embeddings_{semester}.json"),
        "tsne_file": os.path.join(BASE_DIR, "../course-visualization/public/penn_educ_tsne_coords.json"),
        "supabase_table": "user_courses_upenn",
        "supabase_table_extra": "user_courses_upenn_extra",  # For testing/exploring courses
        "supabase_feedback_table": "questions_upenn",
        "validation_semester": "2024F",
        "semester_columns": ["2024F"]
    }
}

# Get current school config
SCHOOL_CONFIG = DATA_CONFIG.get(SCHOOL_ID, DATA_CONFIG["AMHERST"])

# Default port configuration
DEFAULT_PORT = 5000

# User-specific port configurations (Legacy)
USER_PORTS = {
    'hnaka24': 5000,
    # Add other users and their ports here
}

# Get the current user's username
try:
    username = os.getlogin()
    # Get the port: 
    # 1. Environment variable PORT (Highest priority for parallel backends)
    # 2. User-specific port
    # 3. Default port
    env_port = os.getenv("PORT")
    if env_port:
        PORT = int(env_port)
    else:
        PORT = USER_PORTS.get(username, DEFAULT_PORT) 
except:
    PORT = int(os.getenv("PORT", DEFAULT_PORT))