"""
Utility functions for the Agent Orchestration System.

Includes logging, formatting, validation, and common helper functions.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime
import hashlib
from config import LOG_LEVEL, LOG_FILE, LOGS_DIR


def setup_logging(name: str = "agent_system") -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # File handler
    log_path = LOGS_DIR / LOG_FILE
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(getattr(logging, LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logging()


def format_json(obj: Any, indent: int = 2) -> str:
    """Format object as pretty JSON."""
    try:
        return json.dumps(obj, indent=indent, default=str)
    except (TypeError, ValueError):
        return str(obj)


def log_section(title: str, level: str = "info") -> None:
    """Log a section header."""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def log_step(step: int, description: str, level: str = "info") -> None:
    """Log a numbered step."""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"[Step {step}] {description}")


def hash_request(request: str) -> str:
    """Generate a hash of a request string."""
    return hashlib.sha256(request.encode()).hexdigest()[:8]


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_duration_ms(ms: float) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    else:
        return f"{ms / 60000:.1f}m"


def format_cost(cost: float) -> str:
    """Format cost as currency."""
    return f"${cost:.4f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format as percentage."""
    return f"{value * 100:.{decimals}f}%"


def validate_schema(obj: Dict, schema: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate an object against a JSON schema.
    
    Returns:
        (is_valid, error_message)
    """
    # Simplified validation — in production, use jsonschema library
    required_fields = schema.get("required", [])
    
    for field in required_fields:
        if field not in obj:
            return False, f"Missing required field: {field}"
    
    return True, None


def extract_json_from_text(text: str) -> Optional[Dict]:
    """Extract JSON object from text, handling markdown code blocks."""
    import re
    
    # Try to find JSON in code blocks first
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Fall back to finding any JSON object
    json_pattern = r"\{.*\}"
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    return None


def merge_dicts(base: Dict, updates: Dict, deep: bool = True) -> Dict:
    """
    Merge two dictionaries.
    
    Args:
        base: Base dictionary
        updates: Dictionary with updates
        deep: If True, merge recursively
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in updates.items():
        if deep and isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result


def safe_get(obj: Any, path: str, default: Any = None) -> Any:
    """
    Safely get nested value using dot notation.
    
    Example:
        safe_get({"a": {"b": {"c": 1}}}, "a.b.c") → 1
        safe_get({}, "a.b.c", default=0) → 0
    """
    keys = path.split(".")
    current = obj
    
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        
        if current is None:
            return default
    
    return current


class ContextManager:
    """Simple context manager for tracking execution state."""
    
    _stack = []
    
    @classmethod
    def push(cls, context: Dict) -> None:
        """Push a context onto the stack."""
        cls._stack.append(context)
    
    @classmethod
    def pop(cls) -> Optional[Dict]:
        """Pop a context from the stack."""
        return cls._stack.pop() if cls._stack else None
    
    @classmethod
    def current(cls) -> Optional[Dict]:
        """Get current context without popping."""
        return cls._stack[-1] if cls._stack else None
    
    @classmethod
    def clear(cls) -> None:
        """Clear all contexts."""
        cls._stack.clear()


class Timer:
    """Simple timer for measuring execution time."""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
    
    def start(self) -> None:
        """Start the timer."""
        self.start_time = datetime.now()
    
    def stop(self) -> None:
        """Stop the timer."""
        self.end_time = datetime.now()
    
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if not self.start_time or not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() * 1000
    
    def __str__(self) -> str:
        elapsed = self.elapsed_ms()
        name_str = f"{self.name}: " if self.name else ""
        return f"{name_str}{format_duration_ms(elapsed)}"
