from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import joblib
import os
import requests
import smtplib
import threading
from email.mime.text import MIMEText
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= SERVE STATIC FILES =================
# Mount the current directory to serve index.html, style.css, script.js
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
def read_index():
    from fastapi.responses import FileResponse
    return FileResponse("index.html")

# ================= BEHAVIOR PROFILER CLASS (REQUIRED FOR JOBLIB) =================
class BehaviorProfiler:
    def __init__(self):
        self.means = None
        self.stds = None
        
    def fit(self, X):
        self.means = np.mean(X, axis=0)
        self.stds = np.std(X, axis=0)
        self.stds[self.stds == 0] = 1e-6
        return self
        
    def compute_score(self, sample):
        z_scores = np.abs((sample - self.means) / self.stds)
        # Find index of max deviation
        max_idx = np.argmax(z_scores)
        score = np.mean(z_scores) / 10.0
        return score, int(max_idx), float(z_scores[max_idx])

# ================= LOAD MODELS =================
try:
    rf_model = joblib.load('rf_model.pkl')
    xgb_model = joblib.load('xgb_model.pkl')
    scaler = joblib.load('scaler.pkl')
    profiler = joblib.load('behavior_profiler.pkl')
    MODELS_LOADED = True
    print("Models loaded successfully")
except Exception as e:
    print("Model loading failed:", e)
    MODELS_LOADED = False

# ================= TWILIO =================
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
TWILIO_TO_NUMBER = os.environ.get("TWILIO_TO_NUMBER", "")

def send_sms_alert(amount, confidence, reason):
    if not TWILIO_ACCOUNT_SID:
        print(f"[SMS MOCK] Rs.{amount} | {confidence:.2f}% | {reason}")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"

    data = {
        "From": TWILIO_FROM_NUMBER,
        "To": TWILIO_TO_NUMBER,
        "Body": f"🚨 Fraud Alert\nRs.{amount}\nConfidence: {confidence:.2f}%\n{reason}"
    }

    try:
        requests.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    except Exception as e:
        print("SMS error:", e)

# ================= EMAIL ALERT =================
EMAIL_SENDER   = "capstonealladistha2@gmail.com"
EMAIL_RECEIVER = "capstonealladistha2@gmail.com"
EMAIL_PASSWORD = "xdgejijxmqlawmvr"

def _send_email_worker(amount, confidence, reason, location):
    """Runs in a background thread so it never blocks the API response."""
    msg = MIMEText(f"""
🚨 Fraud Alert Detected

Amount    : ₹{amount}
Confidence: {confidence:.2f}%
Location  : {location}
Reason    : {reason}

This alert was generated automatically by the FraudCortex AI system.
""")
    msg['Subject'] = "🚨 Fraud Detection Alert – FraudCortex AI"
    msg['From']    = EMAIL_SENDER
    msg['To']      = EMAIL_RECEIVER

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("📧 Email alert sent")
    except Exception as e:
        print("Email error:", e)

def send_email_alert(amount, confidence, reason, location):
    """Fire-and-forget: sends email in a daemon thread."""
    t = threading.Thread(
        target=_send_email_worker,
        args=(amount, confidence, reason, location),
        daemon=True
    )
    t.start()

# ================= REQUEST MODEL =================
class PredictRequest(BaseModel):
    features: list[float]
    amount: float
    prev: list[float] = []
    location: str = "Unknown"

# ================= PREDICTION =================
@app.post("/predict")
def predict(request: PredictRequest):

    if not MODELS_LOADED:
        raise HTTPException(status_code=500, detail="Models not loaded")

    try:
        # -------- FIX 1: INPUT VALIDATION (CRITICAL) --------
        # Start with all features + amount
        model_input = request.features + [request.amount]
        amount = request.amount

        # Check expected size from scaler
        expected_features = scaler.mean_.shape[0]
        
        # If we have 30 but expect 29, it's likely a [Time, V1...V28, Amount] mismatch
        if len(model_input) == 30 and expected_features == 29:
            model_input = model_input[1:]

        # Apply strict resizing as requested
        if len(model_input) > expected_features:
            model_input = model_input[:expected_features]
        elif len(model_input) < expected_features:
            model_input = model_input + [0.0] * (expected_features - len(model_input))

        # -------- FIX 2: SAFE SCALING --------
        try:
            sample_scaled = scaler.transform([model_input])
        except Exception as e:
            print(f"Scaling error: {e}")
            return {
                "is_fraud": False, 
                "probability": 0.0, 
                "behavior_score": 0.0, 
                "reason": "Scaling error"
            }

        # -------- ML PREDICTION --------
        prob1 = rf_model.predict_proba(sample_scaled)[0][1]
        prob2 = xgb_model.predict_proba(sample_scaled)[0][1]
        prob = float((prob1 + prob2) / 2)

        # -------- FIX 3: BEHAVIOR INPUT FIX (NORMALIZED) --------
        b_score, max_feat_idx, max_z = profiler.compute_score(model_input)
        # FIX 1: LOGARITHMIC SCALING (REFINED FOR DEMO)
        scaled_b = np.log1p(b_score)
        norm_b = min(scaled_b / 0.18, 1.0) 

        # -------- FIX 6: FINAL SCORE (REFINED) --------
        final_score = (0.65 * prob) + (0.35 * norm_b)

        # -------- FRAUD LOGIC (REFINED) --------
        is_fraud = False
        reason = "Normal transaction"

        # REFINED FRAUD CONDITIONS (BALANCED FOR 4-6% RATE)
        if prob > 0.0014:
            is_fraud = True
            reason = "Moderate ML risk"
        
        elif norm_b > 0.95:
            is_fraud = True
            reason = "Behavioral anomaly"

        elif prob > 0.0008 and norm_b > 0.75:
            is_fraud = True
            reason = "Combined anomaly"
            
        elif final_score > 0.65:
            is_fraud = True
            reason = "Elevated risk"

        # -------- ALERTS (SMS + EMAIL) --------
        if is_fraud:
            confidence = max(prob, final_score) * 100
            send_sms_alert(amount, confidence, reason)
            
            # Send email ONLY for high-confidence fraud (exclude medium/moderate risk)
            if confidence >= 85 or reason in ["Behavioral anomaly", "Elevated risk"]:
                send_email_alert(amount, confidence, reason, request.location)

        # -------- RESPONSE --------
        feature_names = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount']
        # Trim to match expected features
        if len(feature_names) > expected_features:
             feature_names = feature_names[-expected_features:]

        return {
            "is_fraud": is_fraud,
            "probability": float(prob),
            "behavior_score": float(b_score),
            "reason": reason,
            "anomaly_feature": feature_names[max_feat_idx],
            "anomaly_deviation": float(max_z)
        }

    except Exception as e:
        # -------- FIX 7: ERROR HANDLING (NEVER CRASH) --------
        print(f"Backend Error: {e}")
        return {
            "is_fraud": False,
            "probability": 0.0,
            "behavior_score": 0.0,
            "reason": "System processing error",
            "anomaly_feature": "N/A",
            "anomaly_deviation": 0.0
        }

# ================= FEATURE IMPORTANCE =================
@app.get("/feature_importance")
def get_importance():
    if not MODELS_LOADED:
        return {"error": "Models not loaded"}
    
    # Get importance from RF model
    importances = rf_model.feature_importances_
    
    # Reconstruct feature names (matching logic in predict)
    expected_features = scaler.mean_.shape[0]
    all_names = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount']
    if len(all_names) > expected_features:
        names = all_names[-expected_features:]
    else:
        names = all_names
    
    # Map names to values and sort
    feat_imp = [{"name": n, "value": float(v)} for n, v in zip(names, importances)]
    feat_imp = sorted(feat_imp, key=lambda x: x["value"], reverse=True)[:10] # Top 10
    
    return {"importances": feat_imp}

# ================= RUN =================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)