import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.core.database import SessionLocalReadOnly

router = APIRouter(prefix="/api", tags=["Real-Time SSE Stream"])

def json_serial(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

async def event_generator(request: Request):
    """
    Asynchronous generator streaming real-time earthquake telemetry.
    Sends:
      1. 'connected' greeting with timestamp.
      2. 'initial_batch' of the latest 10 seismic events.
      3. Periodic 'earthquake_update' events as new records arrive.
      4. Heartbeat keepalive comments every 5 seconds to prevent browser disconnection.
    """
    # Send connection established event
    yield f"event: connected\ndata: {json.dumps({'message': 'SismoWatch Real-Time Stream Connected', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

    last_poll_time = datetime.now(timezone.utc)

    # Step 1: Send initial snapshot
    try:
        with SessionLocalReadOnly() as db:
            query = text("""
                SELECT 
                    id, magnitude, place, event_time_utc, longitude, latitude, depth_km,
                    tsunami_alert, severity_label, is_anomaly, anomaly_explanation, quality_status, updated_at
                FROM curated.gold_earthquakes
                ORDER BY event_time_utc DESC
                LIMIT 50
            """)
            initial_rows = db.execute(query).mappings().fetchall()
            events = [dict(r) for r in initial_rows]
            if events:
                # Set last poll to the latest updated_at or current time
                max_updated = max([r["updated_at"] for r in initial_rows if r.get("updated_at")] or [last_poll_time])
                last_poll_time = max_updated
            yield f"event: initial_batch\ndata: {json.dumps(events, default=json_serial)}\n\n"
    except Exception as e:
        yield f": error fetching initial batch: {str(e)}\n\n"

    # Step 2: Continuous loop checking for new or updated events
    while True:
        # Check if client disconnected
        if await request.is_disconnected():
            break

        try:
            with SessionLocalReadOnly() as db:
                query = text("""
                    SELECT 
                        id, magnitude, place, event_time_utc, longitude, latitude, depth_km,
                        tsunami_alert, severity_label, is_anomaly, anomaly_explanation, quality_status, updated_at
                    FROM curated.gold_earthquakes
                    WHERE updated_at > :last_poll
                    ORDER BY updated_at ASC
                    LIMIT 50
                """)
                new_rows = db.execute(query, {"last_poll": last_poll_time}).mappings().fetchall()

                if new_rows:
                    for r in new_rows:
                        payload = dict(r)
                        if payload.get("updated_at") and payload["updated_at"] > last_poll_time:
                            last_poll_time = payload["updated_at"]
                        yield f"event: earthquake_update\ndata: {json.dumps(payload, default=json_serial)}\n\n"
                else:
                    # Keep-alive heartbeat
                    yield f": keepalive {datetime.now(timezone.utc).isoformat()}\n\n"
        except Exception:
            yield f": keepalive\n\n"

        await asyncio.sleep(4)

@router.get("/stream")
async def sse_stream(request: Request, token: Optional[str] = Query(None)):
    """
    Server-Sent Events (SSE) live feed endpoint.
    Consumers (React EventSource) receive real-time updates as PySpark & Airflow ingest new data.
    """
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )
