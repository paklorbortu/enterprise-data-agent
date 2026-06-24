from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field
from app.config import DEFAULT_MODEL

class ReportGenerationResult(BaseModel):
    document_url: str = Field(description="The absolute URL of the created Google Doc report.")
    document_id: str = Field(description="The unique document ID of the created Google Doc.")
    title: str = Field(description="The title of the generated executive report.")

def get_reporting_agent(docs_tools: list) -> Agent:
    return Agent(
        name="reporting_agent",
        model=Gemini(model=DEFAULT_MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
        instruction=(
            "You are an Executive Business Writer with access to Google Docs tools. "
            "You will receive a user's business question along with structured query data and chart information "
            "directly in the message. Use ALL of it to write and create a professional executive report as a Google Doc.\n\n"
            "CRITICAL: The query data contains real, specific numbers. Cite every category and its exact values. "
            "Do NOT write generic language like 'data was not provided' — the data is in the message, use it explicitly.\n\n"
            "Use the Google Docs tools to create the document with titles, headings, structured text, "
            "and embed the chart image URL into the document.\n\n"
            "After creating the document, end your response with a plain-text summary stating: "
            "the exact document ID returned by the tool, and the title you gave the report. Do not output JSON."
        ),
        tools=docs_tools,
    )

def get_reporting_formatter_agent() -> Agent:
    return Agent(
        name="reporting_formatter_agent",
        model=Gemini(model=DEFAULT_MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
        instruction=(
            "Convert the plain-text summary of a Google Doc creation result into a structured JSON object "
            "matching the enforced output schema. Extract the document ID and report title from the summary. "
            "Construct the document_url by combining: https://docs.google.com/document/d/ + the document ID + /edit. "
            "Do not invent a document ID or title not present in the summary."
        ),
        output_schema=ReportGenerationResult,
    )