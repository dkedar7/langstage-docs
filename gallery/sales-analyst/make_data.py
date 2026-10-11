"""Generate workspace/sales.csv: a year of weekly sales for Northwind Outfitters.

Synthetic and seeded, so it is the same on every run. It has the patterns a real
outdoor retailer's data has, for the agent to find: summer camping and winter
apparel seasonality, a steadily growing online share, one region growing faster than
the rest, and a footwear return-rate spike in the Northeast in August and September.

    python make_data.py
"""

from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(20261011)

REGIONS = {"West": 1.30, "Mountain": 0.85, "Midwest": 0.80, "Northeast": 1.10, "South": 0.95}
CATEGORIES = {  # weekly base revenue per region, average price
    "Tents": (5200, 189.0),
    "Packs": (4100, 129.0),
    "Apparel": (7800, 96.0),
    "Footwear": (6100, 129.0),
    "Hydration": (1900, 34.0),
}
BASE_RETURN = {"Tents": 0.04, "Packs": 0.03, "Apparel": 0.07, "Footwear": 0.06, "Hydration": 0.01}
START = date(2025, 10, 6)  # the first Monday of October 2025: four 13-week quarters
WEEKS = 52


def seasonality(category: str, week_start: date) -> float:
    m = week_start.month + week_start.day / 31
    if category in ("Tents", "Hydration"):  # camping season peaks in July
        return 1 + 0.75 * math.cos((m - 7.2) / 12 * 2 * math.pi)
    if category == "Apparel":  # jackets peak in December
        return 1 + 0.55 * math.cos((m - 12.3) / 12 * 2 * math.pi)
    if category == "Packs":  # summer, plus back-to-school in late August
        return 1 + 0.35 * math.cos((m - 7.8) / 12 * 2 * math.pi)
    return 1 + 0.15 * math.cos((m - 5.0) / 12 * 2 * math.pi)  # footwear: spring races


def main() -> None:
    out = Path(__file__).parent / "workspace" / "sales.csv"
    rows = []
    for w in range(WEEKS):
        week = START + timedelta(weeks=w)
        online_share = 0.38 + 0.14 * w / (WEEKS - 1)  # 38% -> 52% over the year
        for region, size in REGIONS.items():
            growth = 1 + (0.45 if region == "Mountain" else 0.08) * w / (WEEKS - 1)
            for category, (base, price) in CATEGORIES.items():
                revenue_total = base * size * growth * seasonality(category, week) * random.uniform(0.9, 1.1)
                for channel, share in (("Online", online_share), ("Retail", 1 - online_share)):
                    revenue = revenue_total * share
                    units = max(1, round(revenue / (price * random.uniform(0.92, 1.05))))
                    rate = BASE_RETURN[category]
                    # The Switchback runners' sizing problem: Northeast footwear returns
                    # jump in August and September.
                    if category == "Footwear" and region == "Northeast" and week >= date(2026, 8, 3):
                        rate = 0.22
                    returned = sum(random.random() < rate for _ in range(units))
                    rows.append({
                        "week": week.isoformat(), "region": region, "channel": channel,
                        "category": category, "units": units, "revenue": round(revenue, 2),
                        "returned_units": returned,
                    })
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
