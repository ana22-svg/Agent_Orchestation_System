"""
Short-term working memory using Redis.

Stores:
- Current task context
- Completed subtask outputs
- Intermediate results
- Error logs
- Execution metadata

Scoped to one task and cleared on completion.
"""

import json
import redis
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import asyncio

class ShortTermMemory:
    """
    Short-term working memory backed by Redis.
    
    Stores task execution state that needs to persist
    across agent calls within a single task.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Redis connection URL
            db: Redis database number
        """
        self.redis_url = redis_url
        self.db = db
        self._client = None
    
    def _get_client(self) -> redis.Redis:
        """Get or create Redis client (lazy init)."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, db=self.db, decode_responses=True)
        return self._client
    
    def _task_key(self, task_id: str, prefix: str) -> str:
        """Generate a namespaced Redis key."""
        return f"task:{task_id}:{prefix}"
    
    async def set_task_context(self, task_id: str, context: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        """
        Store task context.
        
        Args:
            task_id: Task identifier
            context: Context dictionary (plan, request, metadata)
            ttl_seconds: Time to live (default 1 hour)
        """
        client = self._get_client()
        key = self._task_key(task_id, "context")
        value = json.dumps(context, default=str)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, client.setex, key, ttl_seconds, value)
    
    async def get_task_context(self, task_id: str) -> Optional[Dict]:
        """Get task context."""
        client = self._get_client()
        key = self._task_key(task_id, "context")
        
        loop = asyncio.get_event_loop()
        value = await loop.run_in_executor(None, client.get, key)
        
        return json.loads(value) if value else None
    
    async def store_subtask_result(self, task_id: str, subtask_id: str, result: Dict[str, Any]) -> None:
        """
        Store the result of a completed subtask.
        
        Args:
            task_id: Parent task ID
            subtask_id: Subtask identifier
            result: The subtask result
        """
        client = self._get_client()
        key = self._task_key(task_id, f"subtask:{subtask_id}")
        value = json.dumps(result, default=str)
        
        # Store with 1-hour TTL
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, client.setex, key, 3600, value)
    
    async def get_subtask_result(self, task_id: str, subtask_id: str) -> Optional[Dict]:
        """Get a subtask result."""
        client = self._get_client()
        key = self._task_key(task_id, f"subtask:{subtask_id}")
        
        loop = asyncio.get_event_loop()
        value = await loop.run_in_executor(None, client.get, key)
        
        return json.loads(value) if value else None
    
    async def get_all_subtask_results(self, task_id: str) -> Dict[str, Dict]:
        """Get all completed subtask results for a task."""
        client = self._get_client()
        pattern = self._task_key(task_id, "subtask:*")
        
        loop = asyncio.get_event_loop()
        keys = await loop.run_in_executor(None, client.keys, pattern)
        
        results = {}
        for key in keys:
            value = await loop.run_in_executor(None, client.get, key)
            if value:
                subtask_id = key.split(":")[-1]
                results[subtask_id] = json.loads(value)
        
        return results
    
    async def log_error(self, task_id: str, error: Dict[str, Any]) -> None:
        """
        Log an error during task execution.
        
        Args:
            task_id: Task ID
            error: Error details (message, timestamp, node, etc.)
        """
        client = self._get_client()
        key = self._task_key(task_id, "errors")
        value = json.dumps(error, default=str)
        
        # Append to Redis list
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, client.rpush, key, value)
        
        # Set expiration on the list
        await loop.run_in_executor(None, client.expire, key, 3600)
    
    async def get_errors(self, task_id: str) -> list[Dict]:
        """Get all errors logged for a task."""
        client = self._get_client()
        key = self._task_key(task_id, "errors")
        
        loop = asyncio.get_event_loop()
        error_strings = await loop.run_in_executor(None, client.lrange, key, 0, -1)
        
        return [json.loads(e) for e in error_strings]
    
    async def store_intermediate_result(self, task_id: str, step_name: str, result: Any) -> None:
        """
        Store an intermediate result during task execution.
        
        Args:
            task_id: Task ID
            step_name: Name of the step
            result: The intermediate result
        """
        client = self._get_client()
        key = self._task_key(task_id, f"intermediate:{step_name}")
        value = json.dumps(result, default=str)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, client.setex, key, 3600, value)
    
    async def get_intermediate_result(self, task_id: str, step_name: str) -> Optional[Any]:
        """Get an intermediate result."""
        client = self._get_client()
        key = self._task_key(task_id, f"intermediate:{step_name}")
        
        loop = asyncio.get_event_loop()
        value = await loop.run_in_executor(None, client.get, key)
        
        return json.loads(value) if value else None
    
    async def clear_task_memory(self, task_id: str) -> None:
        """
        Clear all memory for a task (cleanup on completion).
        
        Args:
            task_id: Task ID to clear
        """
        client = self._get_client()
        pattern = self._task_key(task_id, "*")
        
        loop = asyncio.get_event_loop()
        keys = await loop.run_in_executor(None, client.keys, pattern)
        
        if keys:
            await loop.run_in_executor(None, client.delete, *keys)
    
    async def health_check(self) -> bool:
        """Check if Redis is accessible."""
        try:
            client = self._get_client()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, client.ping)
            return result
        except Exception:
            return False
