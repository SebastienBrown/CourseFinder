# Creating the virtual environment:

- `python -m venv course_venv` or `python3.10 -m venv course_venv`
- `source course_venv/bin/activate`
- `pip install -r requirements.txt`

**Run Backend**
- `cd backend`
- `python3 -m venv venv` optional but recommended
- `source venv/bin/activate` or `venv\Scripts\activate` on Windows
- `pip install -r requirements.txt`
- `export FLASK_APP=schedule.py` or `set FLASK_APP=schedule.py` on Windows
- `flask run`

If the search bar returns a "fetch" error, try changing the port.
- If you are a new user, add your username and preferred port number to `course-visualization/src/config.js` AND `backend/config.py`

**Run Frontend**
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
   REACT_APP_SUPABASE_URL=
   REACT_APP_SUPABASE_KEY=
   REACT_APP_BACKEND_URL="http://127.0.0.1:5000" # this should be your backend port
   ```
   all should have the elements in straight double quotes "", without spaces and no curly quotes.
   If it loads the wrong backend url, try quitting both your browser and terminal, fix the above issues and try again.