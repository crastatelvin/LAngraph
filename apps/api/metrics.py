from dataclasses import dataclass


@dataclass
class WorkflowMetricsStore:
    total_runs: int = 0
    parse_failure_count: int = 0
    fallback_count: int = 0
    total_latency_ms: float = 0.0

    def record_workflow(self, metrics: dict) -> None:
        self.total_runs += 1
        self.parse_failure_count += int(metrics.get("parse_failures", 0))
        self.fallback_count += int(metrics.get("fallback_used", False))
        self.total_latency_ms += float(metrics.get("latency_ms", 0.0))

    def snapshot(self) -> dict:
        avg_latency = self.total_latency_ms / self.total_runs if self.total_runs else 0.0
        return {
            "total_runs": self.total_runs,
            "parse_failure_count": self.parse_failure_count,
            "fallback_count": self.fallback_count,
            "avg_workflow_latency_ms": round(avg_latency, 2),
        }
