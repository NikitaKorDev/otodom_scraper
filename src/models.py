"""Data model shared by every layer."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Optional


@dataclass
class Listing:
    url: str
    id: str = ""
    title: str = ""
    price: str = ""
    rent: str = ""
    price_per_m2: str = ""
    address: str = ""
    rooms: str = ""
    area: str = ""
    floor: str = ""
    heating: str = ""
    condition: str = ""
    available_from: str = ""
    deposit: str = ""
    advertiser_type: str = ""
    seller_name: str = ""
    extra_info: str = ""
    description: str = ""
    images: list = field(default_factory=list)
    source: list = field(default_factory=list)   # which extraction paths hit
    raw: dict = field(default_factory=dict)       # anything extra, kept as-is
    error: str = ""

    # --- filled in by the (optional) Gemini AI overview pass ---
    ai_hidden_catches: list = field(default_factory=list)
    ai_extra_monthly_cost: Optional[float] = None
    ai_extra_cost_note: str = ""
    ai_summary: str = ""
    ai_total_monthly_price: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Listing":
        """Rebuild a Listing from a saved listings.json record, ignoring
        keys that no longer exist on the dataclass."""
        known = {f.name for f in fields(cls)}
        listing = cls(url=data.get("url", ""))
        for key, value in data.items():
            if key in known:
                setattr(listing, key, value)
        return listing
