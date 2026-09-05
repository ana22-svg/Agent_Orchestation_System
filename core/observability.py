"""Observability primitives for trace capture and cost tracking."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import json


@dataclass
class TraceEvent:
    """A single event recorded during a task lifecycle."""

    timestamp: str
    node: str
    action: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "node": self.node,
            "action": self.action,
            "metadata": self.metadata,
        }


@dataclass
class TaskTrace:
    """A full trace for a single task execution."""

    task_id: str
    request: str
    status: str = "pending"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    events: list[TraceEvent] = field(default_factory=list)
    total_cost: float = 0.0
    tool_costs: dict[str, float] = field(default_factory=dict)
    domain_facts: list[str] = field(default_factory=list)
    completed_subtasks: list[str] = field(default_factory=list)
    final_output: Any = None

    def add_event(self, node: str, action: str, **metadata: Any) -> None:
        self.events.append(
            TraceEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                node=node,
                action=action,
                metadata=metadata,
            )
        )

    def finalize(self, status: str, final_output: Any = None) -> None:
        self.status = status
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.final_output = final_output

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "request": self.request,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_cost": self.total_cost,
            "tool_costs": self.tool_costs,
            "domain_facts": self.domain_facts,
            "completed_subtasks": self.completed_subtasks,
            "events": [event.to_dict() for event in self.events],
            "final_output": self.final_output,
        }


class CostTracker:
    """Tracks per-task and per-tool cost. """

    def __init__(self) -> None:
        self.task_costs: dict[str, float] = defaultdict(float)
        self.tool_costs: dict[str, float] = defaultdict(float)

    def add_cost(self, task_id: str, amount: float, tool_name: Optional[str] = None) -> float:
        amount = float(amount)
        self.task_costs[task_id] += amount
        if tool_name:
            self.tool_costs[tool_name] += amount
        return self.task_costs[task_id]

    def get_task_total(self, task_id: str) -> float:
        return float(self.task_costs.get(task_id, 0.0))

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self.task_costs),
            "total_spend": sum(self.task_costs.values()),
            "tool_costs": dict(self.tool_costs),
            "task_costs": dict(self.task_costs),
        }


class ObservabilityManager:
    """Aggregates task traces and cost metrics for observability."""

    def __init__(self) -> None:
        self.traces: dict[str, TaskTrace] = {}
        self.cost_tracker = CostTracker()

    def begin_task(self, task_id: str, request: str) -> TaskTrace:
        trace = TaskTrace(task_id=task_id, request=request)
        self.traces[task_id] = trace
        trace.add_event("intake", "task_started", request_preview=request[:120])
        return trace

    def record_event(self, task_id: str, node: str, action: str, **metadata: Any) -> TaskTrace:
        trace = self.traces.setdefault(task_id, TaskTrace(task_id=task_id, request="unknown"))
        trace.add_event(node, action, **metadata)
        return trace

    def record_tool_cost(self, task_id: str, tool_name: str, amount: float) -> float:
        total = self.cost_tracker.add_cost(task_id, amount, tool_name)
        trace = self.traces.get(task_id)
        if trace is not None:
            trace.total_cost = total
            trace.tool_costs[tool_name] = trace.tool_costs.get(tool_name, 0.0) + float(amount)
        return total

    def record_task_completed(self, task_id: str, status: str = "complete", final_output: Any = None) -> TaskTrace:
        trace = self.traces.get(task_id)
        if trace is None:
            trace = TaskTrace(task_id=task_id, request="unknown")
            self.traces[task_id] = trace
        trace.finalize(status=status, final_output=final_output)
        trace.total_cost = self.cost_tracker.get_task_total(task_id)
        return trace

    def get_task_trace(self, task_id: str) -> Optional[TaskTrace]:
        return self.traces.get(task_id)

    def get_all_traces(self) -> list[dict[str, Any]]:
        return [self.traces[task_id].to_dict() for task_id in self.traces]

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self.traces),
            "completed_tasks": sum(1 for trace in self.traces.values() if trace.status in {"complete", "delivered"}),
            "active_tasks": sum(1 for trace in self.traces.values() if trace.status not in {"complete", "delivered"}),
            "costs": self.cost_tracker.get_summary(),
        }

    def export_json(self) -> str:
        return json.dumps({"traces": self.get_all_traces(), "summary": self.get_summary()}, indent=2)


class TraceExplorer:
    """Simple query interface for task traces."""

    def __init__(self, manager: ObservabilityManager):
        self.manager = manager

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        trace = self.manager.get_task_trace(task_id)
        return trace.to_dict() if trace else None

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        traces = list(self.manager.traces.values())
        traces = sorted(traces, key=lambda trace: trace.started_at, reverse=True)
        return [trace.to_dict() for trace in traces[:limit]]
