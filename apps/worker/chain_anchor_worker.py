import logging
import os
import time

from apps.api.chain import process_anchor_jobs
from apps.api.db import Base, SessionLocal, engine

logger = logging.getLogger("worker.chain_anchor")


def run_flush_once(max_items: int = 20) -> dict:
    db = SessionLocal()
    try:
        return process_anchor_jobs(db=db, max_items=max_items)
    finally:
        db.close()


def run_forever() -> None:
    Base.metadata.create_all(bind=engine)
    interval_seconds = float(os.getenv("CHAIN_QUEUE_FLUSH_INTERVAL_SECONDS", "5"))
    max_items = int(os.getenv("CHAIN_QUEUE_MAX_ITEMS", "20"))
    logger.info("Starting chain anchor worker interval=%s max_items=%s", interval_seconds, max_items)
    while True:
        result = run_flush_once(max_items=max_items)
        logger.info("Chain anchor worker cycle result=%s", result)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_forever()
