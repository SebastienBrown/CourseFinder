import json

file_path = "./similarity/output_similarity_all.json"

with open(file_path, "r") as f:
    data = json.load(f)

# Recursively replace course code
def replace_codes(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "course_codes" and v == ["FYSE 102"]:
                obj[k] = ["FYSE-102"]
            elif k == "course_codes" and v == ["FYSE 103"]:
                obj[k] = ["FYSE-103"]
            else:
                replace_codes(v)
    elif isinstance(obj, list):
        for item in obj:
            replace_codes(item)

replace_codes(data)

with open(file_path, "w") as f:
    json.dump(data, f, indent=4)

print("Done cleaning!")
