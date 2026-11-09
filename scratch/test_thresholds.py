
import numpy as np

# Sample data based on my analysis
# Probabilities: Mean=0.0001, Max=0.0017, 95th=0.0004
# B-Scores: Mean=0.0603, Max=0.2693, 95th=0.1148

probs = np.linspace(0, 0.0017, 200) # Simplified distribution
b_scores = np.linspace(0, 0.27, 200)

fraud_count = 0
for p, b in zip(probs, b_scores):
    scaled_b = np.log1p(b)
    norm_b = min(scaled_b / 0.12, 1.0)
    final_score = (0.65 * p) + (0.35 * norm_b)
    
    is_fraud = False
    if p > 0.001:
        is_fraud = True
    elif norm_b > 0.85:
        is_fraud = True
    elif p > 0.0004 and norm_b > 0.6:
        is_fraud = True
    elif final_score > 0.35:
        is_fraud = True
        
    if is_fraud:
        fraud_count += 1

print(f"Projected Fraud Count for 200 rows: {fraud_count} ({fraud_count/200*100}%)")
