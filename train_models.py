import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
import os
import joblib

try:
    # We don't have xgboost by default in all envs, we'll try to import and use fallback if needed
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("XGBoost not installed. Will use a second RandomForest as a placeholder.")

class BehaviorProfiler:
    def __init__(self):
        self.means = None
        self.stds = None
        
    def fit(self, X):
        self.means = np.mean(X, axis=0)
        self.stds = np.std(X, axis=0)
        # Avoid division by zero
        self.stds[self.stds == 0] = 1e-6
        return self
        
    def compute_score(self, sample):
        # Calculate continuous anomaly score based on mean and std
        z_scores = np.abs((sample - self.means) / self.stds)
        return np.mean(z_scores) / 10.0

def main():
    print("Starting Model Training...")
    
    # 1. Load dataset (creditcard.csv)
    if os.path.exists('creditcard.csv'):
        print("Loading creditcard.csv...")
        df = pd.read_csv('creditcard.csv')
        X = df.drop(['Class', 'Time'], axis=1, errors='ignore').values
        y = df['Class'].values
    else:
        print("creditcard.csv not found. Generating synthetic dataset...")
        # 30 features, similar to credit card dataset
        X, y = make_classification(n_samples=5000, n_features=30, n_informative=20, 
                                   n_redundant=2, weights=[0.98, 0.02], random_state=42)
        
    print(f"Dataset shape: {X.shape}")

    # 2. Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 3. Scale data
    print("Scaling data...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    # X_test_scaled = scaler.transform(X_test)
    
    # 4. Train models
    print("Training RandomForestClassifier...")
    rf_model = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
    rf_model.fit(X_train_scaled, y_train)
    
    if HAS_XGB:
        print("Training XGBoostClassifier...")
        xgb_model = XGBClassifier(n_estimators=50, max_depth=6, random_state=42, eval_metric='logloss')
        xgb_model.fit(X_train_scaled, y_train)
    else:
        print("XGBoost not available. Training fallback model...")
        xgb_model = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=123)
        xgb_model.fit(X_train_scaled, y_train)
        
    # 5. Create BehaviorProfiler (Trained on UNSCALED data as requested)
    print("Training BehaviorProfiler on unscaled data...")
    profiler = BehaviorProfiler()
    profiler.fit(X_train) 
    
    # 6. Save models
    print("Saving models to .pkl files...")
    joblib.dump(rf_model, 'rf_model.pkl')
    joblib.dump(xgb_model, 'xgb_model.pkl')
    joblib.dump(scaler, 'scaler.pkl')
    joblib.dump(profiler, 'behavior_profiler.pkl')
    
    print("Model training complete! All .pkl files have been generated.")

if __name__ == "__main__":
    main()
