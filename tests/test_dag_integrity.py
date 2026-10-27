import ast
import os
import glob
import pytest

DAG_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "airflow", "dags"))

def get_dag_files():
    """Discovers all python files in the airflow/dags directory."""
    return glob.glob(os.path.join(DAG_FOLDER, "*.py"))

def test_dag_files_exist():
    """Verifies that all 4 required DAGs exist in airflow/dags/."""
    expected_dags = [
        "dag_usgs_ingest.py",
        "dag_pyspark_medallion.py",
        "dag_daily_ai_report.py",
        "dag_historical_backfill.py"
    ]
    dag_files = [os.path.basename(f) for f in get_dag_files()]
    for expected in expected_dags:
        assert expected in dag_files, f"DAG file '{expected}' is missing from airflow/dags/"

@pytest.mark.parametrize("dag_path", get_dag_files())
def test_dag_ast_syntax(dag_path):
    """
    Verifies that all Airflow DAGs parse cleanly with Python's Abstract Syntax Tree (AST).
    Catches indentation, syntax, or invalid token errors without requiring a heavy Airflow runtime.
    """
    with open(dag_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Parse syntax
    tree = ast.parse(source, filename=dag_path)
    assert tree is not None, f"Failed to parse AST for {dag_path}"

def test_dag_schedule_and_definitions():
    """Inspects DAG code to verify schedules and key task definitions."""
    ingest_path = os.path.join(DAG_FOLDER, "dag_usgs_ingest.py")
    with open(ingest_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "dag_usgs_ingest" in content
    assert "fetch_and_store_bronze" in content
    assert "*/5 * * * *" in content

    medallion_path = os.path.join(DAG_FOLDER, "dag_pyspark_medallion.py")
    with open(medallion_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "dag_pyspark_medallion" in content
    assert "transform_bronze_to_silver" in content
    assert "transform_silver_to_gold" in content

    ai_report_path = os.path.join(DAG_FOLDER, "dag_daily_ai_report.py")
    with open(ai_report_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "dag_daily_ai_report" in content
    assert "generate_daily_executive_report" in content

    backfill_path = os.path.join(DAG_FOLDER, "dag_historical_backfill.py")
    with open(backfill_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "dag_historical_backfill" in content
    assert "execute_backfill" in content
