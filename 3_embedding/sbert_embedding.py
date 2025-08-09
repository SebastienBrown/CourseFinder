import torch
from transformers import AutoTokenizer, AutoModel
import json
from tqdm import tqdm

# ==== Configuration ====
dropbox = '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/'
code = '/Users/hnaka24/Desktop/code/CourseFinder/'

model = "sbert"
mode = "off_the_shelf"  # "off_the_shelf" "self_supervised"
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
model_dir = code + "3_embedding/sbert_contrastive_model"  # folder where your fine-tuned model and tokenizer are saved

json_path = dropbox + 'data/2_intermediate/1_llm_cleaned/amherst_courses_2324S.json'
output_folder = dropbox + f'data/2_intermediate/2_embeddings/{model}_{mode}/'
output_json_path = output_folder + 'output_embeddings_2324S.json'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==== Load tokenizer and model ====
if mode != "off_the_shelf":
    print(f"Loading local model from: {model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    base_model = AutoModel.from_pretrained(model_dir)
else:
    print(f"Loading off-the-shelf model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    base_model = AutoModel.from_pretrained(MODEL_NAME)

# ==== Load tokenizer and model ====
tokenizer = AutoTokenizer.from_pretrained(model_dir)
base_model = AutoModel.from_pretrained(model_dir)

def mean_pooling(token_embeddings, attention_mask):
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * input_mask_expanded).sum(1) / input_mask_expanded.sum(1)

class InferenceModel(torch.nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder

    def forward(self, **kwargs):
        outputs = self.encoder(**kwargs)
        token_embeddings = outputs.last_hidden_state
        return mean_pooling(token_embeddings, kwargs["attention_mask"])

model = InferenceModel(base_model).to(device)
model.eval()

# ==== Load original JSON ====
with open(json_path, 'r') as f:
    courses = json.load(f)

# Extract descriptions (keep track of indices)
descriptions = []
valid_indices = []
for i, course in enumerate(courses):
    desc = course.get("description", "")
    if desc:
        descriptions.append(desc)
        valid_indices.append(i)
    else:
        # If no description, add None to keep list lengths aligned
        descriptions.append(None)

# ==== Batch encode only descriptions that exist ====
batch_size = 64
all_embeddings = []

for i in tqdm(range(0, len(valid_indices), batch_size), desc="Embedding descriptions"):
    batch_texts = [descriptions[idx] for idx in valid_indices[i:i+batch_size]]
    encoded_inputs = tokenizer(batch_texts, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
    
    with torch.no_grad():
        embeddings = model(**encoded_inputs)
    
    all_embeddings.append(embeddings.cpu())

all_embeddings = torch.cat(all_embeddings, dim=0)  # (num_descriptions, embedding_dim)

# ==== Add embeddings back to courses JSON ====
embedding_dim = all_embeddings.size(1)
for emb_idx, course_idx in enumerate(valid_indices):
    emb_list = all_embeddings[emb_idx].tolist()
    # Optionally round floats for compactness
    emb_list_rounded = [round(x, 8) for x in emb_list]
    courses[course_idx]['embedding'] = emb_list_rounded

# ==== Save updated JSON ====
with open(output_json_path, 'w') as f:
    json.dump(courses, f, indent=4)

print(f"Saved JSON with embeddings to {output_json_path}")
