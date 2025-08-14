from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

import os
import ast
import time
import tqdm
import re
import json
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
# Collect all failed links
folder_path = "/orcd/home/002/hnaka24/CourseFinder/logs/"

all_urls = []

for filename in os.listdir(folder_path):
    if filename.endswith(".txt") and filename.startswith("course_scraper"):
        with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip().startswith("Failed links:"):
                    try:
                        # Extract the list part after "Failed links:"
                        url_list = ast.literal_eval(line.strip().split("Failed links:")[1].strip())
                        all_urls.extend(url_list)
                    except Exception as e:
                        print(f"Error parsing line in {filename}: {line.strip()}")
                        print(e)

print(f"Collected URLs: {len(all_urls)}")
base = "https://www.amherst.edu/academiclife/departments/courses/1415F/COSC/COSC-161-1415F"
index = all_urls.index(base)
all_urls = all_urls[index:]
print(f"URLs Left: {len(all_urls)}")
print(all_urls)


# Set up Selenium WebDriver
options = Options()
options.add_argument("--headless")  # Run browser in headless mode (no UI)
os.environ["WDM_LOCAL"] = "1"
service1=Service("/home/hnaka24/.cache/selenium/geckodriver/linux64/0.35.0/geckodriver")
driver = webdriver.Firefox(service=service1, options=options)

jsons = []
failed_links = []
loop = tqdm.tqdm(total=len(all_urls), desc="URLs")

# Loop over the urls
for link in all_urls:

      # Extract from url
      parts = link.split("/")
      semester = parts[6]  # "0910F"
      year = semester.replace('F', '').replace('S', '').replace('J', '')
      base_link = "/".join(parts[:8]) + "/" # dept link
      course_full = parts[-1]  # "PHYS-25-0910F"
      course_codes = course_full.rsplit("-", 1)[0]  # "PHYS-25"

      # Attempt to do it normally
      try:
            driver.get(link)
            time.sleep(20)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            course_list_div = soup.find("div", id="academics-course-list")
            # if not course_list_div:
            #       failed_links.append(link)
            #       continue
            if course_list_div:
                 continue
            course_data = extract_info(soup)
            print(course_data)
      
      # If not possible, then get relevant info from dept page
      except:
            driver.get(base_link)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Go to curriculum page for relevant year
            curriculum_link_tag = soup.find("div", id="course-curriculum-links").find("a", string=lambda text: text and "Curriculum" in text)
            href = curriculum_link_tag.get("href").replace('?', f'/{year}F?')
            full_url = f"https://www.amherst.edu{href}"
            driver.get(full_url)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Get title, and faculty for the course in question
            h4_tag = soup.find("h4", id=course_codes)

            if h4_tag:
                  full_text = h4_tag.get_text(strip=True)
                  course_title = " ".join(full_text.split()[1:]) # assuming the first thing before space is the course number

                  # Get the <p> tag right after the <h4>
                  description_tag = h4_tag.find_next_sibling("p")
                  description = description_tag.get_text(strip=True) if description_tag else None

                  # Get the next <p> tag after that
                  faculty_tag = description_tag.find_next_sibling("p") if description_tag else None
                  faculty_text = faculty_tag.get_text(strip=True) if faculty_tag else None
                  print("Faculty Text:", faculty_text)

                  # Match 'Professor(s)' or 'Lecturer(s)' (case-insensitive), and capture what's after
                  match = re.search(r'(Professor[s]?|Lecturer[s]?)\s+(.+?)(?:\.|$)', faculty_text, re.IGNORECASE)

                  if match:
                        names_str = match.group(2).strip()
                        if " and " in names_str:
                              names = [name.strip() for name in names_str.split(" and ")]
                        else:
                              names = [names_str]
                        faculty = {"Section 01": names}
                  else:
                        faculty = {"Section 01": []}

                  # Create dictionary
                  course_data = {
                        "semester": semester,
                        "course_title": course_title,
                        "course_codes": course_codes,
                        "faculty": faculty,
                        "description": description,
                        "times_and_locations": ""
                  }

                  # Handle special characters
                  course_data = normalize_text_recursive(course_data)
                  course_data = normalize_symbol_recursive(course_data)
                  print(course_data)

            else:
                  print(f"No <h4> tag found with id='{course_codes}'")
            
      # Write to JSON
      output_file = f"/orcd/home/002/hnaka24/CourseFinder/scraped/amherst_courses_{semester}.json"
      with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
      
      data.append(course_data)
      
      with open(output_file, "w") as f:
            json.dump(data, f, indent=4)

      print(f"Data successfully written to {output_file}")
      
      loop.update()