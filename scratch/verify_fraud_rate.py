import pandas as pd
import requests
import json
import time
import numpy as np

def test_fraud_rate():
    # Synthetic test data to simulate realistic variations
    # 29 features
    test_data = []
    
    # Normal transactions (95%)
    for _ in range(95):
        test_data.append({"features": list(np.random.normal(0, 0.5, 29)), "amount": float(np.random.uniform(10, 500))})
    
    # Behavioral anomalies (Moderate)
    for _ in range(3):
        test_data.append({"features": list(np.random.normal(0, 5.0, 29)), "amount": float(np.random.uniform(500, 2000))})
    
    # Extreme anomalies
    for _ in range(2):
        test_data.append({"features": list(np.random.normal(0, 15.0, 29)), "amount": float(np.random.uniform(2000, 5000))})
    
    fraud_count = 0
    total = len(test_data)
    
    print(f"Testing {total} transactions...")
    
    results_summary = {}
    
    for index, item in enumerate(test_data):
        payload = {
            "features": item["features"],
            "amount": item["amount"]
        }
        
        try:
            resp = requests.post("http://127.0.0.1:8000/predict", json=payload)
            result = resp.json()
            is_f = result.get('is_fraud')
            reason = result.get('reason')
            
            if is_f:
                fraud_count += 1
                results_summary[reason] = results_summary.get(reason, 0) + 1
                
        except Exception as e:
            print(f"Error on index {index}: {e}")
            
    rate = (fraud_count / total) * 100
    print(f"\nResults:")
    print(f"Total Transactions: {total}")
    print(f"Fraud Detected: {fraud_count}")
    print(f"Fraud Rate: {rate:.2f}%")
    print(f"Fraud Reasons: {results_summary}")
    
    if 3 <= rate <= 6:
        print("SUCCESS: Fraud rate is within target range (3-6%).")
    else:
        print(f"WARNING: Fraud rate is {rate:.2f}%. Target is 3-6%.")

if __name__ == "__main__":
    test_fraud_rate()
