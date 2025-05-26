# CourseFinder

To run this webapp, from root directory:

# Run backend

cd backend
python3 -m venv venv # optional but recommended
source venv/bin/activate # or venv\Scripts\activate on Windows
pip install -r requirements.txt
export FLASK_APP=schedule.py # or set FLASK_APP=schedule.py on Windows
flask run

# Run frontend

cd course-visualization/src
npm install
npm install tsne-js
npm run start

# Creating the virtual environment:

- `python3.10 -m venv course_venv`
- `source course_venv/bin/activate`
- `pip install requirements.txt`

# Workflow:

**Data Collection and Cleaning**

1. Scraping:
   `sbatch ./CourseFinder/course_scraper.sbatch`

2. To complete the scraping,

- `sbatch ./CourseFinder/failed_links.sbatch`
- Manually check the log of failed_links and add courses
- Find course AMST 224 in amherst_courses_2526F.json and manually add course codes EDST/PSYC/AMST/AAPI 224

3. To clean scraped data:

- `sbatch ./CourseFinder/llm_parsing.sbatch`
- Manually clean the courses printed under `Courses that caused errors`

**Network Graph**
1. Create embeddings for each course
- Output: `./output_courses_with_embeddings.json`

2. Compute pairwise similarity scores
- Output: `./course-visualization/src/data/output_courses_similarity.json`

3. Apply t-SNE to generate coordinates for each course
- `cd ./course-visualization/src/data/`
- `python ./generate_precomputed_tsne.py`
- Output: `./course-visualization/src/data/precomputed_tsne_coords.json`

3. 
