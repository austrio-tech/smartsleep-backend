from sqlalchemy.orm import Session
from app.models.raw_sleep_data import RawSleepData
from app.models.derived_sleep_data import DerivedSleepData
from app.models.user import User
from app.models.user_stat import UserStat
from app.core.feature_engineering import compute_features
from app.core.rule_analyzer import calculate_base_score, calculate_penalties
from app.core.scoring import blend_scores
from app.core.statistics import update_stats
from app.core.ml.predictor import predictor

def process_daily_sleep(db: Session, raw_id: str, user: User):
    raw_data = db.query(RawSleepData).filter(RawSleepData.raw_id == raw_id).first()
    if not raw_data:
        return None

    # 1. Feature Engineering
    features = compute_features(raw_data)
    
    # 2. Rule-based analysis
    base_score = calculate_base_score(features)
    penalty = calculate_penalties(raw_data)
    
    # 3. ML Prediction (Inference)
    predictor.load_user_models(user.user_id)
    # Simplified feature vector for prediction
    feature_vector = [features['sleep_eff'], features['interrupt_index'], features['caff_gap_hours'], features['screen_impact']]
    ml_score, user_class = predictor.predict([feature_vector])
    
    # 4. Scoring Blending
    # Get user learning factor (defaults to 0 for cold start)
    learning_factor = 0.0 # This would come from model_artifact table
    
    final_score_raw = base_score - penalty
    if ml_score is not None:
        final_score_raw = blend_scores(final_score_raw, ml_score, learning_factor)
    
    final_score = int(round(final_score_raw))
    
    # 5. Persistence
    db_derived = DerivedSleepData(
        user_id=user.user_id,
        raw_id=raw_id,
        date=raw_data.record_date,
        **features,
        penalty=penalty,
        base_score=base_score,
        ml_score=ml_score,
        final_score_raw=final_score_raw,
        final_score=final_score,
        user_class=user_class
    )
    db.add(db_derived)
    
    # 6. Update Stats (Welford's)
    stats = db.query(UserStat).filter(UserStat.user_id == user.user_id).first()
    if not stats:
        stats = UserStat(user_id=user.user_id)
        db.add(stats)
    
    if raw_data.hr_rest:
        stats.mean_hr_rest, stats.std_hr_rest, stats.sample_count = update_stats(
            stats.mean_hr_rest, stats.std_hr_rest, stats.sample_count, raw_data.hr_rest
        )
    
    db.commit()
    db.refresh(db_derived)
    return db_derived
