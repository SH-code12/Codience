import os
import json
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import hf_hub_download

# THIS MUST BE SET BEFORE IMPORTING KERAS
os.environ["KERAS_BACKEND"] = "tensorflow"

import keras
import tensorflow as tf
from transformers import TFDistilBertModel, DistilBertTokenizer

app = Flask(__name__)
CORS(app)

# --- 1. Define Custom Layer ---
@keras.saving.register_keras_serializable()
class DistilBertLayer(keras.layers.Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.distilbert = TFDistilBertModel.from_pretrained('distilbert-base-uncased', from_pt=True)
        self.distilbert.trainable = False

    def call(self, inputs):
        input_ids, attention_mask = inputs
        return self.distilbert(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state

    def get_config(self):
        return super().get_config()

# --- 2. Download from Hugging Face ---
REPO_ID = "MalakHisham/PR_Reviewer_Recommender"

print("Downloading model files from Hugging Face...")
model_path = hf_hub_download(repo_id=REPO_ID, filename="pr_recommender_final.keras")
id_map_path = hf_hub_download(repo_id=REPO_ID, filename="reviewer_id_map.json")
skill_cols_path = hf_hub_download(repo_id=REPO_ID, filename="skill_columns.json")

# --- 3. Load Model & Assets ---
print("Loading model into memory...")
model = keras.models.load_model(model_path, safe_mode=False)
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')

with open(id_map_path) as f:
    id_to_reviewer = json.load(f)
with open(skill_cols_path) as f:
    skill_cols = json.load(f)

MAX_LENGTH = 128
print("API is ready to serve requests!")

# --- 4. Define API Routes ---
def predict_pr(text):
    if not text.strip(): return None
    enc = tokenizer(text, truncation=True, padding='max_length', max_length=MAX_LENGTH, return_tensors='tf')
    inputs = [enc['input_ids'], enc['attention_mask']]
    preds = model.predict(inputs, verbose=0)
    
    reviewer_probs = preds['reviewer_output'][0]
    skill_scores = preds['skill_output'][0] * 5.0
    top3 = np.argsort(reviewer_probs)[-3:][::-1]
    
    return {
        "topReviewers": [{"reviewerName": id_to_reviewer[str(i)], "confidence": float(reviewer_probs[i])} for i in top3],
        "skills": [{"skillName": skill_cols[j], "score": float(skill_scores[j])} for j in range(len(skill_cols)) if skill_scores[j] > 2.0]
    }

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/recommend', methods=['POST'])
def recommend():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    title = str(data.get('title', '')).strip()
    body = str(data.get('body', '')).strip()
    text = f"{title} [SEP] {body}".strip()

    if not text or text == "[SEP]":
        return jsonify({"error": "Title or body required"}), 400

    try:
        return jsonify(predict_pr(text)), 200
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": "Server error processing prediction"}), 500

if __name__ == '__main__':
    # Used only for local testing, Gunicorn will handle production serving
    app.run(host='0.0.0.0', port=5000)