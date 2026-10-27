import pytest
from datetime import datetime, timezone

def calculate_severity_label(mag: float) -> str:
    """Business logic function under test (Richter Severity scale)."""
    if mag < 3.0:
        return "Micro"
    elif mag < 5.0:
        return "Menor"
    elif mag < 6.8:
        return "Moderado"
    elif mag < 8.0:
        return "Fuerte"
    else:
        return "Mayor"

def evaluate_tsunami_risk(mag: float, depth_km: float, original_flag: int = 0) -> bool:
    """Tsunami evaluation matrix: M >= 6.8 AND depth <= 100 km OR original flag = 1."""
    if original_flag == 1:
        return True
    return mag >= 6.8 and depth_km <= 100.0

def transform_geojson_feature_to_silver(feature: dict) -> dict:
    """GeoJSON transformation function converting raw feature to Silver refined record."""
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [0.0, 0.0, 0.0])

    mag = float(props.get("mag") or 0.0)
    lon = float(coords[0]) if len(coords) > 0 else 0.0
    lat = float(coords[1]) if len(coords) > 1 else 0.0
    depth = float(coords[2]) if len(coords) > 2 else 0.0

    time_ms = props.get("time", 0)
    event_time_utc = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)

    tsunami_alert = evaluate_tsunami_risk(mag, depth, props.get("tsunami", 0))
    severity_label = calculate_severity_label(mag)

    return {
        "id": feature.get("id"),
        "magnitude": mag,
        "place": props.get("place", "Unknown"),
        "event_time_utc": event_time_utc,
        "longitude": lon,
        "latitude": lat,
        "depth_km": depth,
        "tsunami_alert": tsunami_alert,
        "severity_label": severity_label,
        "quality_status": "VALID"
    }

def test_richter_severity_classification():
    """Verifies that all Richter thresholds are mapped correctly."""
    assert calculate_severity_label(1.2) == "Micro"
    assert calculate_severity_label(2.9) == "Micro"
    assert calculate_severity_label(3.0) == "Menor"
    assert calculate_severity_label(4.9) == "Menor"
    assert calculate_severity_label(5.0) == "Moderado"
    assert calculate_severity_label(6.7) == "Moderado"
    assert calculate_severity_label(6.8) == "Fuerte"
    assert calculate_severity_label(7.9) == "Fuerte"
    assert calculate_severity_label(8.0) == "Mayor"
    assert calculate_severity_label(9.2) == "Mayor"

def test_tsunami_matrix_conditions():
    """Verifies the tsunami risk trigger matrix: M >= 6.8 AND depth <= 100km."""
    # Critical shallow earthquake -> Tsunami Alert Triggered
    assert evaluate_tsunami_risk(7.2, 18.0) is True
    # Deep earthquake (depth > 100km) -> No Tsunami Alert
    assert evaluate_tsunami_risk(7.2, 250.0) is False
    # Low magnitude (< 6.8) -> No Tsunami Alert
    assert evaluate_tsunami_risk(5.5, 10.0) is False
    # USGS pre-flagged event -> Tsunami Alert Triggered
    assert evaluate_tsunami_risk(5.0, 50.0, original_flag=1) is True

def test_twenty_in_twenty_out_invariant(sample_geojson):
    """
    CRITICAL INVARIANT TEST: 'Me llegaron 20, mostré 20'.
    Verifies that for 20 ingested features, exactly 20 Silver rows are output.
    Zero records dropped, zero unmapped rows.
    """
    raw_features = sample_geojson.get("features", [])
    assert len(raw_features) == 20

    silver_records = [transform_geojson_feature_to_silver(f) for f in raw_features]
    assert len(silver_records) == 20

    # Ensure all IDs are preserved
    input_ids = {f["id"] for f in raw_features}
    output_ids = {r["id"] for r in silver_records}
    assert input_ids == output_ids

    # Fidelity rate is mathematically 100.0%
    fidelity_rate = (len(silver_records) / len(raw_features)) * 100.0
    assert fidelity_rate == 100.0
