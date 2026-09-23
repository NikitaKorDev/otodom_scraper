"""Prompt text, response schema and prompt assembly for the Gemini pass."""

from __future__ import annotations

from src.models import Listing

SYSTEM_INSTRUCTION = (
    "You are a meticulous analyst for Polish rental-apartment listings. You "
    "are given the scraped fields and the full free-text description (in "
    "Polish) of one otodom.pl listing. Read the description closely for "
    "anything a renter could easily miss on a skim: extra recurring fees "
    "that are NOT already covered by the advertised price/rent or czynsz "
    "(e.g. a fixed internet/media/parking fee, mandatory cleaning fee), "
    "restrictive or unusual conditions (no pets, students only/not "
    "allowed, guarantor or Polish-citizenship required, cash only, minimum "
    "stay, short-term-only, huge deposit relative to rent, commission owed "
    "to the agency on top of rent, etc.), and any wording that hints the "
    "lister is downplaying a cost or condition. Be conservative: only "
    "report an extra monthly cost if the text actually states or clearly "
    "implies a concrete PLN amount - otherwise leave it null rather than "
    "guessing. Respond only with JSON matching the given schema, in the "
    "same language as the description (Polish) for the summary field."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "hidden_catches": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Short, specific bullet points (one sentence each) for every "
                "hidden catch, extra cost, or restrictive condition found in "
                "the description. Empty array if there genuinely are none."
            ),
        },
        "extra_monthly_recurring_cost_pln": {
            "type": ["number", "null"],
            "description": (
                "A recurring MONTHLY cost in PLN mentioned in the "
                "description that is not already part of the advertised "
                "price or czynsz (e.g. a flat internet or parking fee). "
                "Null if none is mentioned or the amount can't be pinned "
                "down."
            ),
        },
        "extra_cost_explanation": {
            "type": "string",
            "description": "One short sentence: where extra_monthly_recurring_cost_pln came from, or why it's null.",
        },
        "summary_pl": {
            "type": "string",
            "description": "One or two sentence plain-language summary (in Polish) of what a renter should watch out for.",
        },
    },
    "required": [
        "hidden_catches",
        "extra_monthly_recurring_cost_pln",
        "extra_cost_explanation",
        "summary_pl",
    ],
}


def build_contents(listing: Listing) -> str:
    return (
        f"Title: {listing.title}\n"
        f"Advertised price: {listing.price}\n"
        f"Advertised rent/czynsz: {listing.rent}\n"
        f"Deposit: {listing.deposit}\n"
        f"Advertiser type: {listing.advertiser_type}\n"
        f"'Extra info' field from the listing: {listing.extra_info}\n\n"
        f"Full description:\n{listing.description or '(no description available)'}"
    )
