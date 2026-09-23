"""Read/write listings.json and listings.csv."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from src.models import Listing

CSV_FIELDS = [
    "id", "url", "title", "price", "rent", "price_per_m2", "address",
    "rooms", "area", "floor", "heating", "condition", "available_from",
    "deposit", "advertiser_type", "seller_name", "extra_info",
    "description", "image_count", "error",
    "ai_total_monthly_price", "ai_extra_monthly_cost", "ai_hidden_catches", "ai_summary",
]


def save_outputs(listings: list, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "listings.json").write_text(
        json.dumps([asdict(l) for l in listings], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (out_dir / "listings.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for l in listings:
            row = asdict(l)
            row["image_count"] = len(l.images)
            row["ai_hidden_catches"] = "; ".join(l.ai_hidden_catches)
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def load_listings(path: Path) -> list:
    """Load a previously-saved listings.json back into Listing objects -
    used by --ai-only so you can add the AI pass without re-scraping."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Listing.from_dict(d) for d in data]
