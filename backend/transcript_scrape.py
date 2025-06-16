import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import re
import io
import json

def extract_courses_from_transcript(pdf_file_obj):
    # === Mapping semester names to codes ===
    semester_code_map = {
        "Fall 2020": "2021F",
        "January 2021": "2021J",
        "Spring 2021": "2021S",
        "Fall 2021": "2122F",
        "January 2022": "2122J",
        "Spring 2022": "2122S",
        "Fall 2022": "2223F",
        "Spring 2023": "2223S",
        "Fall 2023": "2324F",
        "Spring 2024": "2324S",
        "Fall 2024": "2425F",
        "Spring 2025": "2425S",
        "Fall 2025": "2526F",
        "Spring 2026": "2526S",
    }

    semester_pattern = re.compile(r"(Spring|Fall|Summer|Winter|January)\s+\d{4}", re.IGNORECASE)
    course_code_pattern = re.compile(r"\b([A-Z]{4}\s?\d{3}[A-Z]*)\b")

    def preprocess_image(img):
        gray = img.convert("L")
        return gray.point(lambda x: 0 if x < 140 else 255, "1")

    def extract_text_from_two_columns(image):
        width, height = image.size
        mid_x = width // 2

        left = preprocess_image(image.crop((0, 0, mid_x, height)))
        right = preprocess_image(image.crop((mid_x, 0, width, height)))

        left_text = pytesseract.image_to_string(left)
        right_text = pytesseract.image_to_string(right)
        return left_text + "\n" + right_text

    # === Convert PDF bytes to images ===
    images = convert_from_bytes(pdf_file_obj.read())

    semesters = {}
    lines = []

    for img in images:
        full_text = extract_text_from_two_columns(img)
        lines.extend(full_text.splitlines())
    
    print(full_text)

    current_semester = None
    collecting = False

    for line in lines:
        line_clean = line.strip()

        if "accreditation" in line_clean.lower():
            break

        sem_match = semester_pattern.search(line_clean)
        if sem_match:
            current_semester = sem_match.group(0)
            if current_semester not in semesters:
                semesters[current_semester] = []
            collecting = True
            continue

        if collecting:
            if line_clean.lower().startswith("attempted"):
                collecting = False
                continue

            codes = course_code_pattern.findall(line_clean)
            if current_semester and codes:
                semesters[current_semester].extend(
                    code.strip().replace(" ", "-") for code in codes
                )

    # === Translate semester names to codes ===
    final_output = {}
    for sem, codes in semesters.items():
        semester_code = semester_code_map.get(sem)
        if semester_code:
            final_output[semester_code] = {"courses": codes}

    print(final_output)

    return final_output
