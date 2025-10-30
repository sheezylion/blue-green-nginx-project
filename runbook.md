# Blue-Green Failover Alerts Runbook

## Alert types

### 1) Failover detected (blue → green or green → blue)

What it means  
Nginx began serving successful responses from the backup pool, which indicates the primary stopped responding or returned errors.

Operator actions

1. Check container health for the primary pool:
   - `docker compose ps`
   - `docker compose logs nginx`
   - `docker compose logs app_<pool>`
2. Look for chaos drills or planned work.
3. If unplanned, keep an eye on error rates. Investigate app logs and recent changes.
4. Once primary recovers, traffic should return automatically.

### 2) High upstream error rate (> threshold)

What it means  
The percentage of 5xx responses in the sliding window exceeded the configured threshold.

Operator actions

1. Inspect `docker compose logs app_blue` and `app_green` for errors.
2. Check recent deploys or config changes.
3. Consider toggling pools manually if one side is consistently failing.
4. Verify external dependencies used by the app.

### 3) Recovery (informational)

We rely on the absence of continued alerts and the watcher log to confirm recovery. Optional enhancement: add a "recovery" Slack message when error rate returns below threshold for N consecutive windows.

## Suppressing alerts during planned work

Set `MAINTENANCE_MODE=true` in `.env` before planned flips, then `docker compose up -d` to refresh the watcher environment.  
This suppresses failover alerts. You still receive error-rate alerts to catch unexpected 5xx storms.

## Useful commands

- Tail Nginx JSON logs  
  `docker compose exec nginx sh -c 'tail -n 100 -f /var/log/nginx/access.json.log'`

- Watcher logs  
  `docker compose logs -f alert_watcher`

- Manual version check  
  `curl -s http://localhost:8080/version`

## Tuning

- `ERROR_RATE_THRESHOLD` default 2
- `WINDOW_SIZE` default 200
- `ALERT_COOLDOWN_SEC` default 300

Increase `WINDOW_SIZE` to reduce noise. Increase cooldown to reduce chatty channels.
