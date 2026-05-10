from types import SimpleNamespace
from datetime import date as date_cls, timedelta, datetime
import uuid

from app.db.supabase_client import exec
from app.core.feature_engineering import compute_features, feature_vector
from app.core.rule_analyzer import calculate_base_score, calculate_penalties
from app.core.scoring import blend_scores
from app.core.statistics import update_stats
from app.core.ml.predictor import predictor


def _classify(score_0_100: float) -> str:
    if score_0_100 >= 85:
        return "Excellent"
    if score_0_100 >= 70:
        return "Good"
    if score_0_100 >= 50:
        return "Fair"
    return "Poor"


def _get_model_artifact(db, user_id: str) -> dict:
    rows = exec(db.table("model_artifact").select("*").eq("user_id", user_id))
    return rows[0] if rows else {"training_samples": 0, "current_learning_factor": 0.0}


def process_daily_sleep(db, raw_id: str, user):
    # ── 1. Fetch raw record ───────────────────────────────────────────────────
    rows = exec(db.table("raw_sleep_data").select("*").eq("raw_id", raw_id))
    if not rows:
        return None
    raw_dict = rows[0]
    raw_data = SimpleNamespace(**raw_dict)

    # ── 2. Context data for features ─────────────────────────────────────────
    stat_rows = exec(db.table("user_stat").select("*").eq("user_id", user.user_id))
    user_stat = stat_rows[0] if stat_rows else None

    seven_ago = (date_cls.today() - timedelta(days=7)).isoformat()
    hist_rows = exec(
        db.table("raw_sleep_data")
        .select("sleep_time")
        .eq("user_id", user.user_id)
        .gte("record_date", seven_ago)
    )
    last_7_sleep_times = [r["sleep_time"] for r in hist_rows if r.get("sleep_time")]

    # ── 3. Feature engineering (Steps 2-7) ───────────────────────────────────
    features = compute_features(raw_data, user_stat=user_stat, last_7_sleep_times=last_7_sleep_times)
    fv = feature_vector(features)

    # ── 4. Base score 0-1 (Step 10) ──────────────────────────────────────────
    base_score = calculate_base_score(features)

    # ── 5. Penalties (Step 8) ─────────────────────────────────────────────────
    penalty = calculate_penalties(raw_data, features)

    # ── 6. Learning factor (Step 16) ─────────────────────────────────────────
    artifact = _get_model_artifact(db, user.user_id)
    n = artifact.get("training_samples", 0)
    learning_factor = min(1.0, n / 60) if n >= 14 else 0.0

    # ── 7. ML prediction (Steps 9 / 13 cold-start) ───────────────────────────
    ml_score, user_class = None, None
    if n >= 14:
        ml_score, user_class = predictor.predict(user.user_id, fv)

    # Cold start: ml_score = rule-based score (Step 13)
    if ml_score is None:
        ml_score = base_score * 100
    if user_class is None:
        user_class = _classify(base_score * 100)

    # ── 8. Final score (Step 16) ──────────────────────────────────────────────
    final_score_raw = blend_scores(base_score, ml_score, learning_factor) - penalty
    final_score = int(round(max(0, min(100, final_score_raw))))

    # ── 9. Persist derived record (upsert by raw_id) ─────────────────────────
    derived_payload = {
        "user_id":         user.user_id,
        "raw_id":          raw_id,
        "date":            raw_dict["record_date"],
        # Step 2
        "tib":             features["tib"],
        "tst":             features["tst"],
        "sleep_eff":       features["sleep_eff"],
        "interrupt_index": features["interrupt_index"],
        "consistency_7d":  features["consistency_7d"],
        # Step 3
        "caff_gap_hours":  features["caff_gap_hours"],
        "caff_impact":     features["caff_impact"],
        "screen_impact":   features["screen_impact"],
        "act_gap_hours":   features["act_gap_hours"],
        # Steps 4-6
        "bio_ready":       features["bio_ready"],
        "psych_load":      features["psych_load"],
        "env_score":       features["env_score"],
        # Scoring
        "penalty":         penalty,
        "base_score":      base_score,
        "ml_score":        ml_score,
        "final_score_raw": final_score_raw,
        "final_score":     final_score,
        "user_class":      user_class,
    }

    existing_derived = exec(
        db.table("derived_sleep_data").select("derived_id").eq("raw_id", raw_id)
    )
    if existing_derived:
        derived_id = existing_derived[0]["derived_id"]
        exec(
            db.table("derived_sleep_data")
            .update(derived_payload)
            .eq("derived_id", derived_id)
        )
    else:
        derived_id = str(uuid.uuid4())
        exec(db.table("derived_sleep_data").insert({"derived_id": derived_id, **derived_payload}))

    # ── 10. Update Welford stats (Step 4) ─────────────────────────────────────
    stats = user_stat or {
        "mean_hr_rest": 0.0, "std_hr_rest": 0.0,
        "mean_hrv": 0.0,     "std_hrv": 0.0,
        "mean_body_temp": 0.0, "std_body_temp": 0.0,
        "sample_count": 0,
    }
    current_n = stats.get("sample_count", 0)
    new_stat = {"user_id": user.user_id}

    if raw_dict.get("hr_rest"):
        m, s, current_n = update_stats(stats["mean_hr_rest"], stats["std_hr_rest"], current_n, raw_dict["hr_rest"])
        new_stat.update({"mean_hr_rest": m, "std_hr_rest": s})

    if raw_dict.get("hrv"):
        m, s, _ = update_stats(stats.get("mean_hrv", 0.0), stats.get("std_hrv", 0.0), current_n, raw_dict["hrv"])
        new_stat.update({"mean_hrv": m, "std_hrv": s})

    if raw_dict.get("body_temp"):
        m, s, _ = update_stats(stats.get("mean_body_temp", 0.0), stats.get("std_body_temp", 0.0), current_n, raw_dict["body_temp"])
        new_stat.update({"mean_body_temp": m, "std_body_temp": s})

    new_stat["sample_count"] = current_n
    exec(db.table("user_stat").upsert(new_stat))

    # ── 11. Send sleep report email (fire-and-forget) ─────────────────────────
    try:
        from app.services.email_service import send_email, render_template

        def _fmt(h):
            if not h:
                return "N/A"
            hh, mm = int(h), int((h - int(h)) * 60)
            return f"{hh}h {mm}m"

        score_bg = (
            "linear-gradient(135deg,#16A34A,#15803D)" if final_score >= 85
            else "linear-gradient(135deg,#2563EB,#1D4ED8)" if final_score >= 70
            else "linear-gradient(135deg,#F59E0B,#D97706)" if final_score >= 50
            else "linear-gradient(135deg,#EF4444,#DC2626)"
        )
        display_name = getattr(user, "full_name", None) or user.email.split("@")[0]
        html = render_template(
            "sleep_report.html",
            NAME=display_name,
            EMAIL=user.email,
            SCORE=final_score,
            CLASSIFICATION=user_class,
            SCORE_BG=score_bg,
            REPORT_DATE=raw_dict.get("record_date", "Today"),
            DURATION=_fmt(features.get("tst")),
            EFFICIENCY=f"{int((features.get('sleep_eff') or 0) * 100)}%",
            CONSISTENCY=f"{int((features.get('consistency_7d') or 0) * 100)}%",
            BIO_READY=f"{int((features.get('bio_ready') or 0) * 100)}%",
        )
        send_email(user.email, f"\U0001f319 SmartSleep Report — Score: {final_score}", html)
    except Exception as _exc:
        import logging
        logging.getLogger(__name__).warning("Sleep report email failed: %s", _exc)


def trigger_training(db, derived_id: str, user_id: str, user_score: float, user_class: str):
    """
    Steps 11-14: called after user submits feedback.
    1. Retrieve feature vector from derived record.
    2. Store labeled sample in training_data.
    3. If n >= 14, run partial_fit.
    4. Update model_artifact.
    """
    # Get derived record features
    rows = exec(db.table("derived_sleep_data").select("*").eq("derived_id", derived_id))
    if not rows:
        return
    d = rows[0]

    fv = [
        d.get("tst") or 0.0,
        d.get("sleep_eff") or 0.0,
        d.get("interrupt_index") or 0.0,
        d.get("consistency_7d") or 1.0,
        d.get("caff_impact") or 0.1,
        d.get("screen_impact") or 0.0,
        d.get("act_gap_hours") or 0.0,
        d.get("bio_ready") or 0.5,
        d.get("psych_load") or 0.5,
        d.get("env_score") or 0.5,
    ]

    # Store labeled sample
    exec(db.table("training_data").insert({
        "id":          str(uuid.uuid4()),
        "user_id":     user_id,
        "derived_id":  derived_id,
        "date":        d["date"],
        "features":    {str(i): v for i, v in enumerate(fv)},
        "user_score":  user_score,
        "user_class":  user_class,
    }))

    # Count total labeled samples for this user
    all_samples = exec(db.table("training_data").select("id").eq("user_id", user_id))
    n = len(all_samples)

    # Online learning once cold start is over (Step 14)
    if n >= 14:
        predictor.partial_fit(user_id, fv, user_score, user_class)

    # Update model_artifact
    learning_factor = round(min(1.0, n / 60), 4)
    artifact_rows = exec(db.table("model_artifact").select("model_id").eq("user_id", user_id))

    now = datetime.utcnow().isoformat()
    if artifact_rows:
        exec(
            db.table("model_artifact")
            .update({
                "training_samples": n,
                "current_learning_factor": learning_factor,
                "last_trained": now,
            })
            .eq("user_id", user_id)
        )
    else:
        exec(db.table("model_artifact").insert({
            "model_id":               str(uuid.uuid4()),
            "user_id":                user_id,
            "training_samples":       n,
            "current_learning_factor": learning_factor,
            "last_trained":           now,
        }))
