"""Human approval queue for escalated workflow decisions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Lifecycle states for a human approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRequest(BaseModel):
    """A request that needs human review before execution proceeds."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    original_request: str
    plan_confidence: float = 0.0
    rationale: str = ""
    summary: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer_id: str = "human"
    decision_notes: str = ""
    resolved_at: Optional[datetime] = None

    @property
    def is_pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING


class ApprovalQueue:
    """In-memory queue for human-in-the-loop approvals."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._by_task: dict[str, list[str]] = {}

    def submit_request(
        self,
        task_id: str,
        original_request: str,
        plan_confidence: float = 0.0,
        rationale: str = "",
        summary: str = "",
        reviewer_id: str = "human",
    ) -> ApprovalRequest:
        """Submit a new approval request."""
        request = ApprovalRequest(
            task_id=task_id,
            original_request=original_request,
            plan_confidence=plan_confidence,
            rationale=rationale,
            summary=summary,
            reviewer_id=reviewer_id,
        )
        self._requests[request.request_id] = request
        self._by_task.setdefault(task_id, []).append(request.request_id)
        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def get_pending(self) -> list[ApprovalRequest]:
        return [request for request in self._requests.values() if request.status == ApprovalStatus.PENDING]

    def get_for_task(self, task_id: str) -> list[ApprovalRequest]:
        request_ids = self._by_task.get(task_id, [])
        return [self._requests[request_id] for request_id in request_ids if request_id in self._requests]

    def resolve_request(
        self,
        request_id: str,
        approved: bool,
        notes: str = "",
        reviewer_id: str = "human",
    ) -> ApprovalRequest:
        """Resolve an approval request with a human decision."""
        request = self._requests.get(request_id)
        if request is None:
            raise ValueError(f"Approval request {request_id} not found")

        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.decision_notes = notes
        request.reviewer_id = reviewer_id
        request.resolved_at = datetime.utcnow()
        return request

    def resolve_task(
        self,
        task_id: str,
        approved: bool,
        notes: str = "",
        reviewer_id: str = "human",
    ) -> ApprovalRequest:
        """Resolve the most recent pending approval for a task."""
        pending = [request for request in self.get_for_task(task_id) if request.status == ApprovalStatus.PENDING]
        if not pending:
            raise ValueError(f"No pending approval request for task {task_id}")

        latest = pending[-1]
        return self.resolve_request(latest.request_id, approved, notes=notes, reviewer_id=reviewer_id)

    def list_all(self) -> list[ApprovalRequest]:
        return list(self._requests.values())
