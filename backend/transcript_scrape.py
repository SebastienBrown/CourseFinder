import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import re
import io
import json
import logging

# === Configure Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_courses_from_transcript(pdf_file_obj):
    logger.info("Starting course extraction from transcript")

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
        binarized = gray.point(lambda x: 0 if x < 140 else 255, "1")
        logger.debug("Image preprocessed for OCR")
        return binarized

    def extract_text_from_two_columns(image):
        width, height = image.size
        mid_x = width // 2
        logger.debug(f"Splitting image at midpoint: {mid_x}px")

        left = preprocess_image(image.crop((0, 0, mid_x, height)))
        right = preprocess_image(image.crop((mid_x, 0, width, height)))

        left_text = pytesseract.image_to_string(left)
        right_text = pytesseract.image_to_string(right)

        combined_text = left_text + "\n" + right_text
        logger.info(f"Extracted text from image: {len(combined_text)} characters")
        return combined_text

    # === Convert PDF bytes to images ===
    logger.info("Converting PDF to images")
    images = convert_from_bytes(pdf_file_obj.read())
    logger.info(f"PDF converted to {len(images)} page(s)")

    semesters = {}
    lines = []

    for i, img in enumerate(images):
        logger.info(f"Processing image {i+1}/{len(images)}")
        full_text = extract_text_from_two_columns(img)
        lines_from_img = full_text.splitlines()
        lines.extend(lines_from_img)
        logger.debug(f"Extracted {len(lines_from_img)} lines from page {i+1}")

    current_semester = None
    collecting = False

    logger.info("Parsing text for semesters and course codes")
    for line_num, line in enumerate(lines):
        line_clean = line.strip()

        if "accreditation" in line_clean.lower():
            logger.info(f"Found 'accreditation' at line {line_num}. Stopping parse.")
            break

        sem_match = semester_pattern.search(line_clean)
        if sem_match:
            current_semester = sem_match.group(0)
            if current_semester not in semesters:
                semesters[current_semester] = []
                logger.debug(f"Detected new semester: {current_semester}")
            collecting = True
            continue

        if collecting:
            if line_clean.lower().startswith("attempted"):
                collecting = False
                logger.debug(f"Stopping collection for semester: {current_semester}")
                continue

            codes = course_code_pattern.findall(line_clean)
            if current_semester and codes:
                normalized_codes = [code.strip().replace(" ", "-") for code in codes]
                semesters[current_semester].extend(normalized_codes)
                logger.debug(f"Added courses for {current_semester}: {normalized_codes}")

    logger.info("Translating semester names to codes")
    final_output = {}
    for sem, codes in semesters.items():
        semester_code = semester_code_map.get(sem)
        if semester_code:
            final_output[semester_code] = {"courses": codes}
            logger.info(f"{sem} → {semester_code}: {len(codes)} course(s)")
        else:
            logger.warning(f"No mapping found for semester: {sem}")

    logger.info("Course extraction complete")
    return final_output
