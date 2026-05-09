import joblib
import os
from typing import Optional, Tuple, List
import numpy as np
from sklearn.linear_model import SGDRegressor, SGDClassifier

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "models")
CLASSES = np.array(["Poor", "Fair", "Good", "Excellent"])


class MLPredictor:
    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)

    def _paths(self, user_id: str):
        return (
            os.path.join(MODEL_DIR, f"{user_id}_reg.joblib"),
            os.path.join(MODEL_DIR, f"{user_id}_clf.joblib"),
        )

    def _load(self, user_id: str):
        reg_path, clf_path = self._paths(user_id)
        regressor  = joblib.load(reg_path)  if os.path.exists(reg_path)  else None
        classifier = joblib.load(clf_path) if os.path.exists(clf_path) else None
        return regressor, classifier

    def predict(self, user_id: str, fv: List[float]) -> Tuple[Optional[float], Optional[str]]:
        """Step 9: inference from personal model. Returns (ml_score, user_class) or (None, None)."""
        regressor, classifier = self._load(user_id)
        if not regressor and not classifier:
            return None, None
        X = np.array(fv).reshape(1, -1)
        ml_score   = float(regressor.predict(X)[0])  if regressor  else None
        user_class = str(classifier.predict(X)[0])   if classifier else None
        return ml_score, user_class

    def partial_fit(self, user_id: str, fv: List[float], user_score: float, user_class: str):
        """Step 14: online learning — one incremental update per feedback."""
        regressor, classifier = self._load(user_id)
        reg_path, clf_path = self._paths(user_id)

        X      = np.array(fv).reshape(1, -1)
        y_reg  = np.array([user_score])
        y_clf  = np.array([user_class])

        if regressor is None:
            regressor = SGDRegressor(max_iter=1000, tol=1e-3, warm_start=True)
        if classifier is None:
            classifier = SGDClassifier(loss="modified_huber", max_iter=1000, tol=1e-3)

        regressor.partial_fit(X, y_reg)
        classifier.partial_fit(X, y_clf, classes=CLASSES)

        joblib.dump(regressor, reg_path)
        joblib.dump(classifier, clf_path)


predictor = MLPredictor()
