# Phase 2 Quick Reference

## Memory System Overview

Phase 2 adds persistent memory to the agent system, enabling:
- **Learning**: Tasks store learnings in long-term memory
- **Reuse**: Similar tasks benefit from past experience
- **Efficiency**: Better plans reduce redundant work
- **Compliance**: GDPR-ready deletion

## Architecture

```
Short-term (Redis)
  ↓
  └─ Task context, intermediate results
  └─ TTL: 1 hour
  └─ Cleared on task completion

Long-term (ChromaDB)
  ↓
  └─ Task learnings with embeddings
  └─ Semantic retrieval by relevance
  └─ Importance-based retention
  └─ Consolidation & expiration
```

## Components

| Component | Purpose |
|-----------|---------|
| `ShortTermMemory` | Redis task context |
| `LongTermMemory` | ChromaDB embeddings |
| `MemoryRetriever` | Semantic search + injection |
| `MemoryManager` | Consolidation, expiration, GDPR |
| `MemoryAPI` | High-level operations |

## Running Phase 2 Demo

### Prerequisites

```bash
# Redis (local or Docker)
docker run -p 6379:6379 redis

# Python packages
pip install -r requirements.txt
```

### Execute

```bash
python demo_phase2.py
```

### What to Expect

1. Memory system initializes
2. Task 1: Runs without memory
3. Task 1: Stored to ChromaDB
4. Task 2: Similar task
5. Task 2: Retrieves Task 1 memories
6. Task 2: Memory improves planning (+5-10% confidence)
7. Consolidation & expiration tests
8. GDPR deletion verified
9. ✓ Phase 2 checkpoint passed

## Key Metrics

| Metric | Expected |
|--------|----------|
| Memory retrieval latency | <100ms |
| Plan confidence improvement | +5-10% |
| Consolidation ratio | <10% duplication |
| GDPR deletion | 100% removal |

## Memory Storage

```python
# Record a task after completion
await api.record_task_completion(
    task_id="abc123",
    request="Research AI trends",
    plan_summary="Market analysis",
    tools_used=["web_search", "analyze"],
    domain_facts=["AI adoption growing"],
    success_score=0.87,
    cost=2.50,
    duration_seconds=180,
)
```

## Memory Retrieval

```python
# Get memories for new task
results = await api.retrieve_for_planning(
    request="Analyze AI capabilities",
    n_results=3,
    min_relevance=0.5,
)

# Use in planning
for mem in results['retrieved_memories']:
    print(f"Similar task (relevance: {mem['relevance']:.0%})")
```

## Memory Cleanup

```python
# Consolidate (merge similar memories)
await api.consolidate(dry_run=True)

# Expire old (remove by age + importance)
await api.expire_old(importance_level="low", dry_run=True)

# GDPR deletion
await api.delete_user_memories(user_id="user@example.com")
```

## Integration

Phase 2 is backward compatible:

```python
# Phase 1 mode (no memory)
orch = AgentOrchestrator()

# Phase 2 mode (with memory)
api, short_term, long_term, retriever = await MemoryFactory.create_memory_system()
orch = AgentOrchestrator(memory_api=api, planning_with_memory=planning)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Redis error | `docker run -p 6379:6379 redis` |
| ChromaDB error | `mkdir -p ./data/chromadb` |
| Memory not used | Check `orchestrator.use_memory` flag |

## Next Phase

Phase 3 adds human-in-the-loop:
- Escalation triggers
- Approval queue
- Review interface
- Granular approval levels
