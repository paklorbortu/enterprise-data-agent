import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

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

_IS_WINDOWS = sys.platform == "win32"
_NPX = "npx.cmd" if _IS_WINDOWS else "npx"

# gdocs-mcp lives at the project root (same level as app/, frontend/)
# On Cloud Run: /app/gdocs-mcp  |  Locally: <project_root>/gdocs-mcp
_GDOCS_MCP_CWD = str(BASE_DIR / "gdocs-mcp")

# ==============================================================================
# MCP ENVIRONMENT CONTEXT ISOLATION
# ==============================================================================

bigquery_env = os.environ.copy()
bigquery_env["BIGQUERY_PROJECT_ID"] = os.getenv("BIGQUERY_PROJECT_ID", "")
bigquery_env["BIGQUERY_DATASET_ID"] = os.getenv("BIGQUERY_DATASET_ID", "")
_local_adc = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if _local_adc:
    bigquery_env["GOOGLE_APPLICATION_CREDENTIALS"] = _local_adc

docs_env = os.environ.copy()
if os.getenv("TARGET_DRIVE_FOLDER_ID"):
    docs_env["TARGET_DRIVE_FOLDER_ID"] = os.getenv("TARGET_DRIVE_FOLDER_ID", "")
if os.getenv("GDOCS_TOKEN_PATH"):
    docs_env["GDOCS_TOKEN_PATH"] = os.getenv("GDOCS_TOKEN_PATH")
if os.getenv("GDOCS_CREDENTIALS_PATH"):
    docs_env["GDOCS_CREDENTIALS_PATH"] = os.getenv("GDOCS_CREDENTIALS_PATH")

# ==============================================================================
# MCP SERVER CONFIGURATIONS
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
        "cwd": _GDOCS_MCP_CWD,
        "env": docs_env,
    },
    "chart-generator": {
        "command": _NPX,
        "args": ["-y", "@antv/mcp-server-chart"],
        "env": os.environ.copy(),
    },
}