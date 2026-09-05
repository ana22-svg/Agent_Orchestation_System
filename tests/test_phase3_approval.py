from core import AgentOrchestrator, ApprovalQueue


def test_approval_queue_registers_and_resolves_pending_request():
    queue = ApprovalQueue()
    task_id = "task-123"

    request = queue.submit_request(
        task_id=task_id,
        original_request="Assess a risky deployment plan",
        plan_confidence=0.42,
        rationale="Confidence is below the safe threshold.",
        summary="Needs human approval before proceeding.",
    )

    assert request.task_id == task_id
    assert request.status.value == "pending"
    assert len(queue.get_pending()) == 1

    resolved = queue.resolve_request(request.request_id, approved=True, notes="Approved by operator")
    assert resolved.status.value == "approved"
    assert resolved.decision_notes == "Approved by operator"
