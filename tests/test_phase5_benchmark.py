import time

from core import TenantRegistry


def test_tenant_authentication_benchmark():
    registry = TenantRegistry()
    for index in range(1000):
        registry.register(f"tenant-{index}", f"key-{index}")

    started = time.perf_counter()
    for _ in range(100):
        assert registry.require_tenant("key-999").tenant_id == "tenant-999"
    elapsed = time.perf_counter() - started

    assert elapsed < 0.25