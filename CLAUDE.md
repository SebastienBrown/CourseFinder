# CourseFinder — Web Application

## Summary
Interactive web application ("The Visual Open Curriculum") that lets Amherst College students explore courses on a similarity-based 2D map. Students sign in via Supabase auth, input their past courses, see them highlighted on a t-SNE visualization of all courses, get similarity-based recommendations, check schedule conflicts, and ask questions. The app is deployed on Vercel with two instances: one for Amherst (main branch) and one for UPenn (features/upenn-integration branch).

## Deployments
- **Amherst:** https://visual-open-curriculum.vercel.app/ (branch: `main`)
- **UPenn:** https://course-finder-upenn.vercel.app/ (branch: `feature/upenn-integration`)
- Both deployments use the same codebase but different source data

## Architecture

### Frontend (React)
- **Location:** `course-visualization/`
- **Framework:** React 19 with React Router v7, Tailwind CSS, D3.js for graph visualization
- **Key components:**
  - `App.js` — routing, auth state, layout
  - `CourseSimilarityPrecomputedGraph.jsx` — main t-SNE visualization (63KB, the core of the app)
  - `CourseInput.jsx` — course search/input with backend validation
  - `CoursePopup.jsx` — course detail popup on click
  - `SemesterCourseIntake.jsx` — per-semester course selection during onboarding
  - `IntakePrompt.jsx` — prompts users to add past courses
  - `SurpriseButton.jsx` — random course recommendation
  - `Auth.js` — Supabase authentication (email/password)
  - `UserInfoPopup.jsx` — collects user demographic info (major, class year)
  - `TermsModal.jsx` — terms of service
  - `SubmissionPage.jsx` — question submission form

### Backend (Flask/Python)
- **Location:** `backend/`
- **Key file:** `schedule.py` (41KB) — the Flask API server with all endpoints
- **Features:**
  - Course search with Azure OpenAI embeddings
  - Schedule conflict detection
  - Transcript scraping (`transcript_scrape.py`)
  - Query validation (`query_validation.py`)
  - User info management via Supabase
  - JWT authentication with Supabase tokens
- **External services:**
  - Azure OpenAI (two resources: one for chat/GPT-4o-mini, one for embeddings/text-embedding-3-small)
  - Supabase (auth, database for user courses/info/questions)

### Data Files
- `course-visualization/public/amherst_courses_all.json` — full course catalog (23MB)
- `course-visualization/public/precomputed_tsne_coords_all_5707402.json` — precomputed t-SNE coordinates used by frontend (active)
- `course-visualization/public/tsne_coords_all_sbert_off_the_shelf_5790245.json` — experimental SBERT off-the-shelf coordinates (kept for reference)
- `backend/data/` — embedding data organized by model config, plus similarity data

### Configuration
- `course-visualization/src/config.js` — semester list, current semester (2324S), data file paths, port settings
- `backend/config.py` — port configuration per user
- `.env` files needed in root, `course-visualization/`, and `backend/` with Supabase + Azure OpenAI keys

## Branches
- `main` — Amherst deployment (production)
- `feature/upenn-integration` — UPenn deployment (uses different source data)
- `backup-main` — backup of main
- `map_trials` — experimental map versions
- `ocr-test-docker` — OCR testing for transcript scraping

## What Has Been Tried
- Multiple t-SNE coordinate versions (v1-v4, job 5707402, job 5790245)
- The frontend currently loads `precomputed_tsne_coords_all_5707402.json`; the SBERT off-the-shelf version (5790245) was experimental
- OCR-based transcript scraping (separate branch)
- Various auth flows (current: Supabase email/password)

## To-Do
[No specific tasks assigned for today]

## Useful Skills
- Frontend development: `npm run start` from `course-visualization/`
- Backend: `flask run` from `backend/` (set `FLASK_APP=schedule.py`)
- The `.env` symlink in `course-visualization/` points to root `.env`
- Vercel deployment is automatic on push to respective branches
- Port configuration: default 5000, configurable per user in both `config.js` and `config.py`

## Notes
- The backend and course-visualization directories also exist in the research repo on HPC — they were originally part of one repo and later split out for deployment.
- The `server.js` file is an Express server for serving the built React app (used in production/Vercel, not for local dev).
- Schedule conflict detection is a backend feature that checks course time overlaps.
- The "Ask a Question" feature stores questions in Supabase for researchers to review.
