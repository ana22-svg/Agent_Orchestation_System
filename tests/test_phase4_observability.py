from core import ObservabilityManager


def test_observability_tracks_trace_and_cost():
    manager = ObservabilityManager()
    task_id = "task-456"

    trace = manager.begin_task(task_id, "Analyze a risky rollout plan")
    manager.record_event(task_id, "planning", "create_plan", confidence=0.72)
    manager.record_tool_cost(task_id, "web_search", 1.5)
    manager.record_tool_cost(task_id, "api_call", 0.75)
    manager.record_task_completed(task_id, status="complete", final_output={"result": "ok"})

    assert trace.task_id == task_id
    assert trace.total_cost == 2.25
    assert len(trace.events) >= 2
    assert manager.get_task_trace(task_id).status == "complete"
    assert manager.get_summary()["costs"]["total_spend"] == 2.25
