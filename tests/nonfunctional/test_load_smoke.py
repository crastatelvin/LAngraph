from pathlib import Path
import statistics
import sys
import time

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app

HEADERS = {
    "X-Tenant-Id": "tenant-load-001",
    "X-User-Id": "load-runner",
    "X-User-Role": "admin",
    "X-Request-Id": "req-load-001",
}


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return ordered[index]


def test_health_endpoint_smoke_p95_latency() -> None:
    latencies_ms: list[float] = []
    with TestClient(app) as client:
        for _ in range(80):
            started = time.perf_counter()
            response = client.get("/health")
            elapsed_ms = (time.perf_counter() - started) * 1000
            assert response.status_code == 200
            latencies_ms.append(elapsed_ms)
    assert _p95(latencies_ms) < 250.0


def test_debate_create_smoke_success_rate_and_latency() -> None:
    runs = 20
    successes = 0
    latencies_ms: list[float] = []
    with TestClient(app) as client:
        for idx in range(runs):
            started = time.perf_counter()
            response = client.post(
                "/v1/debates",
                json={"proposal": f"Load smoke proposal {idx} - keep systems reliable"},
                headers=HEADERS,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies_ms.append(elapsed_ms)
            if response.status_code == 200:
                successes += 1
    success_rate = successes / runs
    avg_latency = statistics.fmean(latencies_ms) if latencies_ms else 0.0
    assert success_rate >= 0.95
    assert avg_latency < 3000.0
