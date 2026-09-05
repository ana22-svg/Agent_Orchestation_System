"""
Agent Orchestration System

A multi-agent platform for decomposing complex tasks, executing them via specialist agents,
learning from past interactions via persistent memory, escalating to humans when needed,
and providing full observability into all decisions.

Phases:
1. ✓ Agent Architecture (Supervisor, Specialists, Reviewer, LangGraph orchestration)
2. ✓ Memory System (Redis short-term, ChromaDB long-term, retrieval, management)
3. Human-in-the-Loop (approval queue, escalation triggers)
4. Observability (traces, cost tracking, replay)
5. Integration & Testing (Docker, E2E tests)
6. Portfolio Polish (demo video, narrative)
"""

__version__ = "0.3.0"
__phase__ = "Phase 3: Human-in-the-Loop"

try:
    from core import (
        Agent,
        Supervisor,
        Specialist,
        Reviewer,
        SpecialistType,
        AgentContext,
        AgentDecision,
        TaskDecompositionEngine,
        TaskPlan,
        Subtask,
        ExecutionMode,
        Complexity,
        ToolRegistry,
        ToolDefinition,
        ToolInvocation,
        ToolCategory,
        AgentOrchestrator,
        ExecutionState,
        ApprovalQueue,
        ApprovalRequest,
        ApprovalStatus,
        ObservabilityManager,
        TraceExplorer,
        TaskTrace,
        TraceEvent,
        CostTracker,
        Tenant,
        TenantRegistry,
        TenantTaskStore,
    )
except Exception:  # pragma: no cover - optional runtime deps may be absent in lightweight envs
    Agent = Supervisor = Specialist = Reviewer = None
    SpecialistType = AgentContext = AgentDecision = None
    TaskDecompositionEngine = TaskPlan = Subtask = None
    ExecutionMode = Complexity = None
    ToolRegistry = ToolDefinition = ToolInvocation = ToolCategory = None
    AgentOrchestrator = ExecutionState = None
    ApprovalQueue = ApprovalRequest = ApprovalStatus = None
    ObservabilityManager = TraceExplorer = TaskTrace = TraceEvent = CostTracker = None
    Tenant = TenantRegistry = TenantTaskStore = None

try:
    from memory import (
        ShortTermMemory,
        LongTermMemory,
        Memory,
        MemoryRetriever,
        PlanningWithMemory,
        MemoryManager,
        MaintenanceScheduler,
        ImportanceLevel,
        MemoryAPI,
        MemoryFactory,
    )
except Exception:  # pragma: no cover - optional memory backends may be absent
    ShortTermMemory = LongTermMemory = Memory = None
    MemoryRetriever = PlanningWithMemory = None
    MemoryManager = MaintenanceScheduler = ImportanceLevel = None
    MemoryAPI = MemoryFactory = None

__all__ = [
    # Phase 1
    "Agent",
    "Supervisor",
    "Specialist",
    "Reviewer",
    "SpecialistType",
    "AgentContext",
    "AgentDecision",
    "TaskDecompositionEngine",
    "TaskPlan",
    "Subtask",
    "ExecutionMode",
    "Complexity",
    "ToolRegistry",
    "ToolDefinition",
    "ToolInvocation",
    "ToolCategory",
    "AgentOrchestrator",
    "ExecutionState",
    "ApprovalQueue",
    "ApprovalRequest",
    "ApprovalStatus",
    "ObservabilityManager",
    "TraceExplorer",
    "TaskTrace",
    "TraceEvent",
    "CostTracker",
    "Tenant",
    "TenantRegistry",
    "TenantTaskStore",
    # Phase 2
    "ShortTermMemory",
    "LongTermMemory",
    "Memory",
    "MemoryRetriever",
    "PlanningWithMemory",
    "MemoryManager",
    "MaintenanceScheduler",
    "ImportanceLevel",
    "MemoryAPI",
    "MemoryFactory",
]
