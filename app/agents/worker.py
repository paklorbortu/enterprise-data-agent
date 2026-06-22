from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from app.config import DEFAULT_MODEL

def create_worker_agent(name: str, instruction: str, tools: list = None) -> Agent:
    """Helper function to scaffold worker agents.

    Args:
        name: Name of the worker agent.
        instruction: System instruction guiding the worker's behavior.
        tools: List of tools (functions) available to the worker.

    Returns:
        An initialized Agent instance.
    """
    return Agent(
        name=name,
        model=Gemini(
            model=DEFAULT_MODEL,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=instruction,
        tools=tools or [],
    )

# Placeholder workers (to be implemented with specific capabilities/tools)
data_extraction_worker = create_worker_agent(
    name="data_extraction_worker",
    instruction="You are a data extraction worker. Extract target data fields from input documents."
)

data_processing_worker = create_worker_agent(
    name="data_processing_worker",
    instruction="You are a data processing worker. Format, sanitize, and validate structured data."
)
