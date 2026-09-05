# Agent Orchestration System — Phase 1: Agent Architecture

A multi-agent orchestration platform built with Python 3.11+, LangGraph, and multi-model LLM support (OpenAI + Anthropic).

## Phase 5: Integration and Testing

The project includes a Docker Compose runtime for the application, Redis short-term memory, and ChromaDB long-term memory:

```bash
docker compose up --build
```

Tenant API-key authentication and task ownership checks are provided by `core/security.py`. Run the dependency-light regression and integration suite with:

```bash
python -m pytest -q
```

## Phase 1: Core Agent Architecture

Phase 1 implements the foundational infrastructure for autonomous AI agent workflows:

### Three-Layer Agent Hierarchy

```
┌─────────────────────────────────────────────────┐
│           SUPERVISOR AGENT                       │
│  • Decomposes complex requests into subtasks    │
│  • Creates structured task plans with           │
│    dependencies and assignments                 │
│  • Manages execution flow and retries           │
└─────────────────────────────────────────────────┘
                       ↓
        ┌──────────────┬──────────────┐
        ↓              ↓              ↓
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │Research │  │  Data   │  │ Writing │  ← SPECIALIST AGENTS
   │Specialist  Analysis │  │Specialist  • Use domain-specific tools
   │         │  │Specialist  │         │  • Execute assigned subtasks
   │         │  │         │  │         │  • Return structured output
   └─────────┘  └─────────┘  └─────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│           REVIEWER AGENT                         │
│  • Validates specialist output                  │
│  • Checks against expected schemas              │
│  • Flags errors for rework or escalation        │
└─────────────────────────────────────────────────┘
```

### Workflow State Machine

```
intake
  ↓
planning (create decomposed task plan)
  ↓
[confidence check] → escalate (if low) or specialist_execution
  ↓
specialist_execution (run subtasks in parallel/sequential)
  ↓
review (validate outputs)
  ↓
[quality check] → rework (send back to specialist) or synthesis
  ↓
synthesis (combine results)
  ↓
deliver (prepare final output)
  ↓
END
```

## Project Structure

```
Agent Orchestration System/
├── core/                          # Core agent system
│   ├── __init__.py
│   ├── agents.py                  # Agent base classes & implementations
│   │   ├── Agent (base)
│   │   ├── Supervisor
│   │   ├── Specialist (research, data_analysis, writing, code_execution)
│   │   └── Reviewer
│   ├── task_decomposition.py      # Request → task plan conversion
│   │   ├── TaskDecompositionEngine
│   │   ├── TaskPlan (data model)
│   │   └── Subtask (data model)
│   ├── tool_registry.py           # Tool definitions & usage logging
│   │   ├── ToolRegistry (singleton)
│   │   ├── ToolDefinition
│   │   └── ToolInvocation (logging)
│   └── orchestration.py           # LangGraph state machine
│       ├── AgentOrchestrator
│       └── ExecutionState
├── config.py                      # Configuration management
├── demo.py                        # Phase 1 demo script
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment configuration template
└── README.md                      # This file
```

## Key Components

### 1. Agents (`core/agents.py`)

- **Supervisor**: Breaks down complex requests using the decomposition engine; tracks confidence; routes to appropriate specialists
- **Specialist** (domain variants):
  - `research`: Web search, information gathering, document retrieval
  - `data_analysis`: SQL queries, data processing, statistical analysis
  - `writing`: Content generation, editing, synthesis
  - `code_execution`: Python execution, testing, automation
- **Reviewer**: Validates specialist output against expected schemas; flags issues; approves or rejects work

### 2. Task Decomposition Engine (`core/task_decomposition.py`)

Converts a high-level request into a structured task plan:

```python
# Input
request = "Research and analyze AI market trends, create a report"

# Output
plan = {
    "subtasks": [
        {
            "id": "task_1",
            "description": "Search for recent AI market analysis",
            "specialist_type": "research",
            "required_inputs": [],
            "estimated_complexity": "medium",
            "priority": 9,
        },
        {
            "id": "task_2",
            "description": "Analyze data and extract key insights",
            "specialist_type": "data_analysis",
            "required_inputs": ["task_1"],
            "estimated_complexity": "high",
            "priority": 8,
        },
        {
            "id": "task_3",
            "description": "Synthesize findings into comprehensive report",
            "specialist_type": "writing",
            "required_inputs": ["task_2"],
            "estimated_complexity": "medium",
            "priority": 10,
        },
    ],
    "execution_flow": [["task_1"], ["task_2"], ["task_3"]],
    "confidence": 0.85,  # ← Key metric for escalation
}
```

**Retry Logic**: If the LLM produces malformed plans, the engine automatically retries (up to 3 times) with feedback.

### 3. Tool Registry (`core/tool_registry.py`)

Singleton registry of available tools with full introspection:

```python
registry = ToolRegistry.get_instance()

# Available tools at launch
tools = registry.list_all_tools()
# [web_search, read_file, write_file, execute_python, query_database, api_call]

# Get tools for a specialist
research_tools = registry.get_tools_for_specialist("research")
# [web_search, read_file, api_call]

# Log tool invocations automatically
registry.log_invocation(
    tool_name="web_search",
    specialist_id="research_specialist",
    task_id="task_1",
    inputs={"query": "AI trends 2025"},
    outputs={"results": [...]},
    execution_time_ms=234,
    success=True,
)

# Query usage stats
stats = registry.get_tool_stats("web_search")
# {total_calls, success_rate, avg_time_ms, total_cost}
```

### 4. Orchestrator (`core/orchestration.py`)

LangGraph-based state machine that orchestrates the workflow:

```python
orchestrator = AgentOrchestrator(plan_confidence_threshold=0.6)

# Run the workflow end-to-end
result = await orchestrator.execute(
    request="Analyze the latest AI benchmarks",
    context_facts={"domain": "ML", "user_level": "expert"}
)

# Result structure
{
    "task_id": "abc123",
    "status": "complete",  # intake, planning, executing, reviewing, synthesizing, complete
    "plan": {...},
    "plan_confidence": 0.78,
    "completed_subtasks": {...},
    "review_result": {...},
    "final_output": {...},
    "decisions": [...],  # Full audit trail
    "errors": [],
    "total_cost": 2.34,
}
```

## Running the Demo

### Setup

1. **Clone and install**:
   ```bash
   cd "e:\Agent Orchestation System"
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API keys**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI and Anthropic API keys
   ```

3. **Run the demo**:
   ```bash
   python demo.py
   ```

### Expected Output

The demo will execute a multi-step research task and print:

1. ✓ Tool registry status (6 tools available)
2. ✓ Complex request decomposition
3. ✓ Task plan with subtasks and dependencies
4. ✓ Specialist assignments
5. ✓ Execution flow through each node
6. ✓ Subtask completion status
7. ✓ Review results
8. ✓ Final synthesized output
9. ✓ Tool usage statistics
10. ✓ Phase 1 checkpoint assessment

## Phase 1 Success Metrics

The demo checkpoint validates:

- [ ] **Schema Validation**: Generated plans pass validation on the first try (target: >80%)
- [ ] **Specialist Assignment**: Subtasks correctly routed to appropriate specialists
- [ ] **Tool Integration**: Tool registry operational with all 6 default tools
- [ ] **Workflow Completion**: End-to-end pipeline executes without errors
- [ ] **Review Quality**: Reviewer correctly validates output
- [ ] **Audit Trail**: Every decision logged and traceable
- [ ] **Structured Output**: All outputs follow defined schemas

## Architecture Decisions

### Why Three Layers?

1. **Supervisor** handles planning and meta-reasoning (what to do)
2. **Specialists** handle execution (how to do it) — separates concerns
3. **Reviewer** catches errors before they propagate — quality gate

This reduces hallucination, improves efficiency, and allows task-specific optimization at each layer.

### Why Structured Output?

All agents produce Pydantic models with defined schemas. This enables:
- Type checking and validation
- Reliable downstream parsing
- Clear error detection
- Audit trail generation
- Integration with traditional pipelines

### Why Logging Every Tool Call?

Full introspection into:
- Which tools are actually used (vs. unused)
- Success rates per tool
- Cost attribution
- Latency patterns
- Failure modes

This data is essential for Phase 4 (observability) and cost tracking.

## Extending Phase 1

### Adding a New Specialist Type

1. Add to `SpecialistType` enum in `agents.py`
2. Subclass `Specialist` with domain-specific logic
3. Register in `AgentOrchestrator.__init__()`
4. Add tools for that specialist in `ToolRegistry._initialize_default_tools()`

### Adding a New Tool

```python
registry = ToolRegistry.get_instance()
registry.register_tool(
    name="fetch_email",
    description="Retrieve email from Gmail inbox",
    category=ToolCategory.API_CALL,
    schema=ToolSchema(
        input_type={...},
        output_type={...},
    ),
    allowed_specialists=["research", "data_analysis"],
    rate_limit_per_minute=10,
    cost_per_call=0.01,
)
```

## Known Limitations (Phase 1)

1. **No persistent memory**: Tasks don't learn from past runs yet (Phase 2)
2. **No human-in-the-loop**: Can't pause for user approval yet (Phase 3)
3. **No observability UI**: No trace explorer or dashboard (Phase 4)
4. **Limited tool sandbox**: Code execution is mocked (Phase 5+)
5. **Single-model routing**: Uses same model for all agents (could optimize per agent)
6. **No rate limiting enforcement**: Registered limits aren't enforced yet
7. **Synchronous execution only**: Parallel subtasks run sequentially

These are intentional scope reductions for Phase 1 and will be addressed in subsequent phases.

## Next: Phase 2 — Memory System

Phase 2 will add:
- **Short-term memory** (Redis): Current task context
- **Long-term semantic memory** (ChromaDB): Past task learnings
- **Memory retrieval**: Inject relevant past experience into planning
- **Memory management**: Consolidation, expiration, user-requested deletion

The Phase 2 demo will show a task benefiting from past experience.

## Tech Stack

- **Orchestration**: LangGraph 0.1+
- **LLM Routing**: LangChain 0.1+
- **Models**: OpenAI (gpt-4-turbo) + Anthropic (Claude)
- **Data Models**: Pydantic 2.5+
- **Async**: asyncio + aiohttp
- **Environment**: python-dotenv

## Contributing

For contributions to Phase 1:
1. Follow the three-layer hierarchy
2. Use Pydantic for all data models
3. Log all tool invocations via ToolRegistry
4. Add tests for new agents
5. Update this README with new components

## License

[Your License Here]

## Contact & Support

For questions or issues, refer to the architecture docs or open an issue in the repository.

---

**Status**: ✓ Phase 1 Complete — Ready for Phase 2 (Memory System)
