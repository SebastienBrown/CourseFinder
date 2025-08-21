# -----------------------------
# Functions
# -----------------------------
def canon_node_id(codes, semester):
    """
    Given a list like ['EDST-200','AMST-200','SOCI-200'] and semester like '2223F',
    return a stable, canonical node ID string that includes both course codes and semester.

    Why do this?
    - We want the same combination of codes AND semester to map to the same node,
      regardless of their order in the list. This allows us to parse cross-listed courses
      while distinguishing between different semesters of the same course.
    """
    # Build a cleaned list:
    # - str(c): ensure each element is a string
    # - .strip(): remove surrounding whitespace
    # - if c and str(c).strip(): skip Nones/empties
    cleaned = [str(c).strip() for c in codes if c and str(c).strip()]
    # Sort for order-independence (['B','A'] -> ['A','B'])
    cleaned_sorted = sorted(cleaned)
    # Join with '|' to create a single canonical ID, e.g., 'AMST-200|EDST-200|SOCI-200|2223F'
    return "|".join(cleaned_sorted + [str(semester).strip()])

dept_replacements = {
    "MUSL": "MUSI",
    "LATI": "CLAS",
    "GREE": "CLAS",
    "WAGS": "SWAG",
    "ARAB": "ASLC",
    "CHIN": "ASLC",
    "JAPA": "ASLC"
}

def normalize_codes(codes):
    """Apply department replacements to a list of course codes."""
    normalized = []
    for code in codes:
        if "-" in code:
            dept, rest = code.split("-", 1)
            dept = dept_replacements.get(dept, dept)  # replace if in dict
            normalized.append(f"{dept}-{rest}")
        else:
            normalized.append(code)
    return normalized