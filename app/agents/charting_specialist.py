from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field
from app.config import DEFAULT_MODEL

class ChartingResult(BaseModel):
    chart_image_url: str = Field(description="The URL or file path of the generated chart image.")
    chart_type: str = Field(description="The type of chart generated (bar, line, pie, scatter, etc.).")
    dimensions_visualized: list[str] = Field(description="The dimensions plotted on the chart.")
    metrics_visualized: list[str] = Field(description="The metrics plotted on the chart.")

def get_charting_specialist_agent(charting_tools: list) -> Agent:
    return Agent(
        name="charting_specialist_agent",
        model=Gemini(model=DEFAULT_MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
        instruction=(
            "You are an expert Data Visualization Engineer. Take the structured data (dimensions, metrics, rows), "
            "select the most appropriate chart type, and invoke the charting tool from @antv/mcp-server-chart. "
            "End your response with a plain-text summary stating: the exact asset URL returned by the tool, "
            "the chart type used, and which dimensions and metrics were plotted. Do not output JSON."
        ),
        tools=charting_tools,
    )

def get_charting_formatter_agent() -> Agent:
    return Agent(
        name="charting_formatter_agent",
        model=Gemini(model=DEFAULT_MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
        instruction=(
            "Convert the plain-text chart generation summary you receive into a structured JSON object "
            "matching the enforced output schema. Extract the chart URL/path, chart type, and the "
            "dimensions and metrics visualized. Do not invent information not in the summary."
        ),
        output_schema=ChartingResult,
    )