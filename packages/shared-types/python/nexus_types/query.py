from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict


class QueryRequest(BaseModel):
    connection_id: str
    query: str
    conversation_id: Optional[str] = None


class SqlValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    estimated_rows: Optional[int] = None
    estimated_time_ms: Optional[int] = None


class ResultColumn(BaseModel):
    name: str
    type: str
    is_numeric: bool
    is_temporal: bool
    is_categorical: bool


class QueryResult(BaseModel):
    columns: List[ResultColumn]
    rows: List[Dict[str, Any]]
    total_rows: int
    truncated: bool = False
    execution_time_ms: int


class ChartSuggestion(BaseModel):
    chart_type: str
    title: str
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    group_by: Optional[str] = None
    confidence: float
    reason: str


class QueryMetadata(BaseModel):
    agents_used: List[str]
    total_time_ms: int
    llm_model: str
    llm_tokens_used: int
    cached: bool = False


class QueryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    natural_language_query: str
    generated_sql: str
    validation: SqlValidationResult
    result: Optional[QueryResult] = None
    explanation: str
    suggested_charts: List[ChartSuggestion] = []
    suggested_follow_ups: List[str] = []
    metadata: QueryMetadata
