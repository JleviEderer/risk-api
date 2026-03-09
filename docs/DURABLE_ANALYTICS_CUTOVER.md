# Durable Analytics Cutover

Use this when moving `/stats` and `/dashboard` off ephemeral per-machine JSONL logs and onto the SQLite-backed request-event store.

## Current State

- Repo support exists:
  - `ANALYTICS_DB_PATH` enables SQLite event persistence
  - `/stats` prefers SQLite when that env var is set
  - `REQUEST_LOG_PATH` remains available as the legacy JSONL fallback
- Production cutover was completed on 2026-03-09:
  - Fly volume `augur_analytics` exists in `iad`
  - the app mounts it at `/data`
  - live `/stats` reports `storage_backend=sqlite` and `storage_durable=true`

## Constraints

- This app currently runs as a single Fly machine.
- A Fly volume is attached to one machine regionally.
- Do not scale this analytics approach to multiple active app machines without redesigning the backend around shared storage.

## Recommended Cutover Path

Use this flow again if production is recreated or if another environment needs the same setup.

1. Create a Fly volume in the app region:

   ```bash
   fly volumes create augur_analytics --region iad --size 1 -a augurrisk
   ```

2. `fly.toml` is already prepared for the cutover:
   - volume mount: `augur_analytics -> /data`
   - `ANALYTICS_DB_PATH=/data/analytics.sqlite3`
   - `REQUEST_LOG_PATH=/data/requests.jsonl`

3. Deploy:

   ```bash
   fly deploy
   ```

4. Verify live stats are using SQLite:

   ```bash
   curl https://augurrisk.com/stats
   ```

   Expected fields:
   - `"storage_backend": "sqlite"`
   - `"storage_durable": true`
   - `"storage_path": "/data/analytics.sqlite3"`

5. Restart or redeploy once more and verify counts survive.

## Optional Backfill

If you want continuity from an existing JSONL request log before cutover:

```bash
python scripts/backfill_analytics_db.py --from-log /path/to/requests.jsonl --to-db /data/analytics.sqlite3
```

Notes:
- The SQLite store deduplicates identical entries by content fingerprint.
- Re-running the backfill should skip entries that were already imported.

## Post-Cutover Checks

- `/stats` returns `storage_backend=sqlite`
- `/dashboard` still renders correctly
- request totals survive a deploy
- recent events continue to update after new traffic
- Better Stack health checks are unaffected

## Not Solved By This

- Old-domain `403` traffic that never reaches Flask
- Edge-layer or DNS-layer attribution
- Multi-machine shared analytics
