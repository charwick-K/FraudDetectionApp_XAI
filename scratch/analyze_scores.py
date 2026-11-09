
import pandas as pd
import requests
import numpy as np

def verify():
    df = pd.read_csv('creditcard.csv', nrows=200)
    probs = []
    b_scores = []
    final_scores = []
    
    for index, row in df.iterrows():
        features = row.iloc[:29].tolist()
        amount = float(row['Amount'])
        payload = {"features": features, "amount": amount}
        
        try:
            resp = requests.post("http://127.0.0.1:8000/predict", json=payload)
            if resp.status_code == 200:
                result = resp.json()
                probs.append(result.get('probability', 0))
                b_scores.append(result.get('behavior_score', 0))
                # Reconstruct final score logic from backend: (0.65 * prob) + (0.35 * norm_b)
                # But let's just look at the raw values first
        except:
            pass
            
    if probs:
        print(f"Probabilities: Mean={np.mean(probs):.4f}, Max={np.max(probs):.4f}, 95th={np.percentile(probs, 95):.4f}")
        print(f"B-Scores: Mean={np.mean(b_scores):.4f}, Max={np.max(b_scores):.4f}, 95th={np.percentile(b_scores, 95):.4f}")
    else:
        print("No data.")

if __name__ == "__main__":
    verify()
