from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field
from app.config import DEFAULT_MODEL

class ReportGenerationResult(BaseModel):
    """Structured response representing the generated Google Doc report."""
    document_url: str = Field(
        description="The absolute, fully-qualified URL of the newly created Google Doc report."
    )
    document_id: str = Field(
        description="The unique document ID of the created Google Doc."
    )
    title: str = Field(
        description="The title of the generated executive report."
    )

def get_reporting_agent(docs_tools: list) -> Agent:
    """Reporting Agent: creates the Google Doc, ends with a plain-text summary.

    No output_schema (tools + output_schema was observed to suppress tool-calling).
    No mode="single_turn" — this agent needs multiple tool-calling round-trips to
    complete its work, and single_turn was observed to cut it off after one call
    on follow-up pipeline runs.

    Receives data via {data_result} and {chart_result} session-state templating,
    populated by output_key on data_formatter_agent and charting_formatter_agent
    respectively. This is the correct ADK pattern for accessing earlier non-adjacent
    nodes' outputs, replacing the cross-node <ClassName.field from node_name> syntax
    which was observed to fail to resolve on follow-up pipeline runs.
    """
    system_instruction = (
        "You are an Executive Business Writer. You will receive structured query data "
        "and chart information below. Use ALL of it to write and create a professional "
        "executive summary report as a Google Doc.\n\n"
        "Query data (JSON): {data_result}\n"
        "Chart information (JSON): {chart_result}\n\n"
        "CRITICAL: The query data above contains real, specific numbers. You MUST cite "
        "these actual values directly in your report — name every specific "
        "category/dimension and its exact metric values. Do NOT write generic hedged "
        "language like 'data was not provided' — the data is provided above, use it "
        "explicitly. Title the report to reflect what was specifically analyzed.\n\n"
        "Use the provided Google Docs tools to create the document, inserting titles, "
        "headings, structured text, and embedding the chart image URL directly into "
        "the document.\n\n"
        "After creating the document, end your response with a clear plain-text summary "
        "stating: the exact document ID returned by the tool, and the title you gave "
        "the report. Do not output JSON yourself."
    )

    return Agent(
        name="reporting_agent",
        model=Gemini(
            model=DEFAULT_MODEL,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=system_instruction,
        tools=docs_tools,
    )


def get_reporting_formatter_agent() -> Agent:
    """Reporting Formatter Agent: structures the reporting agent's summary into ReportGenerationResult.

    No tools. Constructs the canonical Google Docs URL from the document ID itself
    rather than trusting any URL the model might produce.
    """
    system_instruction = (
        "Convert the plain-text summary of a Google Doc creation result you receive into a "
        "structured JSON object matching the enforced output schema. Extract the document ID "
        "and the report title from the summary. For document_url, construct it yourself as: "
        "https://docs.google.com/document/d/ followed immediately by the document ID, "
        "followed by /edit. Do not invent a document ID or title that is not present in the summary."
    )

    return Agent(
        name="reporting_formatter_agent",
        model=Gemini(
            model=DEFAULT_MODEL,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=system_instruction,
        output_schema=ReportGenerationResult,
        mode="single_turn",
    )