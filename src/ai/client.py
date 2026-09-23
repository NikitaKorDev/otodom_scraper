"""Thin wrapper around the Gemini SDK (imported lazily - it's optional)."""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from src.ai.prompts import RESPONSE_SCHEMA, SYSTEM_INSTRUCTION, build_contents
from src.models import Listing
from src.utils.logger import log

TRANSIENT_ERROR_MARKERS = ("429", "500", "503", "UNAVAILABLE", "DEADLINE_EXCEEDED")


def make_gemini_client(api_key: Optional[str] = None):
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai isn't installed. Run: pip install google-genai"
        ) from exc
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "No Gemini API key found. Set the GEMINI_API_KEY environment "
            "variable (or pass --gemini-api-key). Get a free key at "
            "https://aistudio.google.com/app/apikey"
        )
    return genai.Client(api_key=key)


def call_gemini_with_retry(client, model: str, contents: str, config: dict, max_retries: int = 4):
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as exc:
            transient = any(code in str(exc) for code in TRANSIENT_ERROR_MARKERS)
            if attempt == max_retries or not transient:
                raise
            log(f"    Gemini call failed ({exc}); retrying in {delay:.0f}s...")
            time.sleep(delay)
            delay *= 2


def analyze_with_gemini(client, model: str, listing: Listing) -> dict:
    response = call_gemini_with_retry(
        client,
        model,
        contents=build_contents(listing),
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
            "temperature": 0.1,
        },
    )
    return json.loads(response.text)
