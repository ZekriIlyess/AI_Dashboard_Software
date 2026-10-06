"""ML Pipeline API endpoints.

Provides REST endpoints for:
- Training AutoML models (background task)
- Listing / retrieving trained models
- Making predictions with saved models
- SHAP explainability data
- Time-series forecasting
- Anomaly detection
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decrypt_password, get_current_user
from app.database import AsyncSessionLocal, get_db
from app.models.connection import DatabaseConnection
from app.models.ml_model import MLModel
from app.api.websocket import manager

from nexus_connectors.postgresql import PostgreSQLConnector
from nexus_connectors.mysql import MySQLConnector
from nexus_connectors.sqlite import SQLiteConnector
from nexus_connectors.snowflake import SnowflakeConnector
from nexus_connectors.bigquery import BigQueryConnector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ml"])

# ---------------------------------------------------------------------------
# Artifact storage directory
# ---------------------------------------------------------------------------
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "ml_artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class TrainRequest(BaseModel):
    connection_id: uuid.UUID
    table_name: str
    target_column: str
    task_type: Optional[str] = None  # "classification" | "regression" | None (auto)
    name: Optional[str] = None  # Friendly name for the model
    max_time_seconds: int = Field(default=300, ge=10, le=3600)

class TrainResponse(BaseModel):
    model_id: str
    status: str

class PredictRequest(BaseModel):
    data: List[Dict[str, Any]]

class ForecastRequest(BaseModel):
    connection_id: uuid.UUID
    query: str  # SQL query to fetch time-series data
    date_column: Optional[str] = None
    value_column: Optional[str] = None
    periods: int = Field(default=30, ge=1, le=365)
    frequency: str = "D"

class AnomalyRequest(BaseModel):
    connection_id: uuid.UUID
    query: str  # SQL query to fetch data
    columns: Optional[List[str]] = None
    method: str = "auto"  # "auto", "zscore", "isolation_forest", "iqr"
    contamination: float = Field(default=0.05, gt=0.0, lt=0.5)

class CausalRequest(BaseModel):
    connection_id: uuid.UUID
    query: str
    treatment_column: str
    outcome_column: str
    common_causes: List[str]

class SimulationRequest(BaseModel):
    model_id: uuid.UUID
    connection_id: uuid.UUID
    table_name: str
    variations: Dict[str, Dict[str, Any]]
    n_iterations: int = 1000
    target_threshold: Optional[float] = None


# ---------------------------------------------------------------------------
# Helper: build a connector from a DatabaseConnection ORM object
# ---------------------------------------------------------------------------
def _build_connector(conn: DatabaseConnection, decrypted_password: str | None):
    """Return the appropriate nexus_connectors instance."""
    db_type = conn.db_type
    if db_type in ("postgresql", "postgres"):
        return PostgreSQLConnector(
            host=conn.host, port=conn.port, database=conn.database,
            user=conn.username, password=decrypted_password,
        )
    elif db_type == "mysql":
        return MySQLConnector(
            host=conn.host, port=conn.port, database=conn.database,
            user=conn.username, password=decrypted_password,
        )
    elif db_type == "sqlite":
        return SQLiteConnector(database_path=conn.host)
    elif db_type == "snowflake":
        return SnowflakeConnector(
            account=conn.host, user=conn.username,
            password=decrypted_password, database=conn.database,
        )
    elif db_type == "bigquery":
        return BigQueryConnector(host=conn.host, project_id=conn.database)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


# ---------------------------------------------------------------------------
# Background: model training pipeline
# ---------------------------------------------------------------------------
async def _train_model_task(
    model_id: uuid.UUID,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
    table_name: str,
    target_column: str,
    task_type: str | None,
    max_time_seconds: int,
):
    """Background worker that runs the full ML pipeline."""
    from app.ml.feature_engineering import FeatureEngineer
    from app.ml.model_tournament import ModelTournament
    from app.ml.explainability import Explainer

    async with AsyncSessionLocal() as db:
        try:
            # ---- 1. Load connection & fetch data ----
            stmt = select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
            result = await db.execute(stmt)
            conn = result.scalar_one_or_none()
            if not conn:
                raise Exception("Database connection not found")

            decrypted_pw = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
            connector = _build_connector(conn, decrypted_pw)

            logger.info(f"[ML:{model_id}] Fetching data from {table_name}...")
            await manager.broadcast_to_session(str(model_id), {
                "type": "ml_progress", "model_id": str(model_id),
                "step": "fetching_data", "message": f"Fetching data from {table_name}..."
            })

            sql = f"SELECT * FROM {table_name} LIMIT 50000"
            raw_data = await connector.execute_query(sql)

            if not raw_data or len(raw_data) < 10:
                raise Exception(f"Table '{table_name}' has insufficient data ({len(raw_data) if raw_data else 0} rows, need ≥10)")

            # ---- 2. Feature Engineering ----
            logger.info(f"[ML:{model_id}] Running feature engineering...")
            await manager.broadcast_to_session(str(model_id), {
                "type": "ml_progress", "model_id": str(model_id),
                "step": "feature_engineering", "message": "Engineering features..."
            })

            engineer = FeatureEngineer()
            fe_result = engineer.prepare(
                data=raw_data,
                target_column=target_column,
                task_type=task_type,
            )

            # ---- 3. Model Tournament ----
            logger.info(f"[ML:{model_id}] Starting model tournament ({fe_result.task_type})...")
            await manager.broadcast_to_session(str(model_id), {
                "type": "ml_progress", "model_id": str(model_id),
                "step": "model_tournament", "message": f"Training models ({fe_result.task_type})..."
            })

            tournament = ModelTournament()
            tourney_result = tournament.run(
                X=fe_result.X,
                y=fe_result.y,
                task_type=fe_result.task_type,
                max_time_seconds=max_time_seconds,
            )

            # ---- 4. SHAP Explainability ----
            logger.info(f"[ML:{model_id}] Computing SHAP explanations...")
            await manager.broadcast_to_session(str(model_id), {
                "type": "ml_progress", "model_id": str(model_id),
                "step": "explainability", "message": "Computing SHAP explanations..."
            })

            explainer = Explainer()
            shap_result = explainer.explain(
                model=tourney_result.best_model,
                X_test=tourney_result.X_test,
                feature_names=fe_result.feature_names,
            )

            # ---- 5. Save model artifact ----
            artifact_path = str(ARTIFACTS_DIR / f"{model_id}.joblib")
            joblib.dump({
                "model": tourney_result.best_model,
                "scaler": fe_result.scaler,
                "label_encoder": fe_result.label_encoder,
                "feature_names": fe_result.feature_names,
                "task_type": fe_result.task_type,
                "label_mapping": fe_result.label_mapping,
            }, artifact_path)

            # ---- 6. Update DB record ----
            stmt = select(MLModel).where(MLModel.id == model_id)
            res = await db.execute(stmt)
            ml_model = res.scalar_one_or_none()

            if ml_model:
                ml_model.status = "completed"
                ml_model.model_type = tourney_result.best_model_name
                ml_model.task_type = fe_result.task_type
                ml_model.feature_columns = fe_result.feature_names
                ml_model.metrics = {
                    "tournament": [
                        {"name": r.name, "metrics": r.metrics, "training_time": r.training_time, "rank": r.rank}
                        for r in tourney_result.results
                    ],
                    "cv_scores": tourney_result.cv_scores,
                    "total_time": tourney_result.total_time,
                }
                ml_model.feature_importance = tourney_result.feature_importance
                ml_model.hyperparameters = {
                    "best_model": tourney_result.best_model_name,
                    "shap_method": shap_result.method,
                    "shap_global_importance": shap_result.global_importance[:10],
                    "shap_waterfall": shap_result.waterfall_data,
                    "shap_summary": shap_result.summary_data,
                    "fe_stats": fe_result.stats,
                    "fe_encoding_map": fe_result.encoding_map,
                    "fe_dropped_columns": fe_result.dropped_columns,
                }
                ml_model.training_time_seconds = tourney_result.total_time
                ml_model.artifact_path = artifact_path
                await db.commit()

            logger.info(f"[ML:{model_id}] Training completed! Best: {tourney_result.best_model_name}")
            await manager.broadcast_to_session(str(model_id), {
                "type": "ml_complete", "model_id": str(model_id),
                "message": f"Training complete! Best model: {tourney_result.best_model_name}",
                "best_model": tourney_result.best_model_name,
            })

        except Exception as exc:
            logger.error(f"[ML:{model_id}] Training failed: {exc}")
            # Update DB with error
            stmt = select(MLModel).where(MLModel.id == model_id)
            res = await db.execute(stmt)
            ml_model = res.scalar_one_or_none()
            if ml_model:
                ml_model.status = "failed"
                ml_model.error_message = str(exc)
                await db.commit()

            await manager.broadcast_to_session(str(model_id), {
                "type": "ml_error", "model_id": str(model_id),
                "message": str(exc),
            })


# ---------------------------------------------------------------------------
# POST /ml/train — Start model training
# ---------------------------------------------------------------------------
@router.post("/train", response_model=TrainResponse)
async def train_model(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Start AutoML training pipeline as a background task."""
    # Verify connection
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == request.connection_id,
        DatabaseConnection.user_id == user.id,
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    # Create ML model record
    model_name = request.name or f"Model on {request.table_name}.{request.target_column}"
    ml_model = MLModel(
        user_id=user.id,
        name=model_name,
        model_type="pending",
        task_type=request.task_type or "auto",
        target_column=request.target_column,
        status="training",
    )
    db.add(ml_model)
    await db.commit()
    await db.refresh(ml_model)

    # Queue background training
    background_tasks.add_task(
        _train_model_task,
        model_id=ml_model.id,
        connection_id=request.connection_id,
        user_id=user.id,
        table_name=request.table_name,
        target_column=request.target_column,
        task_type=request.task_type,
        max_time_seconds=request.max_time_seconds,
    )

    return TrainResponse(model_id=str(ml_model.id), status="training")


# ---------------------------------------------------------------------------
# GET /ml/models — List all models for user
# ---------------------------------------------------------------------------
@router.get("/models")
async def list_models(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all ML models for the authenticated user."""
    stmt = (
        select(MLModel)
        .where(MLModel.user_id == user.id)
        .order_by(MLModel.created_at.desc())
    )
    result = await db.execute(stmt)
    models = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "name": m.name,
            "model_type": m.model_type,
            "task_type": m.task_type,
            "target_column": m.target_column,
            "status": m.status,
            "training_time_seconds": m.training_time_seconds,
            "metrics": m.metrics,
            "feature_importance": m.feature_importance,
            "error_message": m.error_message,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in models
    ]


# ---------------------------------------------------------------------------
# GET /ml/models/{model_id} — Get model details
# ---------------------------------------------------------------------------
@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get detailed model info including SHAP data."""
    stmt = select(MLModel).where(
        MLModel.id == model_id,
        MLModel.user_id == user.id,
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "id": str(model.id),
        "name": model.name,
        "model_type": model.model_type,
        "task_type": model.task_type,
        "target_column": model.target_column,
        "feature_columns": model.feature_columns,
        "status": model.status,
        "metrics": model.metrics,
        "feature_importance": model.feature_importance,
        "hyperparameters": model.hyperparameters,
        "training_time_seconds": model.training_time_seconds,
        "error_message": model.error_message,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
    }


# ---------------------------------------------------------------------------
# POST /ml/models/{model_id}/predict — Make predictions
# ---------------------------------------------------------------------------
@router.post("/models/{model_id}/predict")
async def predict(
    model_id: str,
    request: PredictRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Make predictions using a trained model."""
    stmt = select(MLModel).where(
        MLModel.id == model_id,
        MLModel.user_id == user.id,
        MLModel.status == "completed",
    )
    result = await db.execute(stmt)
    model_record = result.scalar_one_or_none()
    if not model_record:
        raise HTTPException(status_code=404, detail="Trained model not found")

    if not model_record.artifact_path:
        raise HTTPException(status_code=400, detail="Model artifact not found")

    try:
        artifact = joblib.load(model_record.artifact_path)
        model = artifact["model"]
        scaler = artifact["scaler"]
        feature_names = artifact["feature_names"]
        label_mapping = artifact.get("label_mapping")

        # Prepare input data
        df = pd.DataFrame(request.data)
        # Keep only feature columns that were used during training
        missing_cols = [c for c in feature_names if c not in df.columns]
        if missing_cols:
            for col in missing_cols:
                df[col] = 0  # Default missing features to 0

        X = df[feature_names]
        X_scaled = pd.DataFrame(scaler.transform(X), columns=feature_names)

        predictions = model.predict(X_scaled)
        predictions_list = [float(p) for p in predictions]

        # Map labels back for classification
        if label_mapping:
            predictions_list = [
                label_mapping.get(int(p), str(p)) for p in predictions
            ]

        return {"predictions": predictions_list}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(exc)}")


# ---------------------------------------------------------------------------
# GET /ml/models/{model_id}/explain — Get SHAP data
# ---------------------------------------------------------------------------
@router.get("/models/{model_id}/explain")
async def explain_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get SHAP explainability data for a model."""
    stmt = select(MLModel).where(
        MLModel.id == model_id,
        MLModel.user_id == user.id,
        MLModel.status == "completed",
    )
    result = await db.execute(stmt)
    model_record = result.scalar_one_or_none()
    if not model_record:
        raise HTTPException(status_code=404, detail="Model not found")

    hp = model_record.hyperparameters or {}
    return {
        "model_id": str(model_record.id),
        "model_name": model_record.name,
        "method": hp.get("shap_method", "unknown"),
        "global_importance": hp.get("shap_global_importance", []),
        "waterfall_data": hp.get("shap_waterfall", {}),
        "summary_data": hp.get("shap_summary", []),
        "feature_importance": model_record.feature_importance or [],
    }


# ---------------------------------------------------------------------------
# POST /ml/forecast — Time-series forecasting
# ---------------------------------------------------------------------------
@router.post("/forecast")
async def run_forecast(
    request: ForecastRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Run time-series forecasting on query results."""
    from app.ml.time_series import TimeSeriesForecaster

    # Verify connection
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == request.connection_id,
        DatabaseConnection.user_id == user.id,
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        decrypted_pw = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
        connector = _build_connector(conn, decrypted_pw)

        # Execute query to fetch data
        raw_data = await connector.execute_query(request.query)
        if not raw_data:
            raise HTTPException(status_code=400, detail="Query returned no data")

        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=raw_data,
            date_column=request.date_column,
            value_column=request.value_column,
            periods=request.periods,
            frequency=request.frequency,
        )

        return {
            "forecast_data": result.forecast_data,
            "historical_data": result.historical_data,
            "components": result.components,
            "metrics": result.metrics,
            "date_column": result.date_column,
            "value_column": result.value_column,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error(f"Forecast failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(exc)}")


# ---------------------------------------------------------------------------
# POST /ml/anomalies — Anomaly detection
# ---------------------------------------------------------------------------
@router.post("/anomalies")
async def detect_anomalies(
    request: AnomalyRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Run anomaly detection on query results."""
    from app.ml.anomaly_detection import AnomalyDetector

    # Verify connection
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == request.connection_id,
        DatabaseConnection.user_id == user.id,
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        decrypted_pw = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
        connector = _build_connector(conn, decrypted_pw)

        raw_data = await connector.execute_query(request.query)
        if not raw_data:
            raise HTTPException(status_code=400, detail="Query returned no data")

        detector = AnomalyDetector()
        result = detector.detect(
            data=raw_data,
            columns=request.columns,
            method=request.method,
            contamination=request.contamination,
        )

        return {
            "anomalies": [
                {
                    "row_index": a.row_index,
                    "values": a.values,
                    "score": a.score,
                    "severity": a.severity,
                }
                for a in result.anomalies
            ],
            "total_rows": result.total_rows,
            "anomaly_count": result.anomaly_count,
            "anomaly_rate": result.anomaly_rate,
            "method": result.method,
            "columns_analyzed": result.columns_analyzed,
            "column_stats": result.column_stats,
            "thresholds": result.thresholds,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error(f"Anomaly detection failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(exc)}")


# ---------------------------------------------------------------------------
# DELETE /ml/models/{model_id} — Delete a model
# ---------------------------------------------------------------------------
@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Delete a trained model and its artifact."""
    stmt = select(MLModel).where(
        MLModel.id == model_id,
        MLModel.user_id == user.id,
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Delete artifact file
    if model.artifact_path:
        artifact_file = Path(model.artifact_path)
        if artifact_file.exists():
            artifact_file.unlink()

    await db.delete(model)
    await db.commit()
    return {"status": "deleted", "model_id": model_id}


# ---------------------------------------------------------------------------
# GET /ml/connections/{connection_id}/tables — List tables for ML
# ---------------------------------------------------------------------------
@router.get("/connections/{connection_id}/tables")
async def list_tables_for_ml(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List tables and their columns for a connection (for target column selection)."""
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.user_id == user.id,
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        decrypted_pw = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
        connector = _build_connector(conn, decrypted_pw)
        schema = await connector.get_schema()

        # schema is typically a dict of {table_name: [{column_name, data_type, ...}]}
        tables = []
        for table_name, columns in schema.items():
            tables.append({
                "table_name": table_name,
                "columns": [
                    {
                        "name": col.get("column_name", col.get("name", "")),
                        "type": col.get("data_type", col.get("type", "unknown")),
                    }
                    for col in columns
                ] if isinstance(columns, list) else [],
            })

        return {"tables": tables}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {str(exc)}")


# ---------------------------------------------------------------------------
# POST /ml/causal — Causal Inference
# ---------------------------------------------------------------------------
@router.post("/causal")
async def run_causal_analysis(
    request: CausalRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Run causal inference analysis on query results."""
    from app.ml.causal_inference import CausalAnalyzer

    # Verify connection
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == request.connection_id,
        DatabaseConnection.user_id == user.id,
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        decrypted_pw = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
        connector = _build_connector(conn, decrypted_pw)

        raw_data = await connector.execute_query(request.query)
        if not raw_data:
            raise HTTPException(status_code=400, detail="Query returned no data")

        analyzer = CausalAnalyzer()
        res = analyzer.analyze(
            data=raw_data,
            treatment_col=request.treatment_column,
            outcome_col=request.outcome_column,
            common_causes=request.common_causes,
        )

        return {
            "treatment": res.treatment,
            "outcome": res.outcome,
            "estimated_effect": res.estimated_effect,
            "confidence_interval": res.confidence_interval,
            "p_value": res.p_value,
            "method_used": res.method_used,
            "refutation_status": res.refutation_status,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error(f"Causal analysis failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Causal analysis failed: {str(exc)}")


# ---------------------------------------------------------------------------
# POST /ml/simulate — Scenario Simulation
# ---------------------------------------------------------------------------
@router.post("/simulate")
async def run_scenario_simulation(
    request: SimulationRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Run scenario simulation on a trained model's inputs."""
    from app.ml.scenario_sim import ScenarioSimulator

    # Verify model belongs to user and is completed
    stmt = select(MLModel).where(
        MLModel.id == request.model_id,
        MLModel.user_id == user.id,
        MLModel.status == "completed",
    )
    result = await db.execute(stmt)
    model_record = result.scalar_one_or_none()
    if not model_record or not model_record.artifact_path:
        raise HTTPException(status_code=404, detail="Trained model artifact not found")

    # Verify database connection
    conn_stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == request.connection_id,
        DatabaseConnection.user_id == user.id,
    )
    conn_res = await db.execute(conn_stmt)
    conn = conn_res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        decrypted_pw = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
        connector = _build_connector(conn, decrypted_pw)

        # Fetch base data to establish simulation defaults
        query = f"SELECT * FROM {request.table_name} LIMIT 5000"
        raw_data = await connector.execute_query(query)
        if not raw_data:
            raise HTTPException(status_code=400, detail="Base table query returned no data")

        simulator = ScenarioSimulator()
        res = simulator.simulate(
            model_artifact_path=model_record.artifact_path,
            base_data=raw_data,
            variations=request.variations,
            n_iterations=request.n_iterations,
            target_threshold=request.target_threshold,
        )

        return {
            "mean": res.mean,
            "std": res.std,
            "min": res.min,
            "max": res.max,
            "p5": res.p5,
            "p25": res.p25,
            "median": res.median,
            "p75": res.p75,
            "p95": res.p95,
            "simulated_values": res.simulated_values,
            "target_probability": res.target_probability,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error(f"Scenario simulation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Scenario simulation failed: {str(exc)}")
