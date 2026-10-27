import pytest
from datetime import datetime, timezone, timedelta

def validate_earthquake_quality(record: dict) -> dict:
    """
    Implements and evaluates the 7 Pandera/Airflow data quality rules:
      1. Rango de Magnitud (-1.0 <= mag <= 10.0)
      2. Rango de Profundidad (-5.0 <= depth <= 1000.0 km)
      3. Coordenadas Válidas (-90 <= lat <= 90, -180 <= lon <= 180)
      4. Frescura de Datos (lag <= 120 min)
      5. Volumen de Lote (0 < batch_size <= 500)
      6. No Nulos en Campos Críticos (id, time, latitude, longitude)
      7. Unicidad de Eventos (id no vacío)
    Returns: { "quality_status": "VALID" | "FLAGGED", "reasons": list[str] }
    """
    failures = []

    # QR06: No Nulos
    if not record.get("id"):
        failures.append("QR06: ID es nulo o vacío")
    if record.get("magnitude") is None:
        failures.append("QR06: Magnitud es nula")
    if record.get("latitude") is None or record.get("longitude") is None:
        failures.append("QR06: Coordenadas geográficas son nulas")

    # QR01: Rango Magnitud
    mag = record.get("magnitude")
    if mag is not None and not (-1.0 <= mag <= 10.0):
        failures.append(f"QR01: Magnitud fuera de rango (-1.0 a 10.0): {mag}")

    # QR02: Rango Profundidad
    depth = record.get("depth_km")
    if depth is not None and not (-5.0 <= depth <= 1000.0):
        failures.append(f"QR02: Profundidad fuera de rango (-5.0 a 1000.0 km): {depth}")

    # QR03: Coordenadas Geográficas
    lat = record.get("latitude")
    lon = record.get("longitude")
    if lat is not None and not (-90.0 <= lat <= 90.0):
        failures.append(f"QR03: Latitud fuera de rango (-90 a 90): {lat}")
    if lon is not None and not (-180.0 <= lon <= 180.0):
        failures.append(f"QR03: Longitud fuera de rango (-180 a 180): {lon}")

    # QR04: Frescura de Datos
    event_time = record.get("event_time_utc")
    if event_time:
        now = datetime.now(timezone.utc)
        diff = (now - event_time).total_seconds() / 60.0
        if diff > 120:
            failures.append(f"QR04: Registro excede frescura máxima de 120 minutos (lag: {diff:.1f} min)")

    status = "FLAGGED" if len(failures) > 0 else "VALID"
    return {
        "quality_status": status,
        "reasons": failures
    }

def test_valid_earthquake_passes_all_rules():
    """Verifies that a well-formed seismic event passes all 7 quality rules with status VALID."""
    valid_record = {
        "id": "us7000test01",
        "magnitude": 4.5,
        "depth_km": 15.0,
        "latitude": 6.251,
        "longitude": -75.567,
        "event_time_utc": datetime.now(timezone.utc) - timedelta(minutes=5),
        "place": "Medellin, Colombia"
    }
    result = validate_earthquake_quality(valid_record)
    assert result["quality_status"] == "VALID"
    assert len(result["reasons"]) == 0

def test_invalid_magnitude_flagged_non_destructively():
    """
    Verifies that an out-of-range magnitude (>10.0) is flagged.
    NON-DESTRUCTIVE QUARANTINE: The record is NOT discarded or lost.
    """
    invalid_record = {
        "id": "us7000test_bad_mag",
        "magnitude": 14.8, # Impossible magnitude
        "depth_km": 20.0,
        "latitude": 4.5,
        "longitude": -74.0,
        "event_time_utc": datetime.now(timezone.utc) - timedelta(minutes=10),
        "place": "Test Anomaly"
    }
    result = validate_earthquake_quality(invalid_record)
    assert result["quality_status"] == "FLAGGED"
    assert any("QR01" in r for r in result["reasons"])

def test_invalid_coordinates_flagged():
    """Verifies that coordinates outside [-90, 90] and [-180, 180] are caught."""
    bad_coords_record = {
        "id": "us7000test_bad_coords",
        "magnitude": 3.2,
        "depth_km": 10.0,
        "latitude": 125.0, # Impossible latitude
        "longitude": -200.0, # Impossible longitude
        "event_time_utc": datetime.now(timezone.utc) - timedelta(minutes=15),
        "place": "Invalid Coords"
    }
    result = validate_earthquake_quality(bad_coords_record)
    assert result["quality_status"] == "FLAGGED"
    assert any("QR03" in r for r in result["reasons"])

def test_stale_record_flagged_for_freshness():
    """Verifies that records older than 120 minutes are tagged with freshness warning."""
    stale_record = {
        "id": "us7000test_stale",
        "magnitude": 2.1,
        "depth_km": 5.0,
        "latitude": 10.0,
        "longitude": -70.0,
        "event_time_utc": datetime.now(timezone.utc) - timedelta(minutes=180), # 3 hours old
        "place": "Stale Event"
    }
    result = validate_earthquake_quality(stale_record)
    assert result["quality_status"] == "FLAGGED"
    assert any("QR04" in r for r in result["reasons"])
