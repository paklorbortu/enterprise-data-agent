import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

# GCP & Model Configurations
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
BIGQUERY_LOCATION = os.getenv("BIGQUERY_LOCATION", "asia-east1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GOOGLE_CLOUD_PROJECT:
    os.environ["GOOGLE_CLOUD_PROJECT"] = GOOGLE_CLOUD_PROJECT
os.environ["GOOGLE_CLOUD_LOCATION"] = GOOGLE_CLOUD_LOCATION
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

# ==============================================================================
# MCP ENVIRONMENT CONTEXT ISOLATION
# ==============================================================================

# 1. BigQuery Environment Setup
bigquery_env = os.environ.copy()
bigquery_env["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
bigquery_env["BIGQUERY_PROJECT_ID"] = os.getenv("BIGQUERY_PROJECT_ID", "")
bigquery_env["BIGQUERY_DATASET_ID"] = os.getenv("BIGQUERY_DATASET_ID", "")

# 2. Google Docs Environment Setup
docs_env = os.environ.copy()
if os.getenv("TARGET_DRIVE_FOLDER_ID"):
    docs_env["TARGET_DRIVE_FOLDER_ID"] = os.getenv("TARGET_DRIVE_FOLDER_ID", "")

# ==============================================================================
# MODEL CONTEXT PROTOCOL (MCP) SERVER CONFIGURATIONS
# ==============================================================================
MCP_SERVERS = {
    "bigquery": {
        "command": "uvx",
        "args": [
            "mcp-server-bigquery",
            "--project", os.getenv("BIGQUERY_PROJECT_ID", ""),
            "--location", BIGQUERY_LOCATION,
        ],
        "env": bigquery_env,
        "timeout": 90,
    },
    "google-docs": {
        "command": "node",
        "args": ["build/server.js"],
        "cwd": "C:/Users/phili/Documents/capstone-project/enterprise-data-agent/gdocs-mcp",
        "env": docs_env
    },
    "chart-generator": {
        "command": "npx.cmd",
        "args": ["-y", "@antv/mcp-server-chart"],
        "env": os.environ.copy()
    }
}
