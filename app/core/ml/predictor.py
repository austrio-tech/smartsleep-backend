import joblib
import os
from typing import Optional, Tuple
import numpy as np
from sklearn.linear_model import SGDRegressor, SGDClassifier

class MLPredictor:
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.regressor: Optional[SGDRegressor] = None
        self.classifier: Optional[SGDClassifier] = None

    def load_user_models(self, user_id: str):
        # In a real app, this would download from Cloudflare R2
        reg_path = os.path.join(self.model_dir, f"{user_id}_reg.joblib")
        clf_path = os.path.join(self.model_dir, f"{user_id}_clf.joblib")
        
        if os.path.exists(reg_path):
            self.regressor = joblib.load(reg_path)
        if os.path.exists(clf_path):
            self.classifier = joblib.load(clf_path)

    def predict(self, features: np.ndarray) -> Tuple[Optional[float], Optional[str]]:
        reg_score = None
        clf_label = None
        
        if self.regressor:
            reg_score = float(self.regressor.predict(features)[0])
        
        if self.classifier:
            clf_label = str(self.classifier.predict(features)[0])
            
        return reg_score, clf_label

predictor = MLPredictor()
