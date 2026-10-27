from typing import Optional, Any
import logging

logger = logging.getLogger("api.services.chart_protocol")

SEVERITY_COLORS = {
    "Micro": "#4edea3",
    "Menor": "#adc6ff",
    "Moderado": "#ffb690",
    "Fuerte": "#ec6a06",
    "Mayor": "#ef4444"
}

def build_declarative_chart(
    chart_type: str,
    title: str,
    labels: list[str],
    data: list[Any],
    dataset_label: str = "Cantidad",
    color_palette: Optional[list[str]] = None
) -> dict:
    """
    Builds a declarative JSON specification for Chart.js.
    No code is executed on frontend or backend; components consume structured data.
    """
    if not chart_type or chart_type == "none" or not data:
        return {"type": "none"}
        
    if not color_palette:
        if chart_type in ("doughnut", "pie"):
            color_palette = ["#4edea3", "#adc6ff", "#ec6a06", "#f97316", "#ef4444"]
        else:
            color_palette = ["#adc6ff"] * len(data)

    return {
        "type": chart_type,
        "title": title,
        "labels": labels,
        "datasets": [
            {
                "label": dataset_label,
                "data": data,
                "backgroundColor": color_palette[:len(data)],
                "borderColor": "#181c24",
                "borderWidth": 1
            }
        ]
    }
