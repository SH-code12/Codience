from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import pickle
import os
import gdown

app = FastAPI()

# -----------------------------
# 1. Load model from Google Drive (or local cache)
# -----------------------------
MODEL_PATH = "svm_model.pkl"
GDRIVE_FILE_ID = "1vx3K2-unQ6oXbkTI8kVi3YRdDeqbiHwr"

def download_model():
    if not os.path.exists(MODEL_PATH):
        url = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}"
        gdown.download(url, MODEL_PATH, quiet=False)

def load_model():
    download_model()
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

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
# 3. Prediction endpoint
# -----------------------------
@app.post("/predict")
def predict(data: InputData):
    features = np.array([[
        data.la, data.ld, data.nf, data.nd,
        data.ns, data.ent, data.ndev, data.age,
        data.nuc, data.aexp, data.arexp, data.asexp
    ]])

    prediction = model.predict(features)[0].item()

    return {"prediction": prediction}
