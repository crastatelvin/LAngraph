# Worker Services

## Slack Outbound Worker

Polls and flushes queued Slack outbound messages (`chat.postMessage`) from persistent DB storage.

Run:
- `python -m apps.worker.slack_outbound_worker`

Environment:
- `ENABLE_SLACK_INTEGRATION=true`
- `SLACK_BOT_TOKEN=<token>`
- `SLACK_OUTBOUND_FLUSH_INTERVAL_SECONDS=5` (optional)

## Chain Anchor Worker

Polls and processes deferred chain anchor jobs from persistent DB storage.

Run:
- `python -m apps.worker.chain_anchor_worker`

Environment:
- `CHAIN_QUEUE_FLUSH_INTERVAL_SECONDS=5` (optional)
- `CHAIN_QUEUE_MAX_ITEMS=20` (optional)
