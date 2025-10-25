# Creating the virtual environment:

- `python -m venv course_venv` or `python3.10 -m venv course_venv`
- `source course_venv/bin/activate`
- `pip install -r requirements.txt`

# Workflow:

**Data Collection and Cleaning**

1. Scraping:
   `sbatch 1_scraping/course_scraper.sbatch`

2. To complete the scraping,
- `sbatch 1_scraping/failed_links.sbatch`
- Manually check the log of failed_links and add courses
- Find course AMST 224 in amherst_courses_2526F.json and manually add course codes EDST/PSYC/AMST/AAPI 224

3. To clean scraped data:
- `sbatch 2_cleaning/llm_parsing.sbatch` uses LLM to extract a clean subset of the original.
- Manually clean the courses printed under `Courses that caused errors`.
- Run `python 2_cleaning/clean_json.py` to remove duplicates, special characters, and fill in missing course codes.

4. Append the cleaned files together
- Run `python 2_cleaning/append_metadata.py`
- Output: `course-visualization/public/amherst_courses_all.json`.

**Embeddings, Similarity Scores, Mapping, Similar Courses**
`sbatch MASTER.sh` runs the entire pipeline from top to bottom. The `MASTER.sh` file declares all of the global variables, including file paths, LLM to be used, configuration for fine-tuning, etc. If you wish to run only certain sections, simply comment out the other sections. A brief outline of the pipeline is provided below.

0. Contrastive learning
- `3_embedding/0_contrastive_learning.py` 
- Input: manually annotated sets of four courses () and `amherst_courses_all.json`.
- Output: fine-tuned model in `3_embedding/sbert_contrastive_model/`.

1. Create embeddings for each course
- `3_embedding/1_embeddings.py` computes the embeddings.
- Output: `output_embeddings_{semester}.json` in the data folder (`data/2_intermediate/2_embeddings/{model}/`) and `backend/data/{model}/`.

2. Create diagnostic plots of 4-course sets
- `3_embedding/2_diagnostic_plots.py`
- Output:

3. Compute pairwise similarity scores
- `4_similarity/1_similarity_all.py` computes the pairwise similarity scores.
- Output: `output_similarity_{semester}.json`, where semester = 'all' when running for all semesters

4. Create density plots of similarity scores
- `4_similarity/2_similarity_density.py` plots the density of similarity scores by i) within and across departments, and ii) positive and negative pairs from the manual annotated list.
- Input: `output_similarity_{semester}.json`
- Output: 

5. Apply t-SNE to compute coordinates for each course
- `5_webapp/1_tsne_coords.py` computes the coordinates for the App map.
- Output: `course-visualization/public/precomputed_tsne_coords_{semester}.json`

6. Add three most similar courses in the same semester
- `5_webapp/2_append_similar_courses.py` appends for each course the three most similar course in the same semester.
- Output: `course-visualization/public/precomputed_tsne_coords_{semester}.json` (appends to same file as 3)

**Run Backend**
- `cd backend`
- `python -m venv venv` optional but recommended
- `source venv/bin/activate` or `venv\Scripts\activate` on Windows
- `pip install -r requirements.txt`
- `export FLASK_APP=schedule.py` or `set FLASK_APP=schedule.py` on Windows
- `flask run`

If the search bar returns a "fetch" error, try changing the port.
- If you are a new user, add your username and preferred port number to `course-visualization/src/config.js` AND `backend/config.py`

**Run Frontend**
- `cd course-visualization`
- `ln -s ../.env .env` to make the frontend refer to the .env file in the root directory
- `cd course-visualization/src`
- The first time:
   ```
   npm install
   npm install tsne-js
   npm install html2canvas
   npm install lucide-react
   ```
- `npm run start`

`npm install react-router-dom` may fix some issues if the error is related to react-router-dom (should be installed automatically with `npm install`)

**Deploying the Website**
- Both `requirements.txt` and `backend/requirements.txt` are necessary.
- Two `.env` files are necessary: in `course-visualization` and in `backend`. Both should have the following elements:
   ```
   SUPABASE_URL=
   SUPABASE_KEY=
   SUPABASE_JWT_SECRET=
   REACT_APP_SUPABASE_URL=
   REACT_APP_SUPABASE_KEY=
   REACT_APP_BACKEND_URL="http://127.0.0.1:5000" # this should be your backend port
   ```
   all should have the elements in straight double quotes "", without spaces and no curly quotes.
   If it loads the wrong backend url, try quitting both your browser and terminal, fix the above issues and try again.

**Analysis**
- `cd 6_analysis`
- Run major (department)-level analysis with `sbatch major_master.sbatch`
- Run student-level analysis with `sbatch student_master.sbatch`