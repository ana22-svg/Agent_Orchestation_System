"""
Tool registry for managing available tools, their schemas, and usage tracking.

Tracks:
- Tool definitions (name, description, input/output schema)
- Which specialists can use each tool
- Rate limits and cost
- Invocation logs (inputs, outputs, latency, success/failure)
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum
import json
from datetime import datetime
import asyncio
from functools import wraps


class ToolCategory(str, Enum):
    """Categories of tools."""
    WEB_SEARCH = "web_search"
    FILE_OPS = "file_operations"
    CODE_EXECUTION = "code_execution"
    DATABASE = "database"
    API_CALL = "api_call"
    DATA_PROCESSING = "data_processing"


@dataclass
class ToolSchema:
    """Input/output schema for a tool."""
    input_type: dict  # JSON schema
    output_type: dict  # JSON schema
    required_params: list[str] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """Definition of a tool available to agents."""
    name: str
    description: str
    category: ToolCategory
    schema: ToolSchema
    allowed_specialists: list[str]  # e.g., ["research", "data_analysis"]
    rate_limit_per_minute: Optional[int] = None
    cost_per_call: float = 0.0  # For tracking expenses
    requires_api_key: bool = False


@dataclass
class ToolInvocation:
    """Log entry for a tool invocation."""
    tool_name: str
    specialist_id: str
    task_id: str
    timestamp: datetime
    inputs: dict
    outputs: Optional[dict]
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0


class ToolRegistry:
    """
    Singleton registry of available tools.
    
    Manages:
    - Tool definitions and schemas
    - Specialist access control
    - Rate limiting
    - Invocation logging
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}
        self.invocation_log: list[ToolInvocation] = []
        self._initialize_default_tools()
    
    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _initialize_default_tools(self) -> None:
        """Initialize the default tool set."""
        
        # Web Search Tool
        self.register_tool(
            name="web_search",
            description="Search the web for information, facts, and current data",
            category=ToolCategory.WEB_SEARCH,
            schema=ToolSchema(
                input_type={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "description": "Maximum results to return", "default": 5},
                    },
                    "required": ["query"],
                },
                output_type={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"},
                        },
                    },
                },
                required_params=["query"],
            ),
            allowed_specialists=["research", "general"],
            rate_limit_per_minute=20,
            cost_per_call=0.0,
        )
        
        # File Read Tool
        self.register_tool(
            name="read_file",
            description="Read contents of a file from the filesystem",
            category=ToolCategory.FILE_OPS,
            schema=ToolSchema(
                input_type={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to read"},
                    },
                    "required": ["file_path"],
                },
                output_type={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "file_size": {"type": "integer"},
                    },
                },
                required_params=["file_path"],
            ),
            allowed_specialists=["research", "data_analysis", "general"],
            rate_limit_per_minute=50,
            cost_per_call=0.0,
        )
        
        # File Write Tool
        self.register_tool(
            name="write_file",
            description="Write content to a file",
            category=ToolCategory.FILE_OPS,
            schema=ToolSchema(
                input_type={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to write"},
                        "content": {"type": "string", "description": "Content to write"},
                        "mode": {"type": "string", "enum": ["w", "a"], "description": "Write or append"},
                    },
                    "required": ["file_path", "content"],
                },
                output_type={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "file_path": {"type": "string"},
                    },
                },
                required_params=["file_path", "content"],
            ),
            allowed_specialists=["writing", "code_execution", "general"],
            rate_limit_per_minute=20,
            cost_per_call=0.0,
        )
        
        # Code Execution Tool
        self.register_tool(
            name="execute_python",
            description="Execute Python code in a sandboxed environment",
            category=ToolCategory.CODE_EXECUTION,
            schema=ToolSchema(
                input_type={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to execute"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                    },
                    "required": ["code"],
                },
                output_type={
                    "type": "object",
                    "properties": {
                        "stdout": {"type": "string"},
                        "stderr": {"type": "string"},
                        "return_value": {"type": "string"},
                        "execution_time_ms": {"type": "number"},
                    },
                },
                required_params=["code"],
            ),
            allowed_specialists=["code_execution", "data_analysis"],
            rate_limit_per_minute=10,
            cost_per_call=0.1,
        )
        
        # Database Query Tool
        self.register_tool(
            name="query_database",
            description="Execute SQL queries against a database",
            category=ToolCategory.DATABASE,
            schema=ToolSchema(
                input_type={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query"},
                        "database": {"type": "string", "description": "Database name"},
                    },
                    "required": ["query"],
                },
                output_type={
                    "type": "object",
                    "properties": {
                        "rows": {"type": "array"},
                        "row_count": {"type": "integer"},
                    },
                },
                required_params=["query"],
            ),
            allowed_specialists=["data_analysis"],
            rate_limit_per_minute=30,
            cost_per_call=0.05,
            requires_api_key=True,
        )
        
        # API Call Tool
        self.register_tool(
            name="api_call",
            description="Make HTTP requests to external APIs",
            category=ToolCategory.API_CALL,
            schema=ToolSchema(
                input_type={
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                        "url": {"type": "string"},
                        "params": {"type": "object"},
                        "headers": {"type": "object"},
                    },
                    "required": ["method", "url"],
                },
                output_type={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "data": {"type": "object"},
                    },
                },
                required_params=["method", "url"],
            ),
            allowed_specialists=["research", "data_analysis"],
            rate_limit_per_minute=20,
            cost_per_call=0.0,
        )
    
    def register_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        schema: ToolSchema,
        allowed_specialists: list[str],
        rate_limit_per_minute: Optional[int] = None,
        cost_per_call: float = 0.0,
        requires_api_key: bool = False,
    ) -> None:
        """Register a new tool."""
        tool = ToolDefinition(
            name=name,
            description=description,
            category=category,
            schema=schema,
            allowed_specialists=allowed_specialists,
            rate_limit_per_minute=rate_limit_per_minute,
            cost_per_call=cost_per_call,
            requires_api_key=requires_api_key,
        )
        self.tools[name] = tool
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_tools_for_specialist(self, specialist_type: str) -> list[ToolDefinition]:
        """Get all tools available to a specialist type."""
        return [
            tool for tool in self.tools.values()
            if specialist_type in tool.allowed_specialists
        ]
    
    def list_all_tools(self) -> list[ToolDefinition]:
        """List all registered tools."""
        return list(self.tools.values())
    
    def log_invocation(
        self,
        tool_name: str,
        specialist_id: str,
        task_id: str,
        inputs: dict,
        outputs: Optional[dict] = None,
        execution_time_ms: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        tokens_used: int = 0,
    ) -> None:
        """Log a tool invocation."""
        tool = self.get_tool(tool_name)
        cost = (tool.cost_per_call if tool else 0.0)
        
        invocation = ToolInvocation(
            tool_name=tool_name,
            specialist_id=specialist_id,
            task_id=task_id,
            timestamp=datetime.now(),
            inputs=inputs,
            outputs=outputs,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            tokens_used=tokens_used,
            cost=cost,
        )
        self.invocation_log.append(invocation)
    
    def get_invocation_log(self, tool_name: Optional[str] = None, specialist_id: Optional[str] = None) -> list[ToolInvocation]:
        """Get invocation logs, optionally filtered."""
        logs = self.invocation_log
        
        if tool_name:
            logs = [l for l in logs if l.tool_name == tool_name]
        if specialist_id:
            logs = [l for l in logs if l.specialist_id == specialist_id]
        
        return logs
    
    def get_tool_stats(self, tool_name: str) -> dict:
        """Get usage statistics for a tool."""
        logs = self.get_invocation_log(tool_name=tool_name)
        
        if not logs:
            return {}
        
        successful = [l for l in logs if l.success]
        failed = [l for l in logs if not l.success]
        
        return {
            "tool_name": tool_name,
            "total_calls": len(logs),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(logs) if logs else 0.0,
            "avg_execution_time_ms": sum(l.execution_time_ms for l in logs) / len(logs) if logs else 0.0,
            "total_tokens": sum(l.tokens_used for l in logs),
            "total_cost": sum(l.cost for l in logs),
        }
