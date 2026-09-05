"""
Long-term semantic memory using ChromaDB.

Stores learnings from past tasks:
- What was asked (original request)
- What approach worked (plan, tools used)
- Key findings and domain facts
- User preferences observed
- Success metrics (confidence, cost, duration)

Embeds using OpenAI embeddings and retrieves similar memories
for injection into supervisor planning.
"""

import chromadb
from chromadb.config import Settings
import json
from typing import Any, Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib
from pathlib import Path


@dataclass
class Memory:
    """A single memory stored in ChromaDB."""
    memory_id: str  # Unique ID for this memory
    task_id: str  # Original task ID
    request: str  # Original user request
    plan_summary: str  # Summary of the plan created
    tools_used: List[str]  # Tools that were used
    domain_facts: List[str]  # Key facts discovered
    user_preferences: Dict[str, Any]  # User-specific preferences observed
    success_score: float  # 0.0-1.0, based on confidence and outcome
    cost: float  # Task cost
    duration_seconds: float  # Execution time
    timestamp: str  # When this task ran
    tags: List[str] = None  # Custom tags for filtering
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class LongTermMemory:
    """
    Long-term semantic memory backed by ChromaDB.
    
    Stores task learnings with embeddings for semantic retrieval.
    """
    
    def __init__(self, persist_dir: str = "./data/chromadb", model_name: str = "default"):
        """
        Initialize ChromaDB collection.
        
        Args:
            persist_dir: Directory for persistent storage
            model_name: Embedding model (default uses ChromaDB's default)
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB with persistence
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self.persist_dir),
            anonymized_telemetry=False,
        )
        
        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection(
            name="task_memories",
            metadata={"description": "Long-term semantic memory of task executions"},
        )
    
    def _generate_memory_id(self, task_id: str) -> str:
        """Generate a unique memory ID."""
        return hashlib.sha256(f"{task_id}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    
    async def store_memory(self, memory: Memory, min_success_score: float = 0.6) -> Optional[str]:
        """
        Store a task memory if it meets quality threshold.
        
        Args:
            memory: Memory to store
            min_success_score: Minimum success score to store (avoid noise)
            
        Returns:
            Memory ID if stored, None if filtered out
        """
        # Filter out low-quality memories
        if memory.success_score < min_success_score:
            return None
        
        # Create embedding-ready text
        embedding_text = self._create_embedding_text(memory)
        
        # Store in ChromaDB
        self.collection.add(
            ids=[memory.memory_id],
            documents=[embedding_text],
            metadatas=[{
                "task_id": memory.task_id,
                "request_preview": memory.request[:100],
                "success_score": memory.success_score,
                "cost": memory.cost,
                "duration": memory.duration_seconds,
                "timestamp": memory.timestamp,
            }],
            documents_embeddings=None,  # Let ChromaDB generate embeddings
        )
        
        return memory.memory_id
    
    def _create_embedding_text(self, memory: Memory) -> str:
        """Create embedding-ready text from a memory."""
        text_parts = [
            f"Request: {memory.request}",
            f"Plan: {memory.plan_summary}",
            f"Tools: {', '.join(memory.tools_used)}",
            f"Facts: {'; '.join(memory.domain_facts)}",
            f"Preferences: {json.dumps(memory.user_preferences)}",
        ]
        return "\n".join(text_parts)
    
    async def retrieve_similar_memories(
        self,
        query: str,
        n_results: int = 5,
        min_relevance: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar memories for a query.
        
        Args:
            query: Query string (the new task request)
            n_results: Number of results to retrieve
            min_relevance: Minimum relevance score (0.0-1.0)
            
        Returns:
            List of relevant memories with relevance scores
        """
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        
        # Parse results
        memories = []
        if results and results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                
                # Convert distance to relevance score (lower distance = higher relevance)
                relevance = 1.0 / (1.0 + distance)
                
                if relevance >= min_relevance:
                    memories.append({
                        "memory_id": memory_id,
                        "relevance": relevance,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "text": results["documents"][0][i] if results["documents"] else "",
                    })
        
        return sorted(memories, key=lambda x: x["relevance"], reverse=True)
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[Dict]:
        """Get a specific memory by ID."""
        results = self.collection.get(
            ids=[memory_id],
            include=["documents", "metadatas", "distances"]
        )
        
        if results and results["ids"]:
            return {
                "memory_id": results["ids"][0],
                "text": results["documents"][0] if results["documents"] else "",
                "metadata": results["metadatas"][0] if results["metadatas"] else {},
            }
        
        return None
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False
    
    async def delete_memories_by_task_id(self, task_id: str) -> int:
        """Delete all memories for a specific task."""
        # Query for all memories from this task
        results = self.collection.get(
            where={"task_id": {"$eq": task_id}},
            include=[]
        )
        
        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])
        
        return 0
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory collection."""
        # Count total memories
        results = self.collection.get(include=[])
        total_count = len(results["ids"]) if results["ids"] else 0
        
        # Get metadata for aggregation
        metadatas = results.get("metadatas", []) if results else []
        
        if metadatas:
            avg_success = sum(m.get("success_score", 0) for m in metadatas) / len(metadatas)
            total_cost = sum(m.get("cost", 0) for m in metadatas)
            avg_duration = sum(m.get("duration", 0) for m in metadatas) / len(metadatas)
        else:
            avg_success = total_cost = avg_duration = 0
        
        return {
            "total_memories": total_count,
            "average_success_score": avg_success,
            "total_cost_tracked": total_cost,
            "average_duration_seconds": avg_duration,
        }
    
    async def consolidate_memories(self, similarity_threshold: float = 0.85) -> int:
        """
        Consolidate very similar memories to reduce bloat.
        
        Args:
            similarity_threshold: Merge memories above this similarity
            
        Returns:
            Number of memories deleted during consolidation
        """
        # Get all memories
        results = self.collection.get(include=["documents"])
        
        if not results or not results["ids"]:
            return 0
        
        # Find and merge similar memories
        deleted_count = 0
        processed = set()
        
        for i, memory_id in enumerate(results["ids"]):
            if memory_id in processed:
                continue
            
            document = results["documents"][i] if results["documents"] else ""
            
            # Query for similar memories
            similar = await self.retrieve_similar_memories(
                query=document,
                n_results=10,
                min_relevance=similarity_threshold,
            )
            
            # Keep only the best one, mark others for deletion
            for j, sim_mem in enumerate(similar[1:]):  # Skip first (itself)
                sim_id = sim_mem["memory_id"]
                if sim_id not in processed and sim_id != memory_id:
                    await self.delete_memory(sim_id)
                    processed.add(sim_id)
                    deleted_count += 1
            
            processed.add(memory_id)
        
        return deleted_count
    
    async def expire_old_memories(self, days: int = 30) -> int:
        """
        Delete memories older than N days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of memories deleted
        """
        from datetime import datetime, timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Query for old memories
        results = self.collection.get(
            where={"timestamp": {"$lt": cutoff_date}},
        )
        
        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])
        
        return 0
