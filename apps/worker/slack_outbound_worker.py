import logging
import os
import time

from apps.api.db import Base, SessionLocal, engine
from apps.api.slack import SlackIntegration

logger = logging.getLogger("worker.slack_outbound")


def run_flush_once(slack: SlackIntegration | None = None) -> dict:
    integration = slack or SlackIntegration()
    db = SessionLocal()
    try:
        return integration.flush_outbound_queue(db=db)
    finally:
        db.close()


def run_forever() -> None:
    Base.metadata.create_all(bind=engine)
    interval_seconds = float(os.getenv("SLACK_OUTBOUND_FLUSH_INTERVAL_SECONDS", "5"))
    logger.info("Starting Slack outbound worker interval=%s", interval_seconds)
    while True:
        result = run_flush_once()
        logger.info("Slack outbound worker cycle result=%s", result)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_forever()
