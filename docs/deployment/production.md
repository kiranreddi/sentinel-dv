# Production Deployment

Sentinel DV is an MCP server that runs locally over stdio. For “always on” deployments, you can run it under `systemd`.

## Server unit (example)

Create `/etc/systemd/system/sentinel-dv.service`:

```ini
[Unit]
Description=Sentinel DV MCP server
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/sentinel-dv
Environment=PYTHONUNBUFFERED=1
Environment=SENTINEL_DV_CONFIG=/path/to/config.yaml

ExecStart=/usr/bin/python3 -m sentinel_dv.server

Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Indexing

Indexing is a separate step. Run it at startup, before the server starts, or periodically with a `systemd` timer/cron.

Example one-shot indexing:

```bash
python -m sentinel_dv.indexing.indexer --config /path/to/config.yaml --index-all
```

