import pdfplumber
import re
import logging

# === Configure Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_courses_from_transcript(pdf_file_obj):
    logger.info("Starting course extraction from transcript")

    # Mapping semester names to codes
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

    semesters = {}

    with pdfplumber.open(pdf_file_obj) as pdf:
        logger.info(f"Opened PDF with {len(pdf.pages)} pages")

        for page_num, page in enumerate(pdf.pages, start=1):
            width = page.width
            height = page.height
            mid_x = width / 2

            logger.info(f"Processing page {page_num}/{len(pdf.pages)} with size {width}x{height}")

            # Define left and right column bounding boxes
            left_bbox = (0, 0, mid_x, height)
            right_bbox = (mid_x, 0, width, height)

            # Extract words from left column
            left_words = page.within_bbox(left_bbox).extract_words()
            # Extract words from right column
            right_words = page.within_bbox(right_bbox).extract_words()

            def words_to_lines(words):
                lines = []
                current_line_y = None
                current_line_words = []

                for word in words:
                    if current_line_y is None or abs(word['top'] - current_line_y) > 3:
                        if current_line_words:
                            line_text = " ".join(w['text'] for w in current_line_words)
                            lines.append(line_text)
                        current_line_words = [word]
                        current_line_y = word['top']
                    else:
                        current_line_words.append(word)

                if current_line_words:
                    line_text = " ".join(w['text'] for w in current_line_words)
                    lines.append(line_text)
                return lines

            left_lines = words_to_lines(left_words)
            right_lines = words_to_lines(right_words)

            # Process both columns independently
            for col_lines, col_name in [(left_lines, "left"), (right_lines, "right")]:
                logger.debug(f"Processing {len(col_lines)} lines from {col_name} column on page {page_num}")

                current_semester = None
                collecting = False

                for line_num, line in enumerate(col_lines):
                    line_clean = line.strip()

                    # Print each line with info about page and column
                    print(f"[Page {page_num}][{col_name} column][Line {line_num+1}]: {line_clean}")

                    if "accreditation" in line_clean.lower():
                        logger.info(f"Found 'accreditation' at line {line_num} in {col_name} column. Stopping parse.")
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

                        # Remove all lowercase letters before running regex
                        line_clean_no_lower = re.sub(r'[a-z]', '', line_clean)
                        codes = course_code_pattern.findall(line_clean_no_lower)
                        if current_semester and codes:
                            normalized_codes = [code.strip().replace(" ", "-") for code in codes]
                            semesters[current_semester].extend(normalized_codes)
                            logger.debug(f"Added courses for {current_semester} from {col_name} column: {normalized_codes}")

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
