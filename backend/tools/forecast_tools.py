"""Trend projection tools for time-series analysis."""

import logging
import numpy as np

from backend.tools.base import BaseTool, ToolResult
from backend.config import get_settings

logger = logging.getLogger(__name__)


class TrendProjectionTool(BaseTool):
    name = "trend_projection"
    description = (
        "Projects a time-series forward using linear regression. "
        "Estimates future values and identifies trend direction. "
        "Args: values (list of numbers), periods_ahead (int, default 4), labels (optional list of labels for each value)."
    )

    async def execute(self, db_session, **kwargs) -> ToolResult:
        values = kwargs.get("values", [])
        periods_ahead = int(kwargs.get("periods_ahead", 4))
        labels = kwargs.get("labels")

        if not values or len(values) < 2:
            return ToolResult(tool_name=self.name, success=False, error="Need at least 2 data points")

        y = np.array(values, dtype=float)
        x = np.arange(len(y))

        # Linear regression
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs[0], coeffs[1]

        # Project forward
        future_x = np.arange(len(y), len(y) + periods_ahead)
        projections = (slope * future_x + intercept).tolist()

        # Trend classification
        settings = get_settings()
        if abs(slope) < settings.trend_stable_slope_factor * np.mean(y):
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        data = {
            "slope": round(float(slope), 4),
            "intercept": round(float(intercept), 4),
            "trend": trend,
            "r_squared": round(float(1 - np.sum((y - (slope * x + intercept))**2) / np.sum((y - np.mean(y))**2)), 4) if np.var(y) > 0 else 1.0,
            "projections": [round(v, 2) for v in projections],
            "current_value": round(float(y[-1]), 2),
            "projected_change_pct": round(float((projections[-1] - y[-1]) / y[-1] * 100), 1) if y[-1] != 0 else 0,
        }
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=1)
