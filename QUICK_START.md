# Quick Start Guide — Agent Orchestration System Phase 1

## 5-Minute Setup

### Step 1: Install (2 min)

```bash
cd "e:\Agent Orchestation System"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure (1 min)

```bash
cp .env.example .env
```

Then edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-...your-key...
```

### Step 3: Run (2 min)

```bash
python demo.py
```

You'll see a complete workflow execution with all 7 nodes (planning, execution, review, synthesis, delivery).

---

## What You'll See

The demo outputs:

1. **Tool Registry** (6 tools available)
2. **Request Decomposition** (complex task → subtasks)
3. **Plan Creation** (with confidence scores and dependencies)
4. **Execution** (specialists running subtasks)
5. **Review** (output validation)
6. **Synthesis** (combining results)
7. **Final Output** (ready for user)

Look for: `✓ CHECKPOINT PASSED` at the end = success!

---

## What Gets Logged

Every decision is recorded:
```
[Step 1] Initialize Agent Orchestrator
✓ Supervisor configured
✓ 4 specialists available
✓ 6 tools registered

[Step 4] Execute Agent Orchestration Workflow
[planning] ✓ Plan created with 3 subtasks, confidence: 0.87
[specialist_execution] ✓ Research → task_1 completed
[specialist_execution] ✓ Data analysis → task_2 completed
[specialist_execution] ✓ Writing → task_3 completed
[review] ✓ Output approved
[synthesis] ✓ Results combined
[deliver] ✓ Delivered
```

---

## Key Files to Explore

- **`core/agents.py`** — Supervisor, Specialist, Reviewer implementations
- **`core/orchestration.py`** — LangGraph workflow (7 nodes)
- **`core/task_decomposition.py`** — Request → plan conversion
- **`core/tool_registry.py`** — Tool definitions and logging
- **`demo.py`** — Full validation script
- **`README.md`** — Comprehensive documentation

---

## Customizing for Your Domain

### Add a New Specialist

```python
# In demo.py
orchestrator.specialists["my_domain"] = Specialist(SpecialistType.MY_DOMAIN)

# Then request something that needs that specialist type
request = "Use my_domain to solve..."
```

### Add a New Tool

```python
registry = ToolRegistry.get_instance()
registry.register_tool(
    name="my_tool",
    description="Does something useful",
    category=ToolCategory.API_CALL,
    schema=ToolSchema(...),
    allowed_specialists=["research", "my_domain"],
)
```

### Adjust Thresholds

```python
# In demo.py or any script
orchestrator = AgentOrchestrator(
    plan_confidence_threshold=0.7  # Raise to escalate more
)
```

---

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'langgraph'"

Solution: Run `pip install -r requirements.txt` from the project root

### Error: "OPENAI_API_KEY not found"

Solution: 
1. Copy `.env.example` to `.env`
2. Add your OpenAI API key to `.env`
3. Never commit `.env` to git!

### Demo runs but shows low confidence

This is normal — the LLM sometimes produces plans with 0.5-0.7 confidence. The demo handles this gracefully and still completes. In production (Phase 3), low confidence triggers human review.

### Want to run with test/mock data?

```bash
MOCK_EXECUTION=true python demo.py
```

This skips actual LLM calls and uses fallback plans (fast for testing).

---

## Next Steps

### Understand the Architecture

1. Read [README.md](README.md) for detailed architecture
2. Read [PHASE1_SUMMARY.md](PHASE1_SUMMARY.md) for implementation overview
3. Explore `core/` modules — well-documented code

### Try It Out

1. Run the demo: `python demo.py`
2. Look at the plan and decision log
3. Modify the request in demo.py and re-run
4. Check `logs/agent_system.log` for full execution trace

### Prepare for Phase 2

Phase 2 adds memory. Start thinking about:
- What facts should the system remember from this task?
- How would a previous similar task help this one?
- What should be forgotten over time?

---

## Architecture Diagram

```
REQUEST
    ↓
[SUPERVISOR] ← Plan decomposition
    ↓ (creates plan with confidence score)
[PLANNING] 
    ↓
[CONFIDENCE CHECK]
    ├→ Low (< 0.6) → [ESCALATE] → END (Phase 3: human approval)
    └→ OK → [EXECUTION]
         ├→ [Research Specialist] (uses web_search, read_file, api_call)
         ├→ [Data Analysis Specialist] (uses execute_python, query_database)
         └→ [Writing Specialist] (uses write_file)
         ↓
    [REVIEW] ← Validates output
         ↓
    [QUALITY CHECK]
         ├→ Needs Work → Resend to specialist for rework
         └→ OK → [SYNTHESIS]
         ↓
    [DELIVERY]
         ↓
    FINAL OUTPUT
```

---

## Performance Notes

- **Planning**: 2-5 seconds (depends on request complexity)
- **Specialist execution**: 1-3 seconds per subtask (currently mocked)
- **Review**: <1 second
- **Synthesis**: <1 second
- **Total**: 3-10 seconds per task

In production (Phase 4+), you'll see actual tool latencies (web search ~2s, code execution ~5s, etc.).

---

## Getting Help

1. **Error in demo?** Check the traceback — it points to the exact issue
2. **Want to customize?** Look at the docstrings in `core/agents.py`
3. **Confused about architecture?** Read `README.md` → Architecture Decisions section
4. **Need examples?** Check `demo.py` for real usage patterns

---

## What's Next?

- ✓ Phase 1 Complete: Agent architecture done
- → Phase 2: Add memory system (Redis + ChromaDB)
- → Phase 3: Add human approval flow
- → Phase 4: Add observability dashboard
- → Phase 5: Package in Docker Compose
- → Phase 6: Portfolio-ready demo

Ready to proceed to Phase 2?

---

**Status**: ✓ Phase 1 Ready  
**Last Updated**: September 5, 2026  
**Estimated Time to Run Demo**: 2-3 minutes
