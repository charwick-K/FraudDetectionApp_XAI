
import pandas as pd
import requests
import json

def verify():
    df = pd.read_csv('creditcard.csv', nrows=200)
    fraud_count = 0
    total = 0
    
    for index, row in df.iterrows():
        # Prepare features: Time + V1-V28
        features = row.iloc[:29].tolist()
        amount = float(row['Amount'])
        
        payload = {
            "features": features,
            "amount": amount
        }
        
        try:
            resp = requests.post("http://127.0.0.1:8000/predict", json=payload)
            if resp.status_code == 200:
                result = resp.json()
                if result.get('is_fraud'):
                    fraud_count += 1
                total += 1
        except Exception as e:
            print(f"Error: {e}")
            break
            
    if total > 0:
        rate = (fraud_count / total) * 100
        print(f"Total: {total}, Fraud: {fraud_count}, Rate: {rate:.2f}%")
    else:
        print("No data processed.")

if __name__ == "__main__":
    verify()
