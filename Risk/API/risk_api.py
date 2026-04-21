from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import pickle
import os
import gdown

app = FastAPI()

# -----------------------------
# 1. Load model
# -----------------------------
MODEL_PATH = "svm_model_proba.pkl"
GDRIVE_FILE_ID = "1vx3K2-unQ6oXbkTI8kVi3YRdDeqbiHwr"

def download_model():
    if not os.path.exists(MODEL_PATH):
        url = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}"
        gdown.download(url, MODEL_PATH, quiet=False)

# def load_model():
#     download_model()
#     with open(MODEL_PATH, "rb") as f:
#         return pickle.load(f)
import joblib

def load_model():
    download_model()
    return joblib.load(MODEL_PATH)

model = load_model()

# -----------------------------
# 2. Request schema
# -----------------------------
class InputData(BaseModel):
    la: float
    ld: float
    nf: float
    nd: float
    ns: float
    ent: float
    ndev: float
    age: float
    nuc: float
    aexp: float
    arexp: float
    asexp: float

# -----------------------------
# 3. Prediction endpoint (PROBABILITY)
# -----------------------------
@app.post("/predict")
def predict(data: InputData):
    features = np.array([[
        data.la, data.ld, data.nf, data.nd,
        data.ns, data.ent, data.ndev, data.age,
        data.nuc, data.aexp, data.arexp, data.asexp
    ]])

    # 🔥 probability output
    prob = model.predict_proba(features)[0][1]  # class 1 probability
    pred = int(prob >= 0.5)

    return {
        "prediction": pred,
        "bug_probability": float(prob)
    }