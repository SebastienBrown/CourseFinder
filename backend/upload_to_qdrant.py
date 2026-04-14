import os
import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

load_dotenv()

# Load environment configuration (same mechanism as backend)
# You may want to run this with QDRANT_URL and QDRANT_API_KEY
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

print(f"Connecting to Qdrant at {QDRANT_URL}")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

COLLECTION_NAME = "amherst_courses"

# 1. Recreate Collection
print("Recreating Collection (this will delete old data)...")
client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=models.VectorParams(
        size=1536, 
        distance=models.Distance.COSINE
    )
)
print("Collection created.")

# List of semesters mapped in the app
SEMESTER_COLUMNS = [
    "0910F", "0910S", "1011F", "1011S", "1112F", "1112S",
    "1213F", "1213S", "1314F", "1314S", "1415F", "1415S",
    "1516F", "1516S", "1617F", "1617S", "1718F", "1718S",
    "1819F", "1819S", "1920F", "1920S", "2021F", "2021J",
    "2021S", "2122F", "2122J", "2122S", "2223F", "2223S",
    "2324F", "2324S", "2425F", "2425S", "2526F", "2526S"
]

UPLOAD_BATCH_SIZE = 100

for sem in SEMESTER_COLUMNS:
    file_path = f"data/gpt_off_the_shelf/output_embeddings_{sem}.json"
    if not os.path.exists(file_path):
        continue
    
    print(f"Processing semester {sem}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        file_data = json.load(f)
        
    points = []
    
    for course in file_data:
        if "embedding" not in course or course["embedding"] is None:
            continue
            
        # Extract fields to store as payload
        embedding_vector = course.pop("embedding")
        
        # Explicitly tag the semester in the payload if it isn't already
        course["semester"] = sem
            
        # Give a consistent deterministic UUID based on title and semester
        course_uid_string = f"{course.get('course_title', '')}_{sem}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, course_uid_string))
        
        points.append(
            models.PointStruct(
                id=point_id,
                vector=embedding_vector,
                payload=course
            )
        )
        
        # Batch insert to not overwhelm Qdrant
        if len(points) >= UPLOAD_BATCH_SIZE:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            points = []
            
    # Insert any remaining points for this semester
    if len(points) > 0:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        points = []
        
    print(f"Finished {sem}.")

# Create a payload index on the 'semester' field to drastically speed up single-semester searches
print("Creating payload index for semester filtering...")
client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="semester",
    field_schema=models.PayloadSchemaType.KEYWORD,
)

print("✅ Completely finished uploading all data to Qdrant!")
