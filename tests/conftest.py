import os
import sys
import pytest
from datetime import timedelta
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "sismowatch_test_secret_key_super_secure_2026_at_least_32_chars"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from fastapi.testclient import TestClient
from api.main import app
from api.core.security import create_access_token

@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)

@pytest.fixture
def admin_token():
    """Generates a valid JWT token with role 'admin'."""
    return create_access_token(
        data={"sub": "admin", "role": "admin", "email": "admin@sismowatch.gov.co"},
        expires_delta=timedelta(minutes=30)
    )

@pytest.fixture
def viewer_token():
    """Generates a valid JWT token with role 'viewer'."""
    return create_access_token(
        data={"sub": "viewer", "role": "viewer", "email": "viewer@sismowatch.gov.co"},
        expires_delta=timedelta(minutes=30)
    )

@pytest.fixture
def sample_geojson():
    """Sample USGS GeoJSON payload with 20 features (simulating 100% fidelity invariant)."""
    features = []
    for i in range(20):
        features.append({
            "type": "Feature",
            "properties": {
                "mag": 2.5 + (i * 0.25),
                "place": f"Region Test #{i+1}, Colombia",
                "time": 1730000000000 + (i * 60000),
                "updated": 1730000050000 + (i * 60000),
                "tz": None,
                "url": f"https://earthquake.usgs.gov/earthquakes/eventpage/test{i+1}",
                "detail": f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/test{i+1}.geojson",
                "felt": None,
                "cdi": None,
                "mmi": None,
                "alert": None,
                "status": "reviewed",
                "tsunami": 1 if i == 19 else 0,
                "sig": 100 + i * 10,
                "net": "us",
                "code": f"test{i+1}",
                "ids": f",test{i+1},",
                "sources": ",us,",
                "types": ",origin,phase-data,",
                "nst": 20,
                "dmin": 0.5,
                "rms": 0.45,
                "gap": 45,
                "magType": "ml",
                "type": "earthquake",
                "title": f"M {2.5 + i*0.25} - Region Test #{i+1}, Colombia"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-75.567 + (i * 0.1), 6.251 + (i * 0.1), 15.0 + (i * 2.0)]
            },
            "id": f"us7000test{i+1:02d}"
        })
    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": 1730000500000,
            "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
            "title": "USGS Earthquakes Test Feed",
            "status": 200,
            "api": "1.10.3",
            "count": 20
        },
        "features": features
    }
