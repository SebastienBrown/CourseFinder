from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

import json
import time
import os

# Slurm
task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID"))
num_cores = int(os.environ.get("SLURM_CPUS_PER_TASK", 1))
total_jobs = 36

# Save location
output_path = "/orcd/home/002/hnaka24/CourseFinder/"

# Set up Selenium WebDriver
options = Options()
options.add_argument("--headless")  # Run browser in headless mode (no UI)
os.environ["WDM_LOCAL"] = "1"
service1=Service("/home/hnaka24/.cache/selenium/geckodriver/linux64/0.35.0/geckodriver")
driver = webdriver.Firefox(service=service1, options=options)

# Function to extract info
def extract_info(soup):

      # Extract semester
      semester = soup.find("h2", class_="academics-course-list-term").get_text(strip=True)

      # Extract course title
      course_title = soup.find("h3").get_text(strip=True)

      # Extract course codes
      course_code_text = soup.find("p", string=lambda t: t and "Listed in:" in t)
      if not course_code_text:
            course_code_text = soup.find("p").get_text()
      course_codes = []
      if "as " in course_code_text:
            codes_part = course_code_text.split("as ")[1]
            course_codes = [code.strip() for code in codes_part.split(",")]

      # Extract faculty
      faculty_section = soup.find("h4", string="Faculty")
      faculty = []
      if faculty_section:
            for p in faculty_section.find_next_siblings("p"):
                  links = p.find_all("a")
                  faculty += [a.get_text(strip=True) for a in links]
                  break  # Assuming only one relevant <p> under Faculty

      # Extract description
      description_section = soup.find("h4", string="Description")
      description_parts = []
      if description_section:
            for p in description_section.find_next_siblings("p"):
                  span = p.find("span")
                  if span:
                        description_parts.append(span.get_text(strip=True))
                  else:
                        break  # Stop when no more <span> found (e.g., policies, enrollment)
      description = " ".join(description_parts)

      # Extract course times and locations
      time_place_section = soup.find("details", id="acad-course-page-detail-head")
      times = []
      if time_place_section:
            for p in time_place_section.find_all("p"):
                  for line in p.stripped_strings:
                        if any(day in line for day in ["Mo", "Tu", "We", "Th", "Fr"]):
                              times.append(line)

      # Create dictionary and convert to JSON
      course_data = {
            "semester": semester,
            "course_title": course_title,
            "course_codes": course_codes,
            "faculty": faculty,
            "description": description,
            "times_and_locations": times
      }

      return course_data

# Fetch the URL -- changed to jobs approved in the past 3 months
url = "https://www.amherst.edu/academiclife/departments/american_studies/courses/2526S"
driver.get(url)
soup = BeautifulSoup(driver.page_source, 'html.parser')

# Extract list of semesters
options = soup.select("#curriculum-termid option")
term_codes = [opt["value"] for opt in options]
term_codes.reverse()

# Choose the term for this array task
term = term_codes[task_id - 1]
output_file = output_path + f'amherst_courses_{term}.json'

# Extract list of departments
dept_options = soup.select("#curriculum-department option")
departments = [(opt["value"], opt.text.strip()) for opt in dept_options]

# Loop through semesters
jsons = []
print(f"Scraping term: {term}")

# Loop through departments
for dept_url, dept_name in departments:
      print(f"Scraping department: {dept_name} ({dept_url})")

      # Go to that url
      major_url = f"https://www.amherst.edu/{dept_url}/{term}"
      driver.get(major_url)
      soup = BeautifulSoup(driver.page_source, 'html.parser')

      # Extract list of courses
      course_links = soup.select("#academics-course-list .coursehead .course-subj h3 a")

      # Extract hrefs and prepend base URL if needed
      base_url = "https://www.amherst.edu"
      course_urls = [base_url + a["href"] for a in course_links]

      # Loop through courses
      for link in course_urls:
            driver.get(link)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            course_data = extract_info(soup)
            print(course_data)
            jsons += course_data

# Write to JSON
with open(output_file, "w") as f:
      json.dump(jsons, f, indent=4)

driver.quit()
print(f"Data successfully written to {output_file}")