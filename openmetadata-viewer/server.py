import http.server
import json
import socketserver
import os

PORT = int(os.getenv("OPENMETADATA_PORT", 8585))

LINEAGE_METADATA = {
    "entity": {
        "id": "sismowatch-lakehouse",
        "type": "databaseService",
        "name": "sismowatch_governance",
        "fullyQualifiedName": "sismowatch_governance",
        "description": "SismoWatch Pure Medallion Data Lakehouse & Governance Catalog"
    },
    "nodes": [
        {
            "id": "src_usgs",
            "name": "usgs_earthquake_catalog",
            "displayName": "USGS Real-Time Feed (GeoJSON)",
            "type": "pipeline",
            "tier": "External Source",
            "description": "API Oficial USGS: all_day.geojson (Ingesta cada 5 min) y all_month.geojson"
        },
        {
            "id": "bronze_feed",
            "name": "minio_sismowatch_lake.bronze.usgs_feed",
            "displayName": "s3://sismowatch-lake/bronze/",
            "type": "table",
            "tier": "Tier.Bronze",
            "description": "JSON Crudo Inmutable - Append Only - Sin Capa Landing Intermedia",
            "columns": ["raw_payload", "ingested_at", "batch_id", "source_url"]
        },
        {
            "id": "silver_earthquakes",
            "name": "minio_sismowatch_lake.silver.earthquakes",
            "displayName": "s3://sismowatch-lake/silver/earthquakes/",
            "type": "table",
            "tier": "Tier.Silver",
            "description": "Parquet Snappy Columnar - Deduplicado por updated DESC y tipado estricto con Pandas & Pandera (ADR 0010)",
            "columns": ["id", "magnitude", "place", "event_time_utc", "longitude", "latitude", "depth_km", "tsunami_alert", "quality_status"]
        },
        {
            "id": "gold_earthquakes",
            "name": "postgres_sismowatch.curated.gold_earthquakes",
            "displayName": "curated.gold_earthquakes (PostgreSQL)",
            "type": "table",
            "tier": "Tier.Gold",
            "description": "Serving Layer Relacional Indexado (B-Tree) para FastAPI y Agente IA",
            "columns": ["id", "magnitude", "place", "event_time_utc", "depth_km", "severity_label", "is_anomaly", "tsunami_alert"]
        },
        {
            "id": "gold_kpis",
            "name": "postgres_sismowatch.curated.gold_hourly_kpis",
            "displayName": "curated.gold_hourly_kpis",
            "type": "table",
            "tier": "Tier.Gold",
            "description": "Métricas agregadas horarias y severidad"
        },
        {
            "id": "gold_anomalies",
            "name": "postgres_sismowatch.curated.gold_anomalies",
            "displayName": "curated.gold_anomalies",
            "type": "table",
            "tier": "Tier.Gold",
            "description": "Detección estadística Z-Score > 2.5 y enjambres sísmicos"
        }
    ],
    "upstreamEdges": [
        {"fromEntity": "src_usgs", "toEntity": "bronze_feed", "pipeline": "airflow.dag_usgs_ingest"},
        {"fromEntity": "bronze_feed", "toEntity": "silver_earthquakes", "pipeline": "airflow.dag_medallion_processing"},
        {"fromEntity": "silver_earthquakes", "toEntity": "gold_earthquakes", "pipeline": "airflow.dag_medallion_processing"},
        {"fromEntity": "silver_earthquakes", "toEntity": "gold_kpis", "pipeline": "airflow.dag_medallion_processing"},
        {"fromEntity": "silver_earthquakes", "toEntity": "gold_anomalies", "pipeline": "airflow.dag_medallion_processing"}
    ],
    "reconciliation": {
        "rule": "Preservación Total de Datos (100% Fidelidad)",
        "fidelityRate": "100.0%",
        "quarantineMode": "Auditoría no destructiva (flags en quality_metrics)",
        "governanceEngine": "OpenMetadata Compatible Specification"
    }
}

class GovernanceHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Enable CORS
        if self.path == "/api/v1/lineage":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(LINEAGE_METADATA).encode("utf-8"))
        elif self.path == "/api/v1/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "HEALTHY", "service": "OpenMetadata SismoWatch Catalog"}).encode("utf-8"))
        else:
            # Serve index.html for root and any static files
            if self.path == "/" or not os.path.exists(self.path[1:]):
                self.path = "/index.html"
            return super().do_GET()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), GovernanceHandler) as httpd:
        print(f"OpenMetadata Governance Viewer running on port {PORT}...")
        httpd.serve_forever()
