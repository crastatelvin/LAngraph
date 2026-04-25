from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import apps.api.main as api_main
from apps.api.main import app
from apps.api.db import Base, SessionLocal, engine
from apps.api.models import UsageEventModel

FREE_HEADERS = {
    "X-Tenant-Id": "tenant-free-001",
    "X-User-Id": "user-free-1",
    "X-User-Role": "admin",
    "X-Request-Id": "req-plan-001",
}
PRO_HEADERS = {
    "X-Tenant-Id": "tenant-pro-001",
    "X-User-Id": "user-pro-1",
    "X-User-Role": "admin",
    "X-Request-Id": "req-plan-002",
}


def _reset_usage_table() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(UsageEventModel).delete()
    db.commit()
    db.close()


def test_plan_limit_enforces_debate_create_quota() -> None:
    _reset_usage_table()
    old_defaults = api_main.os.getenv("PLAN_LIMIT_DEFAULTS_JSON")
    old_overrides = api_main.os.getenv("PLAN_LIMIT_OVERRIDES_JSON")
    api_main.os.environ["PLAN_LIMIT_DEFAULTS_JSON"] = (
        '{"plan":"pro","limits":{"debate_create_per_day":100,"agent_outcome_ingest_per_day":100,"chain_anchor_requests_per_day":100}}'
    )
    api_main.os.environ["PLAN_LIMIT_OVERRIDES_JSON"] = (
        '{"tenant-free-001":{"plan":"free","limits":{"debate_create_per_day":1}}}'
    )
    try:
        with TestClient(app) as client:
            first = client.post("/v1/debates", json={"proposal": "Free tier first debate"}, headers=FREE_HEADERS)
            assert first.status_code == 200
            second = client.post("/v1/debates", json={"proposal": "Free tier second debate"}, headers=FREE_HEADERS)
            assert second.status_code == 402
            payload = second.json()
            assert payload["limit_key"] == "debate_create_per_day"
            assert payload["plan"] == "free"
    finally:
        if old_defaults is None:
            api_main.os.environ.pop("PLAN_LIMIT_DEFAULTS_JSON", None)
        else:
            api_main.os.environ["PLAN_LIMIT_DEFAULTS_JSON"] = old_defaults
        if old_overrides is None:
            api_main.os.environ.pop("PLAN_LIMIT_OVERRIDES_JSON", None)
        else:
            api_main.os.environ["PLAN_LIMIT_OVERRIDES_JSON"] = old_overrides


def test_plan_limit_does_not_block_other_tenant() -> None:
    _reset_usage_table()
    old_defaults = api_main.os.getenv("PLAN_LIMIT_DEFAULTS_JSON")
    old_overrides = api_main.os.getenv("PLAN_LIMIT_OVERRIDES_JSON")
    api_main.os.environ["PLAN_LIMIT_DEFAULTS_JSON"] = (
        '{"plan":"pro","limits":{"debate_create_per_day":100,"agent_outcome_ingest_per_day":100,"chain_anchor_requests_per_day":100}}'
    )
    api_main.os.environ["PLAN_LIMIT_OVERRIDES_JSON"] = (
        '{"tenant-free-001":{"plan":"free","limits":{"debate_create_per_day":1}}}'
    )
    try:
        with TestClient(app) as client:
            first = client.post("/v1/debates", json={"proposal": "Pro tenant debate one"}, headers=PRO_HEADERS)
            second = client.post("/v1/debates", json={"proposal": "Pro tenant debate two"}, headers=PRO_HEADERS)
            assert first.status_code == 200
            assert second.status_code == 200
    finally:
        if old_defaults is None:
            api_main.os.environ.pop("PLAN_LIMIT_DEFAULTS_JSON", None)
        else:
            api_main.os.environ["PLAN_LIMIT_DEFAULTS_JSON"] = old_defaults
        if old_overrides is None:
            api_main.os.environ.pop("PLAN_LIMIT_OVERRIDES_JSON", None)
        else:
            api_main.os.environ["PLAN_LIMIT_OVERRIDES_JSON"] = old_overrides
