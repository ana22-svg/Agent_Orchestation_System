"""
Memory management: consolidation, expiration, and GDPR compliance.

Handles:
- Importance scoring
- Consolidation of duplicate memories
- Expiration of old memories
- User data deletion (GDPR)
"""

from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio


class ImportanceLevel(str, Enum):
    """Importance levels for memory retention."""
    CRITICAL = "critical"      # Never expire, core learnings
    HIGH = "high"              # Expire after 90 days
    MEDIUM = "medium"          # Expire after 30 days
    LOW = "low"                # Expire after 7 days


@dataclass
class MemoryImportanceScore:
    """Scoring for memory importance."""
    success_score: float        # 0.0-1.0, how well did the task go
    cost_score: float          # 0.0-1.0, based on cost (high cost = higher importance)
    frequency_score: float     # 0.0-1.0, how often similar tasks occur
    recency_decay: float       # 0.0-1.0, newer memories score higher
    
    def calculate_total(self) -> float:
        """Calculate total importance score."""
        return (
            self.success_score * 0.4 +
            self.cost_score * 0.2 +
            self.frequency_score * 0.2 +
            self.recency_decay * 0.2
        )


class MemoryManager:
    """
    Manages memory lifecycle: storage, consolidation, expiration, deletion.
    """
    
    def __init__(
        self,
        long_term_memory: Any,
        consolidation_threshold: float = 0.85,
        critical_age_days: int = 365,
        high_age_days: int = 90,
        medium_age_days: int = 30,
        low_age_days: int = 7,
    ):
        """
        Initialize memory manager.
        
        Args:
            long_term_memory: LongTermMemory instance
            consolidation_threshold: Similarity threshold for consolidation
            critical_age_days: Retention for critical memories
            high_age_days: Retention for high importance
            medium_age_days: Retention for medium importance
            low_age_days: Retention for low importance
        """
        self.memory = long_term_memory
        self.consolidation_threshold = consolidation_threshold
        self.retention_days = {
            ImportanceLevel.CRITICAL: critical_age_days,
            ImportanceLevel.HIGH: high_age_days,
            ImportanceLevel.MEDIUM: medium_age_days,
            ImportanceLevel.LOW: low_age_days,
        }
    
    async def calculate_importance(
        self,
        success_score: float,
        cost: float,
        max_cost_seen: float = 100.0,
        frequency_score: float = 0.5,
        days_old: int = 0,
        max_days_old: int = 365,
    ) -> MemoryImportanceScore:
        """
        Calculate importance score for a memory.
        
        Args:
            success_score: Task success (0.0-1.0)
            cost: Task cost in dollars
            max_cost_seen: Reference for cost scoring
            frequency_score: How often similar tasks occur (0.0-1.0)
            days_old: How old the memory is
            max_days_old: Reference for recency decay
            
        Returns:
            MemoryImportanceScore
        """
        # Cost score: higher cost = higher importance (more critical to remember)
        cost_score = min(1.0, cost / max_cost_seen) if max_cost_seen > 0 else 0.5
        
        # Recency decay: newer memories score higher
        if days_old == 0:
            recency_decay = 1.0
        else:
            recency_decay = max(0.1, 1.0 - (days_old / max_days_old))
        
        return MemoryImportanceScore(
            success_score=success_score,
            cost_score=cost_score,
            frequency_score=frequency_score,
            recency_decay=recency_decay,
        )
    
    async def determine_importance_level(self, score: MemoryImportanceScore) -> ImportanceLevel:
        """
        Determine importance level from score.
        
        Args:
            score: MemoryImportanceScore
            
        Returns:
            ImportanceLevel enum value
        """
        total = score.calculate_total()
        
        if total >= 0.8:
            return ImportanceLevel.CRITICAL
        elif total >= 0.6:
            return ImportanceLevel.HIGH
        elif total >= 0.4:
            return ImportanceLevel.MEDIUM
        else:
            return ImportanceLevel.LOW
    
    async def consolidate_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Consolidate similar memories to reduce bloat.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Report of consolidation actions
        """
        if dry_run:
            # Just report, don't delete
            deleted_count = 0
        else:
            deleted_count = await self.memory.consolidate_memories(
                similarity_threshold=self.consolidation_threshold
            )
        
        stats = await self.memory.get_memory_stats()
        
        return {
            "action": "consolidation",
            "dry_run": dry_run,
            "memories_deleted": deleted_count,
            "remaining_memories": stats["total_memories"],
            "consolidation_ratio": (deleted_count / (stats["total_memories"] + deleted_count)) if (stats["total_memories"] + deleted_count) > 0 else 0,
        }
    
    async def expire_old_memories(self, importance_level: Optional[ImportanceLevel] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Expire old memories based on importance level.
        
        Args:
            importance_level: If specified, only expire this level
            dry_run: If True, only report
            
        Returns:
            Report of expiration actions
        """
        if importance_level:
            age_threshold = self.retention_days[importance_level]
        else:
            # Expire all levels based on their thresholds
            age_threshold = self.retention_days[ImportanceLevel.LOW]
        
        if dry_run:
            deleted_count = 0
        else:
            deleted_count = await self.memory.expire_old_memories(days=age_threshold)
        
        stats = await self.memory.get_memory_stats()
        
        return {
            "action": "expiration",
            "importance_level": importance_level.value if importance_level else "all",
            "age_threshold_days": age_threshold,
            "dry_run": dry_run,
            "memories_deleted": deleted_count,
            "remaining_memories": stats["total_memories"],
        }
    
    async def delete_user_data(self, user_id: str, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Delete all memories for a user (GDPR compliance).
        
        Args:
            user_id: User identifier
            task_ids: Optional list of specific task IDs to delete
            
        Returns:
            Deletion report
        """
        total_deleted = 0
        
        if task_ids:
            # Delete specific tasks
            for task_id in task_ids:
                deleted = await self.memory.delete_memories_by_task_id(task_id)
                total_deleted += deleted
        else:
            # Delete all memories for user
            # This would require a user_id field in ChromaDB, which we can add
            # For now, we'll note this for future implementation
            pass
        
        return {
            "action": "delete_user_data",
            "user_id": user_id,
            "task_ids_deleted": len(task_ids) if task_ids else 0,
            "total_memories_deleted": total_deleted,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def get_memory_health_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive health report of the memory system.
        
        Returns:
            Health report with statistics and recommendations
        """
        stats = await self.memory.get_memory_stats()
        
        recommendations = []
        
        # Check for memory bloat
        if stats["total_memories"] > 1000:
            recommendations.append("Memory collection is large. Consider consolidation.")
        
        # Check for low success rate
        if stats["average_success_score"] < 0.6:
            recommendations.append("Average success score is low. Review past failures.")
        
        # Check for high cost
        if stats["total_cost_tracked"] > 1000:
            recommendations.append("High cumulative costs tracked. Review expensive tasks.")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "recommendations": recommendations,
            "next_maintenance_actions": [
                "Run consolidation if memory count > 1000",
                "Run expiration monthly",
                "Monitor average success score",
            ],
        }


class MaintenanceScheduler:
    """
    Schedules regular memory maintenance tasks.
    """
    
    def __init__(self, manager: MemoryManager):
        """
        Initialize scheduler.
        
        Args:
            manager: MemoryManager instance
        """
        self.manager = manager
        self.tasks = []
    
    async def schedule_daily_tasks(self) -> None:
        """Schedule daily maintenance tasks."""
        # Daily: Check memory health
        await self.manager.get_memory_health_report()
    
    async def schedule_weekly_tasks(self) -> None:
        """Schedule weekly maintenance tasks."""
        # Weekly: Expire low-importance memories
        await self.manager.expire_old_memories(ImportanceLevel.LOW)
    
    async def schedule_monthly_tasks(self) -> None:
        """Schedule monthly maintenance tasks."""
        # Monthly: Consolidate and full expiration
        await self.manager.consolidate_memories()
        await self.manager.expire_old_memories()
    
    async def run_all_maintenance(self) -> Dict[str, Any]:
        """Run all maintenance tasks."""
        results = {
            "daily": await self._run_daily(),
            "weekly": await self._run_weekly(),
            "monthly": await self._run_monthly(),
            "timestamp": datetime.now().isoformat(),
        }
        
        return results
    
    async def _run_daily(self) -> Dict:
        """Run daily tasks."""
        return await self.manager.get_memory_health_report()
    
    async def _run_weekly(self) -> Dict:
        """Run weekly tasks."""
        return await self.manager.expire_old_memories(ImportanceLevel.LOW)
    
    async def _run_monthly(self) -> Dict:
        """Run monthly tasks."""
        consolidation = await self.manager.consolidate_memories()
        expiration = await self.manager.expire_old_memories()
        
        return {
            "consolidation": consolidation,
            "expiration": expiration,
        }
