# app.py
import math

from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
import numpy as np
import pickle
import os
import sys
import gdown
import joblib
import asyncio
import httpx

# --- Robust Logging Setup ---
# Write logs to stderr so they appear in Hugging Face build logs
def log(message: str):
    print(message, file=sys.stderr)

# --- Configuration ---
MODEL_PATH = "svm_model_proba.pkl"
GDRIVE_FILE_ID = "1zbZ_fZ8UCoeB3OEPk4sIhE0it0PniQuI"
DOTNET_BASE_URL = "http://localhost:5051/api/GitHubAuth"
# Redirect HF cache to a writable directory
os.environ["HF_HOME"] = "/app/hf_cache"

# --- Model Download & Loading ---
def download_model():
    """Downloads the model from Google Drive if it doesn't exist."""
    if not os.path.exists(MODEL_PATH):
        log(f"Model not found locally. Downloading from Google Drive (ID: {GDRIVE_FILE_ID})...")
        url = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}"
        try:
            gdown.download(url, MODEL_PATH, quiet=False)
            log(f"Successfully downloaded model to {MODEL_PATH}")
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(f"Download failed: {MODEL_PATH} not found.")
        except Exception as e:
            log(f"CRITICAL ERROR during gdown download: {e}")
            raise
    else:
        log(f"Model found at {MODEL_PATH}")

def load_model():
    """Loads the model from disk, handling potential pickle/joblib formats."""
    download_model()
    log(f"Loading model from {MODEL_PATH}...")
    try:
        # First attempt with joblib
        model = joblib.load(MODEL_PATH)
        log("Model loaded successfully with joblib.")
        return model
    except Exception as joblib_err:
        log(f"joblib failed, falling back to pickle... Error: {joblib_err}")
        try:
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            log("Model loaded successfully with pickle.")
            return model
        except Exception as pickle_err:
            log(f"CRITICAL ERROR: Both joblib and pickle failed to load the model. Pickle error: {pickle_err}")
            raise

# --- FastAPI App Setup ---
app = FastAPI()

log("Attempting to load the model...")
try:
    model = load_model()
    log("Model loading process finished.")
except Exception as e:
    log(f"FATAL: Model could not be loaded. The API will not function. Error: {e}")
    model = None

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


class PredictResponse(BaseModel):
    prediction: int
    bug_probability: float



@app.post("/predict")
def predict(data: InputData):
    """Predicts based on the provided input features."""
    if model is None:
        return {"error": "Model not loaded. The API is unavailable."}
    features = np.array([[
        data.la, data.ld, data.nf, data.nd,
        data.ns, data.ent, data.ndev, data.age,
        data.nuc, data.aexp, data.arexp, data.asexp
    ]])

    # 🔥 probability output
    prob = model.predict_proba(features)[0][1]  # class 1 probability

    return {

        "bug_probability": float(prob)
    }


@app.get("/orchestrate/{owner}/{repo:path}/{pull_number}")
async def get_combined_prediction(owner: str, repo: str, pull_number: int):
    # verify=False handles local SSL/HTTPS issues; timeout handles slow GitHub calls
    async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
        # Use 127.0.0.1 specifically to avoid IPv6 "Connection Refused"
        base = f"http://127.0.0.1:5051/api/GitHubAuth/{owner}/{repo}/pulls/{pull_number}"

        # 1. Define the endpoints (Reverting to individual calls since .NET is fixed)
        endpoints = {
            "metrics":f"{base}/metrics",
            "history":f"{base}/history",
            "files":f"{base}/files",
            "experience":f"{base}/experience"

        }


        # 2. Call all .NET APIs concurrently
        tasks = {key: client.get(url) for key, url in endpoints.items()}
        responses = await asyncio.gather(*tasks.values(), return_exceptions=True)

        results = {}
        for key, response in zip(tasks.keys(), responses):
            # Detailed error reporting
            if isinstance(response, Exception):
                raise HTTPException(
                    status_code=502,
                    detail=f"Connection to .NET failed on {key}: {type(response).__name__}"
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f".NET returned {response.status_code} for {key}. Body: {response.text}"
                )

            # Extract the value (handling both raw numbers and JSON)
            try:
                val = response.json()
                results[key] = float(val) if not isinstance(val, dict) else float(val.get("value", 0))
            except:
                results[key] = 0.0


        print("results:", results )
        la = results.get("la", 0)
        ld = results.get("ld", 0)
        nf = results.get("nf", 0)
        nd = results.get("nd", 0)
        ns = results.get("ns", 0)
        ent = results.get("ent", 0)
        ndev = results.get("ndev", 0)
        age = results.get("age", 0)
        nuc = results.get("nuc", 0)
        aexp = results.get("exp", 0)
        arexp = results.get("rexp", 0)
        asexp = results.get("sexp", 0)

        input_obj = InputData(
            # Size & Diffusion (Usually used as raw counts or logged depending on skew)
            la=la,
            ld=ld,
            nf=nf,
            nd=nd,
            ns=ns,
            ent=ent,

            # History & Experience (Kamei explicitly logs these)
            ndev=math.log1p(ndev),
            age=math.log1p(age),

            # NUC is usually logged after normalization by NF
            nuc=math.log1p(nuc / nf) if nf > 0 else 0,

            # Experience metrics
            aexp=math.log1p(aexp),
            arexp=math.log1p(arexp),
            asexp=math.log1p(asexp)
        )

        # 4. Predict
        return predict(input_obj)