# CourseFinder

# Creating the virtual environment:
- `python3.10 -m venv course_venv`
- `source course_venv/bin/activate`
- `pip install requirements.txt`

# Workflow:

**Data Collection and Cleaning**
1. Scraping:
```sbatch ./CourseFinder/course_scraper.sbatch```

2. To complete the scraping, 
- ```sbatch ./CourseFinder/failed_links.sbatch```
- Manually check the log of failed_links and add courses
- Find course AMST 224 in amherst_courses_2526F.json and manually add course codes EDST/PSYC/AMST/AAPI 224

3. To clean scraped data:
- ```sbatch ./CourseFinder/llm_parsing.sbatch```
- Manually clean the courses printed under `Courses that caused errors`

**Network Graph**