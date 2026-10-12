"""Generate the incident workspace's logs: an API that starts failing after a deploy.

Seeded, so it's the same on every run. The story is in the data, not spelled out:
v2.8.0 ships at 14:02 with a new CSV export endpoint and a "tidy" config change that
cuts the database pool from 20 connections to 5. Slow exports hold connections, the
pool runs dry, and requests start failing with pool timeouts and 503s.

    python make_logs.py
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(1011)
WS = Path(__file__).parent / "workspace"
DAY = datetime(2026, 10, 11)
DEPLOY = DAY.replace(hour=14, minute=2, second=11)
START, END = DAY.replace(hour=13, minute=30), DAY.replace(hour=14, minute=40)
ROUTES = [("GET", "/v2/orders", 40), ("GET", "/v2/orders/{id}", 25), ("POST", "/v2/orders", 60),
          ("GET", "/v2/customers/{id}", 20), ("GET", "/healthz", 2)]


def api_log() -> list[str]:
    lines, t = [], START
    pool = 20
    while t < END:
        t += timedelta(seconds=random.uniform(0.8, 3.5))
        ts = t.strftime("%Y-%m-%d %H:%M:%S,") + f"{random.randint(0, 999):03d}"
        if pool == 20 and t >= DEPLOY:
            pool = 5
            lines += [
                f"{ts} INFO  api.boot: starting api version=2.8.0 commit=9f3c2e1 workers=4",
                f"{ts} INFO  api.db: engine created url=postgresql://orders-db:5432/orders pool_size=5 max_overflow=0 pool_timeout=30",
                f"{ts} INFO  api.routes: registered GET /v2/orders/export (csv)",
            ]
            continue
        after = t >= DEPLOY
        if after and random.random() < 0.10:
            dur = random.uniform(18, 34)
            lines.append(f"{ts} INFO  api.access: GET /v2/orders/export?format=csv 200 {dur * 1000:.0f}ms rows={random.randint(80_000, 240_000)}")
            continue
        method, route, base = random.choice(ROUTES)
        path = route.replace("{id}", str(random.randint(10_000, 99_999)))
        pressure = min(1.0, max(0.0, (t - DEPLOY).total_seconds() / 600)) if after else 0.0
        if after and random.random() < 0.55 * pressure and route != "/healthz":
            lines.append(f"{ts} ERROR api.db: sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 0 reached, connection timed out, timeout 30.00")
            lines.append(f"{ts} WARN  api.access: {method} {path} 503 30012ms")
            continue
        ms = base * random.uniform(0.6, 1.8) * (1 + 6 * pressure)
        lines.append(f"{ts} INFO  api.access: {method} {path} 200 {ms:.0f}ms")
    return lines


def db_log() -> list[str]:
    lines, t = [], START
    while t < END:
        t += timedelta(seconds=random.uniform(20, 40))
        ts = t.strftime("%Y-%m-%d %H:%M:%S UTC")
        conns = random.randint(16, 21) if t < DEPLOY else random.randint(4, 5)
        lines.append(f"{ts} [stats] connections active={conns} idle={max(0, 20 - conns) if t < DEPLOY else 0} db=orders")
        if t >= DEPLOY and random.random() < 0.5:
            lines.append(f"{ts} [slow] duration: {random.uniform(18_000, 34_000):.1f} ms  statement: SELECT o.*, c.email FROM orders o JOIN customers c ON c.id = o.customer_id ORDER BY o.created_at")
    return lines


def main() -> None:
    (WS / "logs").mkdir(parents=True, exist_ok=True)
    (WS / "logs" / "api.log").write_text("\n".join(api_log()) + "\n", encoding="utf-8")
    (WS / "logs" / "orders-db.log").write_text("\n".join(db_log()) + "\n", encoding="utf-8")
    print("wrote", *(p.relative_to(WS.parent) for p in sorted((WS / "logs").iterdir())))


if __name__ == "__main__":
    main()
