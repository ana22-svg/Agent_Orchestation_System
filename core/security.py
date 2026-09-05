"""Tenant isolation and API-key authorization for the orchestration service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Tenant:
    """A tenant allowed to submit and inspect tasks."""

    tenant_id: str
    api_key: str
    active: bool = True


@dataclass
class TenantRegistry:
    """In-memory tenant registry suitable for local deployment and tests."""

    tenants: dict[str, Tenant] = field(default_factory=dict)

    def register(self, tenant_id: str, api_key: str) -> Tenant:
        if not tenant_id or not api_key:
            raise ValueError("tenant_id and api_key are required")
        tenant = Tenant(tenant_id=tenant_id, api_key=api_key)
        self.tenants[tenant_id] = tenant
        return tenant

    def authenticate(self, api_key: str) -> Optional[Tenant]:
        for tenant in self.tenants.values():
            if tenant.active and tenant.api_key == api_key:
                return tenant
        return None

    def require_tenant(self, api_key: str) -> Tenant:
        tenant = self.authenticate(api_key)
        if tenant is None:
            raise PermissionError("Invalid or inactive API key")
        return tenant


class TenantTaskStore:
    """Stores task ownership and prevents cross-tenant task access."""

    def __init__(self) -> None:
        self._owners: dict[str, str] = {}

    def register(self, task_id: str, tenant_id: str) -> None:
        self._owners[task_id] = tenant_id

    def owns(self, task_id: str, tenant_id: str) -> bool:
        return self._owners.get(task_id) == tenant_id

    def require_access(self, task_id: str, tenant_id: str) -> None:
        if not self.owns(task_id, tenant_id):
            raise PermissionError("Task does not belong to tenant")