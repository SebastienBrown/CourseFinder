from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

import json
import re
import os
import time
import tqdm
from collections import OrderedDict
import unicodedata

def normalize_text(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
def normalize_text_recursive(obj):
    if isinstance(obj, str):
        return normalize_text(obj)  # Normalize string values
    elif isinstance(obj, dict):
        return {k: normalize_text_recursive(v) for k, v in obj.items()}  # Recursively apply to dicts
    elif isinstance(obj, list):
        return [normalize_text_recursive(item) for item in obj]  # Recursively apply to lists
    else:
        return obj  # Return non-string values as-is

def normalize_symbol_recursive(obj):
    if isinstance(obj, str):
        # Apply all the replacements for a string
        return (
            obj.replace('\xa0', ' ')
            .replace('&amp;', '&')
            .replace('\n---', '')
            .replace('\n', ' ')
            .replace('\u200b', '')
            .replace('\u2013', '-')
            .replace('\u2014', '--')
            .replace('\u2018', "'")
            .replace('\u2019', "'")
            .replace('\u201c', '"')
            .replace('\u201d', '"')
        )
    elif isinstance(obj, dict):
        # Recursively apply to all values in the dictionary
        return {k: normalize_text_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Recursively apply to all items in the list
        return [normalize_text_recursive(item) for item in obj]
    else:
        return obj  # Return non-string values as-is

#--------------------------------------------------------------------------------
# Function to extract info
def extract_info(soup):

      # Extract semester
      semester = soup.find("h2", class_="academics-course-list-term").get_text(strip=True)

      # Extract course title
      course_title = soup.find("h3").get_text(strip=True)

      # Find the <p> tag that contains 'Listed in:'
      course_code_paragraph = None
      for p in soup.find_all("p"):
            if "Listed in:" in p.get_text():
                  course_code_paragraph = p
                  break

      course_codes = []
      if course_code_paragraph:
            text = course_code_paragraph.get_text(separator=" ", strip=True)
            # This regex captures course codes like AMST-117 and FAMS-130 and CHEM-160L
            course_codes = re.findall(r'\b([A-Z]{2,}-\d+[A-Z]?)\b', text)

      # Locate the "Faculty" section
      faculty_dict = OrderedDict()

      faculty_section = soup.find("h4", string="Faculty")
      if faculty_section:
            for p in faculty_section.find_next_siblings("p"):
                  # Stop parsing once next <h4> is reached
                  if p.find_previous_sibling("h4") and p.find_previous_sibling("h4").text.strip() != "Faculty":
                        break

                  chunks = re.split(r'<br\s*/?>', p.decode_contents())
                  for chunk in chunks:
                        chunk_soup = BeautifulSoup(chunk, "html.parser")
                        text = chunk_soup.get_text(strip=True)

                        # Extract section (optional)
                        section_match = re.search(r"\(Section (\d+)\)", text)
                        section = f"Section {section_match.group(1)}" if section_match else "Section 01"

                        # Extract faculty name(s)
                        names = [a.get_text(strip=True) for a in chunk_soup.find_all("a")]
                        if not names:
                              # Fallback: try extracting from plain text before (Section XX)
                              name_only = re.sub(r"\(Section \d+\)", "", text).strip()
                              if name_only:
                                    names = [name_only]
                              else:
                                    names = ["TBA"]

                        faculty_dict.setdefault(section, []).extend(names)
                  break

      # Guarantee Section 01 exists
      if "Section 01" not in faculty_dict:
            faculty_dict["Section 01"] = ["TBA"]
        
      # Extract description
      description_section = soup.find("h4", string="Description")
      description_parts = []

      if description_section:
            for tag in description_section.find_next_siblings():
                  if tag.name == "h4" or tag.name == "h3":
                        break  # Stop at next section
                  if tag.name == "p":
                        text = tag.get_text(separator=" ", strip=True)
                        if text:
                              description_parts.append(text)

      description = " ".join(description_parts)

      # Extract structured times and locations by section
      times_by_section = {}
      details_section = None
      for details in soup.find_all("details"):
            summary = details.find("summary")
            if summary and "Course times and locations" in summary.get_text():
                  details_section = details
                  break

      if details_section:
            wrapper = details_section.find("div", class_="details-wrapper")
            if wrapper:
                  current_group = None
                  for tag in wrapper.children:
                        if tag.name == "h5":
                              current_group = tag.get_text(strip=True)  # e.g., "BCBP 400 - LEC"
                              times_by_section[current_group] = {}
                        elif tag.name == "p" and current_group:
                              text_lines = tag.get_text(separator="\n", strip=True).split("\n")
                              section_match = re.search(r"Section (\d+)", text_lines[0])
                              if section_match:
                                    section_number = section_match.group(1)
                                    section_key = f"Section {section_number}"
                                    time_lines = text_lines[1:]  # skip header
                              else:
                                    section_key = "General"
                                    time_lines = text_lines  # use all lines

                              times = []
                              for line in time_lines:
                                    m = re.match(r'^([A-Za-z]+)\s+([\d:APM\s\-]+)\s+(.+)$', line)
                                    if m:
                                          times.append({
                                          "day": m.group(1),
                                          "time": m.group(2).strip(),
                                          "location": m.group(3).strip()
                                          })
                              times_by_section[current_group][section_key] = times



      # Create dictionary
      course_data = {
            "semester": semester,
            "course_title": course_title,
            "course_codes": course_codes,
            "faculty": faculty_dict,
            "description": description,
            "times_and_locations": times_by_section
      }

      # Handle special characters
      course_data = normalize_text_recursive(course_data)
      course_data = normalize_symbol_recursive(course_data)

      return course_data

#--------------------------------------------------------------------------------
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

# Fetch the URL -- changed to jobs approved in the past 3 months
url = "https://www.amherst.edu/academiclife/departments/american_studies/courses/2526S"
driver.get(url)
time.sleep(20)
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
loop = tqdm.tqdm(total=len(departments), desc="Departments")

# Loop through semesters
jsons = []
failed_links = []
print(f"Scraping term: {term}")

# Loop through departments
for dept_url, dept_name in departments:
      print(f"Scraping department: {dept_name} ({dept_url})")

      # Go to that url
      major_url = f"https://www.amherst.edu/{dept_url}/{term}"
      driver.get(major_url)
      time.sleep(20)
      soup = BeautifulSoup(driver.page_source, 'html.parser')

      # Extract list of courses
      course_links = soup.select("#academics-course-list .coursehead .course-subj h3 a")

      # Extract hrefs and prepend base URL if needed
      base_url = "https://www.amherst.edu"
      course_urls = [base_url + a["href"] for a in course_links]

      # Loop through courses
      for link in course_urls:
            driver.get(link)
            # time.sleep(20)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            course_list_div = soup.find("div", id="academics-course-list")
            if not course_list_div:
                  failed_links.append(link)
                  continue
            course_data = extract_info(soup)
            print(course_data)
            jsons.append(course_data)
      
      loop.update()

# Write to JSON
with open(output_file, "w") as f:
      json.dump(jsons, f, indent=4)

driver.quit()
print(f"Data successfully written to {output_file}")
print(f"Failed links: {failed_links}")