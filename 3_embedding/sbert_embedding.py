import torch
from transformers import AutoTokenizer, AutoModel
import sys

# Load fine-tuned model and tokenizer
save_dir = "fine_tuned_sbert"
tokenizer = AutoTokenizer.from_pretrained(save_dir)
model = AutoModel.from_pretrained(save_dir)
model.eval()

def compute_embedding(text):
    inputs = tokenizer([text], padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0]  # CLS token
    return embedding.squeeze().numpy()

if __name__ == "__main__":
    # Example usage: python sbert_embedding.py "Your text here"
    text = sys.argv[1] if len(sys.argv) > 1 else "The cat is on the mat."
    emb = compute_embedding(text)
    print(emb) 