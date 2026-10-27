from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.core.database import get_readonly_db

router = APIRouter(prefix="/api/events", tags=["Earthquake Events"])

@router.get("")
def list_events(
    limit: int = Query(500, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    min_magnitude: Optional[float] = Query(None, ge=0.0, le=10.0),
    severity: Optional[str] = Query(None),
    tsunami_only: bool = Query(False),
    anomalies_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_readonly_db)
):
    """
    Returns paginated seismic events from curated.gold_earthquakes.
    Supports filtering by magnitude, severity, tsunami alert, anomalies, and location text search.
    """
    conditions = ["1=1"]
    params = {"limit": limit, "offset": offset}

    if min_magnitude is not None:
        conditions.append("magnitude >= :min_mag")
        params["min_mag"] = min_magnitude

    if severity:
        conditions.append("LOWER(severity_label) = LOWER(:sev)")
        params["sev"] = severity

    if tsunami_only:
        conditions.append("tsunami_alert = TRUE")

    if anomalies_only:
        conditions.append("is_anomaly = TRUE")

    if search:
        conditions.append("place ILIKE :search")
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(conditions)

    count_query = text(f"SELECT COUNT(*) FROM curated.gold_earthquakes WHERE {where_clause}")  # nosec B608
    total_count = db.execute(count_query, params).scalar() or 0

    # nosec B608
    data_query = text(f"""
        SELECT 
            id,
            magnitude,
            place,
            event_time_utc,
            updated_time_utc,
            longitude,
            latitude,
            depth_km,
            tsunami_alert,
            significance,
            review_status,
            severity_label,
            is_anomaly,
            anomaly_explanation,
            quality_status
        FROM curated.gold_earthquakes
        WHERE {where_clause}
        ORDER BY event_time_utc DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(data_query, params).mappings().fetchall()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "events": [dict(r) for r in rows]
    }

@router.get("/{event_id}")
def get_event_detail(event_id: str, db: Session = Depends(get_readonly_db)):
    """Returns detailed information for a specific earthquake event."""
    query = text("""
        SELECT 
            id,
            magnitude,
            place,
            event_time_utc,
            updated_time_utc,
            longitude,
            latitude,
            depth_km,
            tsunami_alert,
            significance,
            review_status,
            severity_label,
            is_anomaly,
            anomaly_explanation,
            quality_status,
            created_at
        FROM curated.gold_earthquakes
        WHERE id = :event_id
        LIMIT 1
    """)
    row = db.execute(query, {"event_id": event_id}).mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sismo con ID '{event_id}' no encontrado."
        )
    return dict(row)
