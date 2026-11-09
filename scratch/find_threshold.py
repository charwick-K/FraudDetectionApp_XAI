import pandas as pd
import numpy as np
import joblib

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
        score = np.mean(z_scores) / 10.0
        return score

def find_thresholds():
    print("Loading models and data...")
    rf_model = joblib.load('rf_model.pkl')
    xgb_model = joblib.load('xgb_model.pkl')
    scaler = joblib.load('scaler.pkl')
    profiler = joblib.load('behavior_profiler.pkl')
    
    df = pd.read_csv('creditcard.csv', nrows=5000)
    X = df.drop(['Class', 'Time'], axis=1, errors='ignore').values
    
    X_scaled = scaler.transform(X)
    
    print("Predicting probabilities...")
    prob1 = rf_model.predict_proba(X_scaled)[:, 1]
    prob2 = xgb_model.predict_proba(X_scaled)[:, 1]
    probs = (prob1 + prob2) / 2
    
    print("Computing behavior scores...")
    b_scores = []
    for row in X:
        b_scores.append(profiler.compute_score(row))
    b_scores = np.array(b_scores)
    
    scaled_b = np.log1p(b_scores)
    norm_b = np.minimum(scaled_b / 4.0, 1.0)
    
    final_scores = (0.65 * probs) + (0.35 * norm_b)
    
    # Sort final scores to find the threshold for 5%
    sorted_scores = np.sort(final_scores)[::-1]
    target_idx = int(len(sorted_scores) * 0.05)
    threshold = sorted_scores[target_idx]
    
    print(f"Threshold for 5% fraud rate on first 5000 rows: {threshold:.4f}")
    
    # Check rate at this threshold
    detected = np.sum(final_scores > threshold)
    print(f"Detected: {detected} ({detected/len(final_scores)*100:.2f}%)")
    
    return threshold

if __name__ == "__main__":
    find_thresholds()
