from types import SimpleNamespace
import uuid
from app.db.supabase_client import exec
from app.core.feature_engineering import compute_features
from app.core.rule_analyzer import calculate_base_score, calculate_penalties
from app.core.scoring import blend_scores
from app.core.statistics import update_stats
from app.core.ml.predictor import predictor


def process_daily_sleep(db, raw_id: str, user):
    rows = exec(db.table("raw_sleep_data").select("*").eq("raw_id", raw_id))
    if not rows:
        return None

    raw_dict = rows[0]
    raw_data = SimpleNamespace(**raw_dict)

    # 1. Feature engineering
    features = compute_features(raw_data)

    # 2. Rule-based scoring
    base_score = calculate_base_score(features)
    penalty = calculate_penalties(raw_data)

    # 3. ML prediction
    predictor.load_user_models(user.user_id)
    ml_score, user_class = predictor.predict([[
        features["sleep_eff"],
        features["interrupt_index"],
        features["caff_gap_hours"],
        features["screen_impact"],
    ]])

    # 4. Score blending
    final_score_raw = base_score - penalty
    if ml_score is not None:
        final_score_raw = blend_scores(final_score_raw, ml_score, 0.0)
    final_score = int(round(max(0, min(100, final_score_raw))))

    # 5. Persist derived record
    derived_id = str(uuid.uuid4())
    exec(db.table("derived_sleep_data").insert({
        "derived_id": derived_id,
        "user_id": user.user_id,
        "raw_id": raw_id,
        "date": raw_dict["record_date"],
        **features,
        "penalty": penalty,
        "base_score": base_score,
        "ml_score": ml_score,
        "final_score_raw": final_score_raw,
        "final_score": final_score,
        "user_class": user_class,
    }))

    # 6. Update Welford stats
    stat_rows = exec(db.table("user_stat").select("*").eq("user_id", user.user_id))
    stats = stat_rows[0] if stat_rows else {"mean_hr_rest": 0.0, "std_hr_rest": 0.0, "sample_count": 0}

    if raw_dict.get("hr_rest"):
        new_mean, new_std, new_count = update_stats(
            stats["mean_hr_rest"], stats["std_hr_rest"], stats["sample_count"], raw_dict["hr_rest"]
        )
        exec(db.table("user_stat").upsert({
            "user_id": user.user_id,
            "mean_hr_rest": new_mean,
            "std_hr_rest": new_std,
            "sample_count": new_count,
        }))
