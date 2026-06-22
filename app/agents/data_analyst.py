from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field
from app.config import DEFAULT_MODEL

class DataQueryResult(BaseModel):
    """Structured query output separating dimensions, metrics, and data rows."""
    dimensions: list[str] = Field(
        description="The dimension names/categories representing the independent variables (e.g., 'year', 'region', 'product_category')."
    )
    metrics: list[str] = Field(
        description="The metric or measure names representing the dependent variables (e.g., 'sales', 'revenue', 'transaction_count')."
    )
    data: list[dict] = Field(
        description="The query result rows, where each row is a dictionary containing key-value pairs corresponding to the dimensions and metrics."
    )

def get_data_analyst_agent(bigquery_tools: list) -> Agent:
    """Data Analyst Agent: queries BigQuery, ends with a plain-text summary.

    No output_schema (tools + output_schema was observed to suppress tool-calling).
    mode="single_turn" required for graph Workflow nodes.
    """
    system_instruction = (
        "You are an expert Data Analyst with direct access to BigQuery tools. You MUST use these "
        "tools to answer every request — never answer from assumptions or claim no data exists "
        "without first attempting to query the data.\n\n"
        "The data lives in BigQuery project `empyrean-verve-401907`, dataset `sales`, "
        "table `sales_table`. The fully qualified table reference for SQL queries is "
        "`empyrean-verve-401907.sales.sales_table` (use backticks around the full path in your SQL).\n\n"
        "Your process for every request:\n"
        "1. If you are not already certain of the table's column names and types, first use the "
        "available BigQuery tool(s) to inspect the schema of `empyrean-verve-401907.sales.sales_table`.\n"
        "2. Construct a SQL query against that exact fully qualified table to answer the user's request.\n"
        "3. Execute the query using the BigQuery tool.\n"
        "4. After receiving real query results, end your response with a clear plain-text summary "
        "listing: the dimension column names used, the metric column names used, and the actual "
        "data rows returned (as plain text, not JSON). Do not output JSON yourself.\n\n"
        "Under no circumstances should you attempt to visualize the data or produce charts."
    )

    return Agent(
        name="data_analyst_agent",
        model=Gemini(
            model=DEFAULT_MODEL,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=system_instruction,
        tools=bigquery_tools,
        mode="single_turn",
    )


def get_data_formatter_agent() -> Agent:
    """Data Formatter Agent: structures the analyst's plain-text summary into DataQueryResult.

    No tools — kept separate to avoid the output_schema + tools suppression issue.
    """
    system_instruction = (
        "Convert the plain-text summary of BigQuery query results you receive into a "
        "structured JSON object matching the enforced output schema. Extract the "
        "dimension names, metric names, and the data rows as a list of dictionaries "
        "mapping column names to values. Do not invent data that is not present "
        "in the summary. If the summary states that no data was found after a "
        "genuine query attempt, return empty lists."
    )

    return Agent(
        name="data_formatter_agent",
        model=Gemini(
            model=DEFAULT_MODEL,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=system_instruction,
        output_schema=DataQueryResult,
        mode="single_turn",
    )