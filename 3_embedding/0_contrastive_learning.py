import torch
import torch.nn as nn
import torch.nn.functional as F
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from transformers import AutoTokenizer, AutoModel
from torch.utils.data import DataLoader, Dataset
import random
import json
import pandas as pd
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv
load_dotenv()

# ========================================
# Configuration 
# ========================================
dropbox = os.environ["DROPBOX"]
code = os.environ["CODE"]

json_path = os.environ["CONTRASTIVE_JSON_PATH"]
save_dir = os.environ["CONTRASTIVE_SAVE_DIR"]

model_name = os.environ["SBERT_MODEL_NAME"]
dropout_rate = float(os.environ["CONTRASTIVE_DROPOUT_RATE"])
alpha = float(os.environ["CONTRASTIVE_ALPHA"])  # Weight for supervised loss
max_self_supervised = int(os.environ["CONTRASTIVE_MAX_SELF_SUPERVISED"])
num_epochs = int(os.environ["CONTRASTIVE_NUM_EPOCHS"])
lr = float(os.environ["CONTRASTIVE_LR"])
random_seed = int(os.environ["CONTRASTIVE_RANDOM_SEED"])
diagnostics_path = os.environ["CONTRASTIVE_DIAGNOSTICS_PATH"]

# Early stopping variables
best_val_loss = float('inf')
patience = 3
patience_counter = 0

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Set random seed for reproducibility
random.seed(random_seed)
np.random.seed(random_seed)
torch.manual_seed(random_seed)

# ========================================
# Functions
# ========================================
def find_course_description(course_info, course_data):
    """Find course description by matching course code"""
    semester, course_code = course_info.split(', ')
    
    for course in course_data:
        # Check if semester matches
        if course.get('semester') != semester:
            continue
            
        # Handle case where course_codes might be a string or list
        course_codes = course.get('course_codes', [])
        if isinstance(course_codes, str):
            course_codes = [course_codes]
        
        if course_code in course_codes:
            return course.get('description', '')
    
    print(f"Warning: No description found for {course_info}")
    return ''

def create_triplets(pos_pairs, neg_pairs):
    """Create triplets from positive and negative pairs"""
    triplets = []
    
    # For each positive pair, find a corresponding negative pair
    for i, (pos_anchor, pos_positive) in enumerate(pos_pairs):
        if i < len(neg_pairs):
            neg_anchor, neg_negative = neg_pairs[i]
            # Create triplet: (anchor, positive, negative)
            triplets.append((pos_anchor, pos_positive, neg_negative))
    
    return triplets

def encode_texts(texts, model):
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors='pt').to(device)
    return model(**inputs)

def compute_validation_loss(model, val_triplets):
    """Compute validation loss on validation triplets"""
    if not val_triplets:
        return float('inf')
    
    model.eval()
    total_loss = 0.0
    num_batches = 0
    
    # Process validation data in batches
    batch_size = 32
    for i in range(0, len(val_triplets), batch_size):
        batch_triplets = val_triplets[i:i + batch_size]
        
        anchors, positives, negatives = zip(*batch_triplets)
        anchor_emb = encode_texts(anchors, model)
        pos_emb = encode_texts(positives, model)
        neg_emb = encode_texts(negatives, model)
        
        contrast_emb = torch.cat([pos_emb, neg_emb], dim=0)
        logits = torch.matmul(anchor_emb, contrast_emb.T) / 0.07
        labels = torch.arange(anchor_emb.size(0), device=device)
        loss = F.cross_entropy(logits, labels)
        
        total_loss += loss.item()
        num_batches += 1
    
    model.train()
    return total_loss / num_batches if num_batches > 0 else float('inf')

def create_supervised_pairs(course_rows, course_data):
    """Create positive and negative pairs from diagnostics data"""
    pos_pairs = []
    neg_pairs = []
    
    for row in course_rows:
        # Extract courses A, B, C, D
        course_a_info = row[0]['full_info']
        course_b_info = row[1]['full_info']
        course_c_info = row[2]['full_info']
        course_d_info = row[3]['full_info']
        
        # Get descriptions for each course
        desc_a = find_course_description(course_a_info, course_data)
        desc_b = find_course_description(course_b_info, course_data)
        desc_c = find_course_description(course_c_info, course_data)
        desc_d = find_course_description(course_d_info, course_data)
        
        # Only create pairs if we have valid descriptions
        if desc_a and desc_b and desc_c and desc_d:
            # Positive pairs: A-B, A-C, B-D, C-D
            pos_pairs.extend([
                (desc_a, desc_b),
                (desc_a, desc_c),
                (desc_b, desc_d),
                (desc_c, desc_d)
            ])
            
            # Negative pairs: A-D, B-C
            neg_pairs.extend([
                (desc_a, desc_d),
                (desc_b, desc_c)
            ])
    
    return pos_pairs, neg_pairs

# ========================================
# Prepare Supervised Training Data
# ========================================
# Load course data for lookup
print("Loading course data for description lookup...")
with open(json_path, 'r') as f:
    course_data = json.load(f)

# Load and process diagnostics data
print("Loading diagnostics dataset...")
df = pd.read_csv(diagnostics_path)
print(f"Loaded diagnostics dataset with {len(df)} rows")

# Parse course information from each row of the diagnostics data
all_courses = []
for idx, row in df.iterrows():
    row_courses = []
    for col in ['A', 'B', 'C', 'D']:
        course_info = row[col].strip('"')  # Remove quotes
        semester, course_code = course_info.split(', ')
        row_courses.append({
            'semester': semester,
            'course_code': course_code,
            'full_info': course_info
        })
    all_courses.append(row_courses)

# Split diagnostics data into training and validation sets
n_total = len(all_courses)
n_train = int(n_total * 0.8)  # 80% for training
n_val = n_total - n_train  # 20% for validation

# Shuffle and split
indices = list(range(n_total))
random.shuffle(indices)

train_indices = indices[:n_train]
val_indices = indices[n_train:]

train_courses = [all_courses[i] for i in train_indices]
val_courses = [all_courses[i] for i in val_indices]

print(f"Split data: {len(train_courses)} training rows ({n_train/n_total*100:.1f}%), {len(val_courses)} validation rows ({n_val/n_total*100:.1f}%)")

# Pull descriptions from course data and save as positive and negative pairs
train_pos_pairs, train_neg_pairs = create_supervised_pairs(train_courses, course_data)
print(f"Created {len(train_pos_pairs)} supervised positive pairs and {len(train_neg_pairs)} negative pairs")

val_pos_pairs, val_neg_pairs = create_supervised_pairs(val_courses, course_data)
print(f"Created {len(val_pos_pairs)} validation positive pairs and {len(val_neg_pairs)} negative pairs")

# ========================================
# Prepare Self-Supervised Training Data
# ========================================
positive_pairs = []
negative_pairs = []

# Get all courses with descriptions
valid_courses = []
for course in course_data:
    if course.get('description'):
        valid_courses.append(course)

print(f"Creating self-supervised pairs from {len(valid_courses)} valid courses...")

# Create set of positive pairs from diagnostics CSV for checking
diagnostics_positive_pairs = set()
for row in all_courses:
    # Extract course info for each row
    course_a_info = row[0]['full_info']  # e.g., "2324S, ARHA-225"
    course_b_info = row[1]['full_info']  # e.g., "2324S, ARHA-130"
    course_c_info = row[2]['full_info']  # e.g., "2324S, ECON-111E"
    course_d_info = row[3]['full_info']  # e.g., "2425S, ECON-414"
    
    # Add positive pairs from diagnostics (A-B, A-C, B-D, C-D)
    diagnostics_positive_pairs.add((course_a_info, course_b_info))
    diagnostics_positive_pairs.add((course_b_info, course_a_info))  # Add reverse too
    diagnostics_positive_pairs.add((course_a_info, course_c_info))
    diagnostics_positive_pairs.add((course_c_info, course_a_info))
    diagnostics_positive_pairs.add((course_b_info, course_d_info))
    diagnostics_positive_pairs.add((course_d_info, course_b_info))
    diagnostics_positive_pairs.add((course_c_info, course_d_info))
    diagnostics_positive_pairs.add((course_d_info, course_c_info))

print(f"Found {len(diagnostics_positive_pairs)} positive pairs in diagnostics CSV")

# Create all possible pairs for sampling without replacement
all_possible_pairs = []
for i in range(len(valid_courses)):
    for j in range(i + 1, len(valid_courses)):
        course1 = valid_courses[i]
        course2 = valid_courses[j]
        
        # Create course info strings for comparison (Handle case where course_codes might be a string or list
        course1_codes = course1['course_codes'] if isinstance(course1['course_codes'], list) else [course1['course_codes']]
        course2_codes = course2['course_codes'] if isinstance(course2['course_codes'], list) else [course2['course_codes']]
        
        # Check if they're in the same department
        dept1 = set(code[:4] for code in course1_codes if len(code) >= 4)
        dept2 = set(code[:4] for code in course2_codes if len(code) >= 4)
        same_dept = bool(dept1.intersection(dept2)) # checks for intersections of department codes
        
        all_possible_pairs.append({
            'course1': course1,
            'course2': course2,
            'same_dept': same_dept,
            'description1': course1['description'],
            'description2': course2['description']
        })

# Shuffle all possible pairs
random.shuffle(all_possible_pairs)

# Sample without replacement
max_pairs = len(train_pos_pairs)
for pair_data in all_possible_pairs:
    if len(positive_pairs) >= max_pairs and len(negative_pairs) >= max_pairs:
        break
        
    same_dept = pair_data['same_dept']
    desc1 = pair_data['description1']
    desc2 = pair_data['description2']
    
    # Add positive pairs if they are in the same department
    if same_dept and len(positive_pairs) < max_pairs:
        positive_pairs.append((desc1, desc2))
    
    # Add negative pairs if they are not in the same department
    elif not same_dept and len(negative_pairs) < max_pairs:
        
        # Don't include if this pair is a positive pair in diagnostics CSV
        is_positive_in_diagnostics = False
        
        # Extract semester and course codes for comparison
        semester1 = pair_data['course1']['semester']
        semester2 = pair_data['course2']['semester']
        course1_codes = pair_data['course1']['course_codes'] if isinstance(pair_data['course1']['course_codes'], list) else [pair_data['course1']['course_codes']]
        course2_codes = pair_data['course2']['course_codes'] if isinstance(pair_data['course2']['course_codes'], list) else [pair_data['course2']['course_codes']]
        
        # Check if any combination of course codes from these two courses appears in diagnostics
        for course1_code in course1_codes:
            for course2_code in course2_codes:
                # Create the pair format that would appear in diagnostics
                diagnostics_pair1 = (f"{semester1}, {course1_code}", f"{semester2}, {course2_code}")
                diagnostics_pair2 = (f"{semester2}, {course2_code}", f"{semester1}, {course1_code}")
                
                if diagnostics_pair1 in diagnostics_positive_pairs or diagnostics_pair2 in diagnostics_positive_pairs:
                    is_positive_in_diagnostics = True
                    break
            if is_positive_in_diagnostics:
                break
        
        if not is_positive_in_diagnostics:
            negative_pairs.append((desc1, desc2))

print(f"Created {len(positive_pairs)} self-supervised positive pairs and {len(negative_pairs)} negative pairs")

# Convert to triplets format (anchor, positive, negative)
train_triplets = create_triplets(train_pos_pairs, train_neg_pairs)
val_triplets = create_triplets(val_pos_pairs, val_neg_pairs)
self_sup_triplets = create_triplets(positive_pairs, negative_pairs)

print(f"Created {len(train_triplets)} supervised training triplets, {len(val_triplets)} validation triplets, and {len(self_sup_triplets)} self-supervised triplets")

# ========================================
# Prepare Model
# ========================================
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
        input_mask_expanded = kwargs["attention_mask"].unsqueeze(-1).expand(token_embeddings.size())
        pooled_output = (token_embeddings * input_mask_expanded).sum(1) / input_mask_expanded.sum(1)
        return self.dropout(pooled_output)

model = DropoutEncoder(base_model, dropout_rate=dropout_rate)
model = model.to(device)

# Optimizer
optimizer = torch.optim.Adam(model.parameters(), lr=lr)
model.train()
print("Model loaded")

# ========================================
# Train Model
# ========================================
for epoch in tqdm(range(num_epochs), desc="Training"):
    optimizer.zero_grad()
    
    # Get mixed batch based on alpha
    n_supervised = int(32 * alpha)
    n_self_supervised = 32 - n_supervised
    
    # Sample from supervised triplets
    if len(train_triplets) > 0:
        supervised_batch = random.sample(train_triplets, min(n_supervised, len(train_triplets)))
    else:
        supervised_batch = []
    
    # Sample from self-supervised triplets
    if len(self_sup_triplets) > 0:
        self_supervised_batch = random.sample(self_sup_triplets, min(n_self_supervised, len(self_sup_triplets)))
    else:
        self_supervised_batch = []
    
    # Combine batches
    batch_triplets = supervised_batch + self_supervised_batch
    
    # # Pad with random samples if needed
    # while len(batch_triplets) < 32 and (train_triplets or self_sup_triplets):
    #     if random.random() < ALPHA and train_triplets:
    #         batch_triplets.append(random.choice(train_triplets))
    #     elif self_sup_triplets:
    #         batch_triplets.append(random.choice(self_sup_triplets))
    
    if batch_triplets:
        # Compute loss
        anchors, positives, negatives = zip(*batch_triplets)
        anchor_emb = encode_texts(anchors, model)
        pos_emb = encode_texts(positives, model)
        neg_emb = encode_texts(negatives, model)
        
        contrast_emb = torch.cat([pos_emb, neg_emb], dim=0)
        logits = torch.matmul(anchor_emb, contrast_emb.T) / 0.07
        labels = torch.arange(anchor_emb.size(0), device=device)
        loss = F.cross_entropy(logits, labels)
        
        loss.backward()
        optimizer.step()
        
        # Compute validation loss
        val_loss = compute_validation_loss(model, val_triplets)
        
        # Early stopping check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model
            model.encoder.save_pretrained(save_dir)
            tokenizer.save_pretrained(save_dir)
        else:
            patience_counter += 1
        
        tqdm.write(f"Epoch {epoch+1}: Train Loss={loss.item():.4f} | Val Loss={val_loss:.4f} | Batch size={len(batch_triplets)} | Patience={patience_counter}/{patience}")
        
        # Early stopping
        if patience_counter >= patience:
            tqdm.write(f"Early stopping triggered after {epoch+1} epochs")
            break
    else:
        tqdm.write(f"Epoch {epoch+1}: No valid triplets in batch")

# Final evaluation
print("\n" + "="*50)
print("FINAL EVALUATION")
print("="*50)

# Load best model if early stopping was used
if os.path.exists(save_dir):
    print("Loading best model from early stopping...")
    model.encoder = AutoModel.from_pretrained(save_dir)
    model = model.to(device)

# Final validation loss
final_val_loss = compute_validation_loss(model, val_triplets)
print(f"Final Validation Loss: {final_val_loss:.4f}")
print(f"Best Validation Loss: {best_val_loss:.4f}")

# Save Final Model
model.encoder.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)
print(f"Model and tokenizer saved to {save_dir}")

# Save training metrics
metrics = {
    "best_val_loss": best_val_loss,
    "final_val_loss": final_val_loss,
    "epochs_trained": epoch + 1,
    "early_stopping_triggered": patience_counter >= patience
}

import json
with open(save_dir + "/training_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
print(f"Training metrics saved to {save_dir}/training_metrics.json")
