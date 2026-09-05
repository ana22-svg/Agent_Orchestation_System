"""
Memory API endpoints for managing and querying memory.

Provides:
- Store task memory after execution
- Retrieve relevant past experience
- Delete user data (GDPR)
- Memory statistics and health
- Maintenance operations
"""

from typing import Any, Optional, Dict, List
from datetime import datetime
from .short_term import ShortTermMemory
from .long_term import LongTermMemory, Memory
from .retrieval import MemoryRetriever, PlanningWithMemory
from .management import MemoryManager, MaintenanceScheduler, ImportanceLevel


class MemoryAPI:
    """
    High-level API for memory operations.
    """
    
    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        retriever: MemoryRetriever,
        manager: MemoryManager,
    ):
        """
        Initialize memory API.
        
        Args:
            short_term: Short-term memory instance
            long_term: Long-term memory instance
            retriever: Memory retriever instance
            manager: Memory manager instance
        """
        self.short_term = short_term
        self.long_term = long_term
        self.retriever = retriever
        self.manager = manager
    
    async def record_task_completion(
        self,
        task_id: str,
        request: str,
        plan_summary: str,
        tools_used: List[str],
        domain_facts: List[str],
        success_score: float,
        cost: float,
        duration_seconds: float,
        user_preferences: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Record a completed task to long-term memory.
        
        Args:
            task_id: Task ID
            request: Original user request
            plan_summary: Summary of plan created
            tools_used: Tools that were used
            domain_facts: Key facts discovered
            success_score: Success score (0.0-1.0)
            cost: Task cost
            duration_seconds: Execution duration
            user_preferences: User preferences observed
            
        Returns:
            Recording result
        """
        # Create memory object
        memory = Memory(
            memory_id=self.long_term._generate_memory_id(task_id),
            task_id=task_id,
            request=request,
            plan_summary=plan_summary,
            tools_used=tools_used,
            domain_facts=domain_facts,
            user_preferences=user_preferences or {},
            success_score=success_score,
            cost=cost,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat(),
        )
        
        # Calculate importance
        importance_score = await self.manager.calculate_importance(
            success_score=success_score,
            cost=cost,
            frequency_score=0.5,  # Default, could be updated
        )
        
        importance_level = await self.manager.determine_importance_level(importance_score)
        memory.tags.append(f"importance:{importance_level.value}")
        
        # Store in long-term memory
        memory_id = await self.long_term.store_memory(memory)
        
        # Clear short-term memory for this task
        await self.short_term.clear_task_memory(task_id)
        
        return {
            "status": "stored" if memory_id else "filtered",
            "memory_id": memory_id,
            "reason": "Stored in long-term memory" if memory_id else "Filtered out (low success score)",
            "importance_level": importance_level.value,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def retrieve_for_planning(
        self,
        request: str,
        n_results: int = 3,
        min_relevance: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant memories for planning a new task.
        
        Args:
            request: New task request
            n_results: Number of memories to retrieve
            min_relevance: Minimum relevance threshold
            
        Returns:
            Retrieval results
        """
        context = await self.retriever.retrieve_relevant_context(
            request=request,
            n_memories=n_results,
            min_relevance=min_relevance,
        )
        
        return {
            "request": request,
            "memories_found": context["memories_found"],
            "retrieved_memories": context["retrieved_memories"],
            "insights": context["insights"],
            "recommendation": context["recommendation"],
            "formatted_for_prompt": self.retriever.format_for_prompt(context),
        }
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory collection statistics."""
        return await self.long_term.get_memory_stats()
    
    async def delete_memory_by_id(self, memory_id: str) -> Dict[str, Any]:
        """
        Delete a specific memory.
        
        Args:
            memory_id: Memory to delete
            
        Returns:
            Deletion result
        """
        success = await self.long_term.delete_memory(memory_id)
        
        return {
            "memory_id": memory_id,
            "deleted": success,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def delete_user_memories(
        self,
        user_id: str,
        task_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Delete all memories for a user (GDPR).
        
        Args:
            user_id: User identifier
            task_ids: Optional specific task IDs
            
        Returns:
            Deletion report
        """
        return await self.manager.delete_user_data(user_id, task_ids)
    
    async def consolidate(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Consolidate memories.
        
        Args:
            dry_run: If True, only report
            
        Returns:
            Consolidation report
        """
        return await self.manager.consolidate_memories(dry_run=dry_run)
    
    async def expire_old(
        self,
        importance_level: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Expire old memories.
        
        Args:
            importance_level: Optional level to expire
            dry_run: If True, only report
            
        Returns:
            Expiration report
        """
        level = ImportanceLevel(importance_level) if importance_level else None
        return await self.manager.expire_old_memories(level, dry_run=dry_run)
    
    async def get_health_report(self) -> Dict[str, Any]:
        """Get memory system health report."""
        return await self.manager.get_memory_health_report()


class MemoryFactory:
    """
    Factory for creating and initializing the complete memory system.
    """
    
    @staticmethod
    async def create_memory_system(
        redis_url: str = "redis://localhost:6379",
        chromadb_dir: str = "./data/chromadb",
        decomposition_engine: Optional[Any] = None,
    ) -> tuple[MemoryAPI, ShortTermMemory, LongTermMemory, MemoryRetriever]:
        """
        Create a complete memory system.
        
        Args:
            redis_url: Redis connection URL
            chromadb_dir: ChromaDB persistence directory
            decomposition_engine: Optional task decomposition engine
            
        Returns:
            (memory_api, short_term, long_term, retriever)
        """
        # Initialize components
        short_term = ShortTermMemory(redis_url=redis_url)
        long_term = LongTermMemory(persist_dir=chromadb_dir)
        retriever = MemoryRetriever(long_term)
        manager = MemoryManager(long_term)
        
        # Create API
        api = MemoryAPI(short_term, long_term, retriever, manager)
        
        return api, short_term, long_term, retriever
