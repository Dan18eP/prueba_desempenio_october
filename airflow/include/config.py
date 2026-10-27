import os
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3
from botocore.client import Config

# USGS Endpoints
USGS_REALTIME_FEED_URL = os.getenv(
    "USGS_REALTIME_FEED_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
)
USGS_HISTORICAL_QUERY_URL = os.getenv(
    "USGS_HISTORICAL_QUERY_URL",
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
)

# PostgreSQL Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DB = os.getenv("POSTGRES_DB", "sismowatch")

# Role specific credentials
SISMO_INGEST_USER = os.getenv("SISMO_INGEST_USER", "sismo_ingest")
SISMO_INGEST_PASSWORD = os.getenv("SISMO_INGEST_PASSWORD", "ingest_secret_pass_2026")

SISMO_TRANSFORM_USER = os.getenv("SISMO_TRANSFORM_USER", "sismo_transform")
SISMO_TRANSFORM_PASSWORD = os.getenv("SISMO_TRANSFORM_PASSWORD", "transform_secret_pass_2026")

# MinIO / S3 Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "sismowatch-lake")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "sismowatch_admin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "sismowatch_secret_minio_2026")

def get_db_connection(role: str = "transform"):
    """Returns a psycopg2 connection with least-privilege credentials based on role."""
    if role == "ingest":
        user = SISMO_INGEST_USER
        password = SISMO_INGEST_PASSWORD
    else:
        user = SISMO_TRANSFORM_USER
        password = SISMO_TRANSFORM_PASSWORD

    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=user,
        password=password,
        cursor_factory=RealDictCursor
    )

def get_s3_client():
    """Returns an authenticated boto3 S3 client configured for MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1"
    )
