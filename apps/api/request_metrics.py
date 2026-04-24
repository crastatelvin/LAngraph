from dataclasses import dataclass, field


@dataclass
class EndpointMetric:
    count: int = 0
    total_latency_ms: float = 0.0


@dataclass
class EndpointMetricsStore:
    data: dict[str, EndpointMetric] = field(default_factory=dict)

    def observe(self, key: str, latency_ms: float) -> None:
        metric = self.data.setdefault(key, EndpointMetric())
        metric.count += 1
        metric.total_latency_ms += latency_ms

    def snapshot(self) -> dict:
        result: dict[str, dict] = {}
        for key, metric in self.data.items():
            avg = metric.total_latency_ms / metric.count if metric.count else 0.0
            result[key] = {"count": metric.count, "avg_latency_ms": round(avg, 2)}
        return result

