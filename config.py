"""
Configuration and environment settings for the Agent Orchestration System.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Model Configuration
DEFAULT_PLANNING_MODEL = os.getenv("PLANNING_MODEL", "gpt-4-turbo")
DEFAULT_SPECIALIST_MODEL = os.getenv("SPECIALIST_MODEL", "gpt-4-turbo")
DEFAULT_REVIEW_MODEL = os.getenv("REVIEW_MODEL", "gpt-4-turbo")

# Orchestration Configuration
PLAN_CONFIDENCE_THRESHOLD = float(os.getenv("PLAN_CONFIDENCE_THRESHOLD", "0.6"))
MAX_RETRIES_PER_SUBTASK = int(os.getenv("MAX_RETRIES", "2"))
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("TIMEOUT", "300"))

# Tool Configuration
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
ENABLE_CODE_EXECUTION = os.getenv("ENABLE_CODE_EXECUTION", "true").lower() == "true"
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))

# Database Configuration (for Phase 2+)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/agent_system")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "agent_system.log")

# UI Configuration
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
TRACE_EXPLORER_PORT = int(os.getenv("TRACE_EXPLORER_PORT", "8502"))

# Cost Tracking
TRACK_COSTS = os.getenv("TRACK_COSTS", "true").lower() == "true"
COST_ALERT_THRESHOLD = float(os.getenv("COST_ALERT_THRESHOLD", "10.0"))  # $10 per task

# Execution Mode
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
MOCK_EXECUTION = os.getenv("MOCK_EXECUTION", "false").lower() == "true"

# Directories
BASE_DIR = Path(__file__).parent
CORE_DIR = BASE_DIR / "core"
TOOLS_DIR = BASE_DIR / "tools"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create necessary directories
for directory in [DATA_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)
