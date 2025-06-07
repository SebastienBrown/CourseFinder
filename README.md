# Creating the virtual environment:

- `python -m venv course_venv` or `python3.10 -m venv course_venv`
- `source course_venv/bin/activate`
- `pip install requirements.txt`

# Workflow:

**Data Collection and Cleaning**

1. Scraping:
   `sbatch ./course_scraper.sbatch`

2. To complete the scraping,
- `sbatch ./failed_links.sbatch`
- Manually check the log of failed_links and add courses
- Find course AMST 224 in amherst_courses_2526F.json and manually add course codes EDST/PSYC/AMST/AAPI 224

3. To clean scraped data:
- `sbatch ./llm_parsing.sbatch` uses LLM to extract a clean subset of the original.
- Manually clean the courses printed under `Courses that caused errors`.
- Run `python ./clean_json.py` to remove duplicates, special characters, and fill in missing course codes.

4. Append the cleaned files together
- Run `python ./append_metadata.py` to output `./course-visualization/public/amherst_courses_all.json`.

**Network Graph**
1. Create embeddings for each course
- `sbatch embedding./.sbatch`
- Output: `./embeddings/output_embeddings_{semester}.json`

2. Compute pairwise similarity scores
- Run `python ./similarity.py` to process semesters individually
- Run `sbatch ./similarity.sbatch`  or `python ./similarity_all.py` to process all semester courses pairwise
- Output: `./similarity/output_similarity_{semester}.json`, where semester = 'all' for the latter

3. Apply t-SNE to compute coordinates for each course
- `cd ./course-visualization/src/data/`
- `sbatch ./generate_precomputed_tsne.sbatch` or `python ./generate_precomputed_tsne.py`
- Output: `./course-visualization/public/precomputed_tsne_coords_{semester}.json`

**Run backend**
- `cd backend`
- `python3 -m venv venv` optional but recommended
- `source venv/bin/activate` or `venv\Scripts\activate` on Windows
- `pip install -r requirements.txt`
- `export FLASK_APP=schedule.py` or `set FLASK_APP=schedule.py` on Windows
- `flask run`

If the search bar returns a "fetch" error, try changing the port.
- If you are a new user, add your username and preferred port number to `course-visualization/src/config.js`

**Run frontend**
- `cd course-visualization/src`
- `npm install`
- `npm install tsne-js`
- `npm run start`

`npm install react-router-dom` may fix some issues if the error is related to react-router-dom.

**Descriptive Analysis**
- `cd analysis/code`
- Make a semester-department panel with `sbatch descriptives.sbatch`