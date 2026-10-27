import math
import statistics
from datetime import datetime, timezone
from collections import defaultdict

def classify_severity(magnitude: float) -> str:
    """Classifies seismic event into standard Richter severity scale."""
    if magnitude is None:
        return "Desconocido"
    mag = float(magnitude)
    if mag < 2.5:
        return "Micro"
    elif mag < 4.5:
        return "Menor"
    elif mag < 6.0:
        return "Moderado"
    elif mag < 7.0:
        return "Fuerte"
    else:
        return "Mayor"

def detect_seismic_anomalies(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Computes statistical Z-Score and detects seismic swarms.
    Returns (enriched_records, detected_anomalies).
    """
    if not records:
        return [], []
    
    # 1. Extract valid magnitudes
    magnitudes = [float(r["magnitude"]) for r in records if r.get("magnitude") is not None]
    if len(magnitudes) >= 2:
        mean_mag = statistics.mean(magnitudes)
        stdev_mag = statistics.stdev(magnitudes)
        if stdev_mag == 0:
            stdev_mag = 0.5
    else:
        mean_mag = magnitudes[0] if magnitudes else 2.5
        stdev_mag = 1.0

    # 2. Hourly event frequency for swarms
    hour_counts = defaultdict(int)
    for r in records:
        t = r.get("event_time_utc")
        if t:
            if isinstance(t, str):
                t = datetime.fromisoformat(t.replace("Z", "+00:00"))
            hour_key = t.strftime("%Y-%m-%d %H:00")
            hour_counts[hour_key] += 1
            
    # Swarm threshold: > 10 events in a single hour
    swarm_hours = {h for h, c in hour_counts.items() if c >= 10}

    enriched_records = []
    anomalies = []

    for r in records:
        rec = dict(r)
        mag = float(rec["magnitude"]) if rec.get("magnitude") is not None else 0.0
        
        # Calculate Z-score
        z_score = round((mag - mean_mag) / stdev_mag, 2)
        
        # Check swarm membership
        t = rec.get("event_time_utc")
        if isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00"))
        hour_key = t.strftime("%Y-%m-%d %H:00") if t else ""
        is_swarm = hour_key in swarm_hours
        
        # Anomaly condition: Z > 2.5 OR (swarm and mag >= 4.0)
        is_anomaly = bool(z_score > 2.5 or (is_swarm and mag >= 4.0))
        
        explanation = None
        if is_anomaly:
            if is_swarm:
                explanation = f"Enjambre sísmico detectado: {hour_counts[hour_key]} eventos en ventana horaria con magnitud {mag}."
            else:
                explanation = f"Sismo de magnitud {mag} supera en {z_score} desviaciones estándar el promedio regional (mu={round(mean_mag, 2)})."
            
            anomalies.append({
                "earthquake_id": rec["id"],
                "magnitude": mag,
                "place": rec["place"],
                "z_score": z_score,
                "is_swarm": is_swarm,
                "anomaly_explanation": explanation,
                "detected_at": datetime.now(timezone.utc)
            })

        rec["severity_label"] = classify_severity(mag)
        rec["is_anomaly"] = is_anomaly
        rec["anomaly_explanation"] = explanation
        enriched_records.append(rec)

    return enriched_records, anomalies
