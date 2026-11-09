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
        max_idx = np.argmax(z_scores)
        score = np.mean(z_scores) / 10.0
        return score, int(max_idx), float(z_scores[max_idx])

def simulate_predict():
    # Load models
    rf_model = joblib.load('c:/Users/charw/FraudDetectionApp_Antigravity/rf_model.pkl')
    xgb_model = joblib.load('c:/Users/charw/FraudDetectionApp_Antigravity/xgb_model.pkl')
    scaler = joblib.load('c:/Users/charw/FraudDetectionApp_Antigravity/scaler.pkl')
    profiler = joblib.load('c:/Users/charw/FraudDetectionApp_Antigravity/behavior_profiler.pkl')

    df = pd.read_csv('c:/Users/charw/FraudDetectionApp_Antigravity/creditcard.csv', nrows=1000)
    
    fraud_count = 0
    
    for i, row in df.iterrows():
        # model_input includes V1-V28 and Amount
        features = row.drop(['Time', 'Class'], errors='ignore').tolist()
        model_input = features

        sample_scaled = scaler.transform([model_input])

        prob1 = rf_model.predict_proba(sample_scaled)[0][1]
        prob2 = xgb_model.predict_proba(sample_scaled)[0][1]
        prob = float((prob1 + prob2) / 2)

        b_score, max_feat_idx, max_z = profiler.compute_score(model_input)
        
        # New normalization
        scaled_b = np.log1p(b_score)
        norm_b = min(scaled_b / 0.5, 1.0) 

        final_score = (0.85 * prob) + (0.15 * norm_b)

        is_fraud = False
        if prob > 0.75:
            is_fraud = True
        elif prob > 0.5 and norm_b > 0.8:
            is_fraud = True
        elif final_score > 0.85:
            is_fraud = True
            
        if is_fraud:
            fraud_count += 1
            
    print(f"Total Transactions: {len(df)}")
    print(f"Fraud Count: {fraud_count}")
    print(f"Fraud Rate: {(fraud_count / len(df)) * 100:.2f}%")

if __name__ == "__main__":
    simulate_predict()
