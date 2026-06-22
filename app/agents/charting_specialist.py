from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field
from app.config import DEFAULT_MODEL

class ChartingResult(BaseModel):
    """Structured response containing generated chart assets."""
    chart_image_url: str = Field(
        description="The local asset path, file path, or URL of the generated chart image (typically returned by the chart generator tool)."
    )
    chart_type: str = Field(
        description="The type of chart generated (e.g., 'bar', 'line', 'pie', 'scatter')."
    )
    dimensions_visualized: list[str] = Field(
        description="The dimensions from the query result that were plotted on the chart."
    )
    metrics_visualized: list[str] = Field(
        description="The metrics/measures from the query result that were plotted on the chart."
    )

def get_charting_specialist_agent(charting_tools: list) -> Agent:
    """Charting Specialist Agent: generates a chart, ends with a plain-text summary.

    No output_schema (27 tools + output_schema exceeds Gemini's schema complexity limit).
    mode="single_turn" required for graph Workflow nodes.
    """
    system_instruction = (
        "You are an expert Data Visualization Engineer. Your job is to take structured data "
        "represented by dimensions, metrics, and data rows (from a DataQueryResult), "
        "select the most appropriate chart type (e.g., bar chart for categorical data, line chart "
        "for time-series data, pie chart for relative shares), formulate the correct payload, "
        "and invoke the appropriate charting tool from the `@antv/mcp-server-chart` library. "
        "After the chart has been generated, end your response with a clear plain-text summary "
        "stating: the exact asset URL or file path returned by the tool, the chart type used, "
        "and which dimensions and metrics were plotted. Do not output JSON yourself; just "
        "state these facts clearly in plain text."
    )

    return Agent(
        name="charting_specialist_agent",
        model=Gemini(
            model=DEFAULT_MODEL,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=system_instruction,
        tools=charting_tools,
        mode="single_turn",
    )


def get_charting_formatter_agent() -> Agent:
    """Charting Formatter Agent: structures the specialist's plain-text summary into ChartingResult.

    No tools — kept separate to avoid Gemini's schema complexity limit.
    """
    system_instruction = (
        "You convert a plain-text summary of a chart generation result into a "
        "structured JSON object matching the enforced output schema. Extract the "
        "chart's asset URL/path, chart type, and the dimensions and metrics that "
        "were visualized. Do not invent information that is not present in the summary."
    )

    return Agent(
        name="charting_formatter_agent",
        model=Gemini(
            model=DEFAULT_MODEL,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=system_instruction,
        output_schema=ChartingResult,
        mode="single_turn",
    )