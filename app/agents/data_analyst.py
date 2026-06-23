from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field
from app.config import DEFAULT_MODEL

class DataQueryResult(BaseModel):
    dimensions: list[str] = Field(description="The dimension names/categories representing the independent variables.")
    metrics: list[str] = Field(description="The metric or measure names representing the dependent variables.")
    data: list[dict] = Field(description="The query result rows as a list of dicts mapping column names to values.")

def get_data_analyst_agent(bigquery_tools: list) -> Agent:
    return Agent(
        name="data_analyst_agent",
        model=Gemini(model=DEFAULT_MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
        instruction=(
            "You are an expert Data Analyst with direct access to BigQuery tools. You MUST use these "
            "tools to answer every request. The data lives in BigQuery project `empyrean-verve-401907`, "
            "dataset `sales`, table `sales_table`. Fully qualified: `empyrean-verve-401907.sales.sales_table`.\n\n"
            "1. Inspect the schema if needed.\n"
            "2. Write and execute a SQL query.\n"
            "3. End your response with a plain-text summary of dimension names, metric names, and all data rows. "
            "Do not output JSON. Do not produce charts."
        ),
        tools=bigquery_tools,
    )

def get_data_formatter_agent() -> Agent:
    return Agent(
        name="data_formatter_agent",
        model=Gemini(model=DEFAULT_MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
        instruction=(
            "Convert the plain-text BigQuery summary you receive into a structured JSON object "
            "matching the enforced output schema. Extract dimension names, metric names, and data rows. "
            "Do not invent data not present in the summary."
        ),
        output_schema=DataQueryResult,
    )