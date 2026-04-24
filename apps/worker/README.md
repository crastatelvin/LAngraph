# Worker Services

## Slack Outbound Worker

Polls and flushes queued Slack outbound messages (`chat.postMessage`) from persistent DB storage.

Run:
- `python -m apps.worker.slack_outbound_worker`

Environment:
- `ENABLE_SLACK_INTEGRATION=true`
- `SLACK_BOT_TOKEN=<token>`
- `SLACK_OUTBOUND_FLUSH_INTERVAL_SECONDS=5` (optional)
