from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.db import SessionLocal
from apps.api.models import SlackOutboundMessageModel, SlackSentDedupeModel
from apps.api.slack import SlackIntegration
from apps.worker.slack_outbound_worker import run_flush_once


def test_worker_flush_once_sends_and_marks_dedupe() -> None:
    db = SessionLocal()
    db.query(SlackOutboundMessageModel).delete()
    db.query(SlackSentDedupeModel).delete()
    db.commit()
    db.close()

    slack = SlackIntegration()

    def fake_send(token: str, channel: str, text: str, thread_ts: str | None = None) -> bool:
        return True

    original_sender = slack._send_chat_post_message
    slack._send_chat_post_message = fake_send

    import os

    old_flag = os.getenv("ENABLE_SLACK_INTEGRATION")
    old_token = os.getenv("SLACK_BOT_TOKEN")
    os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
    try:
        db = SessionLocal()
        slack.queue_thread_message(db=db, channel="C777", text="worker test", dedupe_key="wk1")
        db.close()

        result = run_flush_once(slack=slack)
        assert result["sent"] == 1

        db = SessionLocal()
        sent = db.query(SlackSentDedupeModel).filter(SlackSentDedupeModel.dedupe_key == "wk1").first()
        db.close()
        assert sent is not None
    finally:
        slack._send_chat_post_message = original_sender
        if old_flag is None:
            os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
        else:
            os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
        if old_token is None:
            os.environ.pop("SLACK_BOT_TOKEN", None)
        else:
            os.environ["SLACK_BOT_TOKEN"] = old_token
