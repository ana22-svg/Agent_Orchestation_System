import asyncio

import pytest

from core import AgentOrchestrator, TenantRegistry, TenantTaskStore


def test_workflow_records_trace_and_isolates_tenant_tasks(monkeypatch):
    orchestrator = AgentOrchestrator()

    async def deterministic_plan(self, request, context_facts=None):
        return self._create_fallback_plan(request) | {"confidence": 0.9}

    monkeypatch.setattr("core.orchestration.TaskDecompositionEngine.decompose", deterministic_plan)

    async def run_without_langgraph(initial_state):
        state = await orchestrator._node_intake(initial_state)
        state = await orchestrator._node_planning(state)
        state = await orchestrator._node_specialist_execution(state)
        state = await orchestrator._node_review(state)
        state = await orchestrator._node_synthesis(state)
        return await orchestrator._node_deliver(state)

    monkeypatch.setattr(orchestrator, "_run_graph_async", run_without_langgraph)

    registry = TenantRegistry()
    tenant = registry.register("tenant-a", "key-a")
    tasks = TenantTaskStore()

    result = asyncio.run(orchestrator.execute("Summarize the deployment checklist"))
    tasks.register(result["task_id"], tenant.tenant_id)

    tasks.require_access(result["task_id"], tenant.tenant_id)
    with pytest.raises(PermissionError):
        tasks.require_access(result["task_id"], "tenant-b")

    trace = orchestrator.trace_explorer.get_task(result["task_id"])
    assert result["status"] == "complete"
    assert trace["status"] == "complete"
    assert any(event["action"] == "workflow_finished" for event in trace["events"])


def test_authentication_rejects_unknown_keys():
    registry = TenantRegistry()
    registry.register("tenant-a", "key-a")

    assert registry.require_tenant("key-a").tenant_id == "tenant-a"
    with pytest.raises(PermissionError):
        registry.require_tenant("wrong-key")