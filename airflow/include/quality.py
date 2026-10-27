from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger("airflow.include.quality")

def evaluate_data_quality(records: list[dict], batch_id: str) -> tuple[list[dict], dict]:
    """
    Evaluates 7 quality rules on incoming records without dropping any record (20 in -> 20 out).
    Flags invalid records as 'FLAGGED' with specific rejection reasons.
    Returns (enriched_records, quality_summary).
    """
    now_utc = datetime.now(timezone.utc)
    rules_evaluated = 0
    rules_passed = 0
    rules_failed = 0
    
    seen_ids = set()
    enriched_records = []
    
    # 1. Volume Check
    rules_evaluated += 1
    count = len(records)
    volume_ok = 0 < count <= 500
    if volume_ok:
        rules_passed += 1
    else:
        rules_failed += 1
        logger.warning(f"[QUALITY] Volume check alert: batch count = {count}")
    
    # 2. Freshness Check
    rules_evaluated += 1
    freshness_lag_minutes = 9999
    if records:
        try:
            latest_time = max(r.get("event_time_utc") for r in records if r.get("event_time_utc"))
            if isinstance(latest_time, str):
                # parse ISO or timestamp
                latest_time = datetime.fromisoformat(latest_time.replace("Z", "+00:00"))
            if latest_time.tzinfo is None:
                latest_time = latest_time.replace(tzinfo=timezone.utc)
            lag = (now_utc - latest_time).total_seconds() / 60.0
            freshness_lag_minutes = int(lag)
            if lag <= 120:
                rules_passed += 1
            else:
                rules_failed += 1
                logger.warning(f"[QUALITY] Stale feed alert: lag = {freshness_lag_minutes} min")
        except Exception as e:
            rules_failed += 1
            logger.warning(f"[QUALITY] Could not compute freshness: {e}")
    else:
        rules_failed += 1
    
    # Individual record rules (Rules 3 to 7)
    for r in records:
        record_flags = []
        rec_id = r.get("id")
        
        # Rule 3: Uniqueness
        rules_evaluated += 1
        if rec_id in seen_ids:
            record_flags.append(f"Duplicate ID in batch: {rec_id}")
            rules_failed += 1
        else:
            seen_ids.add(rec_id)
            rules_passed += 1
            
        # Rule 4: Mandatory Fields
        rules_evaluated += 1
        has_mandatory = bool(rec_id and r.get("place") and r.get("event_time_utc") is not None)
        if has_mandatory:
            rules_passed += 1
        else:
            record_flags.append("Missing mandatory fields (id, place, time)")
            rules_failed += 1
            
        # Rule 5: Coordinate Ranges
        rules_evaluated += 1
        lat = r.get("latitude")
        lon = r.get("longitude")
        if lat is not None and lon is not None and -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0:
            rules_passed += 1
        else:
            record_flags.append(f"Invalid coordinates: lat={lat}, lon={lon}")
            rules_failed += 1
            
        # Rule 6: Depth Plausibility
        rules_evaluated += 1
        depth = r.get("depth_km")
        if depth is not None and -5.0 <= float(depth) <= 800.0:
            rules_passed += 1
        else:
            record_flags.append(f"Implausible depth: {depth} km")
            rules_failed += 1
            
        # Rule 7: Magnitude Plausibility
        rules_evaluated += 1
        mag = r.get("magnitude")
        if mag is not None and -2.0 <= float(mag) <= 10.0:
            rules_passed += 1
        else:
            record_flags.append(f"Implausible magnitude: {mag}")
            rules_failed += 1
            
        # Enrich record with quality status without dropping it
        rec_copy = dict(r)
        if record_flags:
            rec_copy["quality_status"] = "FLAGGED"
            rec_copy["quality_reasons"] = "; ".join(record_flags)
        else:
            rec_copy["quality_status"] = "VALID"
            rec_copy["quality_reasons"] = None
            
        enriched_records.append(rec_copy)

    # Compute overall score
    quality_score = round((rules_passed / max(rules_evaluated, 1)) * 100.0, 2)
    overall_status = "PASSED" if quality_score >= 85.0 else "WARNING"
    
    summary = {
        "batch_id": batch_id,
        "rules_evaluated": rules_evaluated,
        "rules_passed": rules_passed,
        "rules_failed": rules_failed,
        "quality_score": quality_score,
        "freshness_lag_minutes": freshness_lag_minutes,
        "volume_count": count,
        "status": overall_status,
        "flagged_records_count": len([r for r in enriched_records if r["quality_status"] == "FLAGGED"])
    }
    
    return enriched_records, summary

def persist_quality_metrics(summary: dict):
    """Writes the batch quality summary to audit.quality_metrics."""
    from airflow.include.config import get_db_connection
    import json
    
    try:
        conn = get_db_connection(role="transform")
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit.quality_metrics (
                    batch_id, rules_evaluated, rules_passed, rules_failed,
                    quality_score, freshness_lag_minutes, volume_count, status, details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                summary["batch_id"],
                summary["rules_evaluated"],
                summary["rules_passed"],
                summary["rules_failed"],
                summary["quality_score"],
                summary["freshness_lag_minutes"],
                summary["volume_count"],
                summary["status"],
                json.dumps(summary)
            ))
            conn.commit()
        conn.close()
        logger.info(f"[QUALITY] Successfully saved quality metrics for batch {summary['batch_id']}: Score={summary['quality_score']}%")
    except Exception as e:
        logger.error(f"[QUALITY] Error persisting quality metrics: {e}")
