from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class ChartType(str, Enum):
    bar = "bar"
    line = "line"
    scatter = "scatter"
    pie = "pie"
    heatmap = "heatmap"
    histogram = "histogram"
    area = "area"
    table = "table"
    metric = "metric"


class ChartConfig(BaseModel):
    type: ChartType
    title: Optional[str] = None
    description: Optional[str] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    group_by: Optional[str] = None
    color_scale: Optional[List[str]] = None
    show_legend: bool = True
    is_stacked: bool = False


class GridConfig(BaseModel):
    x: int
    y: int
    w: int
    h: int


class WidgetConfig(BaseModel):
    id: str
    query_id: Optional[str] = None
    sql: Optional[str] = None
    chart_config: ChartConfig
    grid: GridConfig


class DashboardLayout(BaseModel):
    columns: int = 12
    row_height: int = 150


class DashboardConfig(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    widgets: List[WidgetConfig] = []
    layout: DashboardLayout
    created_at: str
    updated_at: str
