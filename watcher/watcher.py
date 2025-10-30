import os
import sys
import time
import json
import re
import requests
from collections import deque
from datetime import datetime, timezone

# Env
ACTIVE_POOL = os.getenv("ACTIVE_POOL", "blue").strip().lower()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()
ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", "2"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "200"))
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", "300"))
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").strip().lower() == "true"
LOG_PATH = os.getenv("LOG_PATH", "/var/log/nginx/access.json.log")

# State
last_pool = ACTIVE_POOL
window = deque(maxlen=WINDOW_SIZE)
last_error_rate_alert_ts = 0.0
last_failover_alert_ts = 0.0

def now_ts():
    return time.time()

def post_slack(text, blocks=None):
    if not SLACK_WEBHOOK_URL:
        print(f"[watcher] SLACK_WEBHOOK_URL not set. Would post: {text}", flush=True)
        return
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code >= 400:
            print(f"[watcher] Slack post failed: {resp.status_code} {resp.text}", flush=True)
    except Exception as e:
        print(f"[watcher] Slack post exception: {e}", flush=True)

def parse_status_code(upstream_status, overall_status):
    """
    upstream_status can be '502' or '502, 200' etc.
    We use the last code if present, else fall back to overall status.
    """
    if upstream_status:
        nums = re.findall(r"\d{3}", str(upstream_status))
        if nums:
            try:
                return int(nums[-1])
            except ValueError:
                pass
    try:
        return int(overall_status)
    except Exception:
        return 0

def is_error(code):
    return 500 <= code <= 599

def tail_f(path):
    with open(path, "r") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue
            yield line

def cooldown_ok(last_ts):
    return (now_ts() - last_ts) >= ALERT_COOLDOWN_SEC

def alert_failover(prev_pool, new_pool, sample):
    global last_failover_alert_ts
    if not cooldown_ok(last_failover_alert_ts):
        return
    last_failover_alert_ts = now_ts()

    t = sample.get("time", datetime.now().isoformat())
    release = sample.get("release", "unknown")
    upstream = sample.get("upstream_addr", "unknown")
    text = f"Failover detected: {prev_pool} → {new_pool}\nRelease: {release}\nUpstream: {upstream}\nTime: {t}"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Failover detected* {prev_pool} → {new_pool}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Release: `{release}` | Upstream: `{upstream}` | Time: {t}"}]},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": "_Action: check health of primary container, review upstream logs, confirm auto-recovery._"}}
    ]
    post_slack(text, blocks)

def alert_error_rate(rate_pct, sample):
    global last_error_rate_alert_ts
    if not cooldown_ok(last_error_rate_alert_ts):
        return
    last_error_rate_alert_ts = now_ts()

    t = sample.get("time", datetime.now().isoformat())
    pool = sample.get("pool", "unknown")
    text = f"High upstream error rate: {rate_pct:.2f}% over last {len(window)} requests\nPool: {pool}\nTime: {t}"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*High upstream error rate* {rate_pct:.2f}% over last {len(window)} reqs"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Pool: `{pool}` | Time: {t}"}]},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": "_Action: inspect upstream app logs, check recent deploys, consider toggling pools if errors persist._"}}
    ]
    post_slack(text, blocks)

def main():
    global last_pool

    print(f"[watcher] starting. active_pool={last_pool} window={WINDOW_SIZE} threshold={ERROR_RATE_THRESHOLD}% cooldown={ALERT_COOLDOWN_SEC}s maintenance={MAINTENANCE_MODE}", flush=True)
    print(f"[watcher] tailing {LOG_PATH}", flush=True)

    try:
        for raw in tail_f(LOG_PATH):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                # Not JSON, skip
                continue

            pool = str(rec.get("pool") or "").strip().lower()
            release = rec.get("release")
            upstream_status = rec.get("upstream_status")
            overall_status = rec.get("status")
            code = parse_status_code(upstream_status, overall_status)

            # Track error window
            window.append(is_error(code))
            if len(window) >= max(50, int(WINDOW_SIZE * 0.25)):  # minimum sample before alerting
                error_rate = (sum(1 for x in window if x) / len(window)) * 100.0
                if error_rate > ERROR_RATE_THRESHOLD:
                    alert_error_rate(error_rate, rec)

            # Detect failover on first successful response from a different pool
            if pool and pool != last_pool:
                # Treat a success as evidence of real traffic cutover
                if 200 <= code <= 399:
                    if not MAINTENANCE_MODE:
                        prev = last_pool
                        last_pool = pool
                        alert_failover(prev, pool, rec)
                    else:
                        # Quiet during planned toggles
                        last_pool = pool
                        print(f"[watcher] maintenance mode: observed pool change {last_pool}", flush=True)

    except FileNotFoundError:
        print(f"[watcher] log file not found: {LOG_PATH}", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"[watcher] fatal error: {e}", flush=True)
        sys.exit(2)

if __name__ == "__main__":
    main()
