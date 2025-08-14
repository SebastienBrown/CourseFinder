import torch
import torch.nn as nn
import torch.nn.functional as F
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from transformers import AutoTokenizer, AutoModel
from torch.utils.data import DataLoader, Dataset
import random
import json
from tqdm import tqdm
from dotenv import load_dotenv
load_dotenv()

# ========== Configuration ==========
dropbox = '/Users/hnaka24/Dropbox (Personal)/AmherstCourses/'
code = '/Users/hnaka24/Desktop/code/CourseFinder/'

JSON_PATH = dropbox + 'data/2_intermediate/1_llm_cleaned/amherst_courses_2324S.json'
# JSON_PATH = code + 'backend/data/amherst_courses_2324S.json'
save_dir = code + "3_embedding/sbert_contrastive_model"

MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
DROPOUT_RATE = 0.1
ALPHA = 0          # Weight for supervised loss (set to 0 for self-supervised only)
MAX_SELF_SUPERVISED = 10000  # Cap how many course descriptions to use
NUM_EPOCHS = 10
LR = 1e-5
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ========== Model Setup ==========

def mean_pooling(token_embeddings, attention_mask):
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size())
    return (token_embeddings * input_mask_expanded).sum(1) / input_mask_expanded.sum(1)

def get_tokenizer_and_model(model_name=MODEL_NAME, dropout_rate=DROPOUT_RATE):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    base_model = AutoModel.from_pretrained(model_name)

    class DropoutEncoder(nn.Module):
        def __init__(self, encoder, dropout_rate=0.1):
            super().__init__()
            self.encoder = encoder
            self.dropout = nn.Dropout(dropout_rate)

        def forward(self, **kwargs):
            outputs = self.encoder(**kwargs)
            token_embeddings = outputs.last_hidden_state
            pooled_output = mean_pooling(token_embeddings, kwargs["attention_mask"])
            return self.dropout(pooled_output)

    model = DropoutEncoder(base_model, dropout_rate=dropout_rate)
    return tokenizer, model

tokenizer, model = get_tokenizer_and_model()
model = model.to(DEVICE)

# ========== Load Course Descriptions for Self-Supervised ==========
def load_course_descriptions(json_path, max_texts=MAX_SELF_SUPERVISED):
    with open(json_path, 'r') as f:
        data = json.load(f)
    descriptions = []
    for course in data:
        if "description" in course and course["description"]:
            descriptions.append(course["description"])
    random.shuffle(descriptions)
    return descriptions[:max_texts]

self_supervised_texts = load_course_descriptions(JSON_PATH)

# ========== Manual Triplets (Supervised) ==========
manual_triplets = [
    ("The cat is on the mat.", "A cat sits on a rug.", "Bananas are yellow."),
    # Add more triplets manually as needed
]

# ========== Embedding ==========
def encode_texts(texts, model):
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors='pt').to(DEVICE)
    with torch.no_grad():
        return model(**inputs)

# ========== InfoNCE Loss ==========
def info_nce(anchor, positives, temperature=0.07):
    anchor = F.normalize(anchor, dim=1)
    positives = F.normalize(positives, dim=1)
    logits = torch.matmul(anchor, positives.T) / temperature
    labels = torch.arange(anchor.size(0), device=anchor.device)
    return F.cross_entropy(logits, labels)

# ========== Supervised Contrastive Loss ==========
def supervised_info_nce(model, triplets):
    anchors, positives, negatives = zip(*triplets)
    anchor_emb = encode_texts(anchors, model)
    pos_emb = encode_texts(positives, model)
    neg_emb = encode_texts(negatives, model)
    contrast_emb = torch.cat([pos_emb, neg_emb], dim=0)
    logits = torch.matmul(anchor_emb, contrast_emb.T) / 0.07
    labels = torch.arange(anchor_emb.size(0), device=DEVICE)
    return F.cross_entropy(logits, labels)

# ========== Self-Supervised Contrastive Loss ==========
class TextDataset(Dataset):
    def __init__(self, texts, tokenizer, max_length=128):
        self.encodings = tokenizer(texts, padding=True, truncation=True, max_length=max_length, return_tensors="pt")

    def __getitem__(self, idx):
        return {k: v[idx] for k, v in self.encodings.items()}

    def __len__(self):
        return len(self.encodings["input_ids"])

def self_supervised_info_nce(texts, model, tokenizer, batch_size=64):
    dataset = TextDataset(texts, tokenizer)
    loader = DataLoader(dataset, batch_size=batch_size, num_workers=0)
    embeddings = []

    model.train()  # IMPORTANT: enable dropout + gradient tracking
    for batch in tqdm(loader, desc="Self-supervised batches"):
        batch = {k: v.to(DEVICE) for k, v in batch.items()}
        emb = model(**batch)
        embeddings.append(emb)

    z = torch.cat(embeddings, dim=0)  # keep on DEVICE
    return info_nce(z, z)  # SimCSE-style: dropout gives different views


# ========== Combined Loss Function ==========
def combined_loss(model, triplets, texts, alpha=ALPHA):
    loss_sup = supervised_info_nce(model, triplets) if alpha > 0 and triplets else torch.tensor(0.0, device=DEVICE)
    loss_self = self_supervised_info_nce(texts, model, tokenizer)
    return alpha * loss_sup + (1 - alpha) * loss_self, loss_sup, loss_self

# ========== Optimizer ==========
optimizer = torch.optim.Adam(model.parameters(), lr=LR)
model.train()
print("Model loaded")

# ========== Training Loop ==========
for epoch in tqdm(range(NUM_EPOCHS), desc="Training"):
    optimizer.zero_grad()
    loss, loss_sup, loss_self = combined_loss(model, manual_triplets, self_supervised_texts, alpha=ALPHA)
    loss.backward()
    optimizer.step()
    tqdm.write(f"Epoch {epoch+1}: Total={loss.item():.4f} | Supervised={loss_sup.item():.4f} | Self-supervised={loss_self.item():.4f}")

# ========== Save Fine-tuned Model ==========
model.encoder.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)
print(f"Model and tokenizer saved to {save_dir}")
