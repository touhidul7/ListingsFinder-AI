import json
import re

import requests

from .config import ANTHROPIC_API_KEY, OPENROUTER_API_KEY
from .models import SearchCriteria
from .parser import clean_industry, parse_mandate

ANTHROPIC_MODELS = [
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1-20250805",
    "claude-3-5-haiku-20241022",
]

OPENROUTER_MODELS = [
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-opus-4.1",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "google/gemini-2.5-pro",
    "meta-llama/llama-3.3-70b-instruct",
]

SYSTEM_PROMPT = """You convert Dealio Advisor search mandates into structured search criteria.
Return JSON only. Never estimate unknown values.
Fields:
industry string, location string, price_min number|null, price_max number|null,
revenue_min number|null, revenue_max number|null, keywords string, exclude string.
The goal is finding business-for-sale listings, not outreach or scoring.

Rules:
- Strip instruction words such as please, find, search for, best, looking for.
- Correct obvious typos in business words, such as copany -> company.
- Do not include company/business/entity words in industry unless they are part of the actual sector.
- Keep industry short and preserve the user's actual target sector.
- Convert shorthand money amounts such as $2M into numbers such as 2000000."""


def _json_from_text(text):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("AI response did not contain JSON")
    return json.loads(match.group(0))


def _criteria_from_payload(original_query, payload):
    fallback = parse_mandate(original_query)
    industry = clean_industry(str(payload.get("industry") or fallback.industry or ""))
    return SearchCriteria(
        original_query=original_query,
        industry=industry,
        location=str(payload.get("location") or fallback.location or "").strip(),
        price_min=payload.get("price_min") if payload.get("price_min") not in ("", None) else fallback.price_min,
        price_max=payload.get("price_max") if payload.get("price_max") not in ("", None) else fallback.price_max,
        revenue_min=payload.get("revenue_min") if payload.get("revenue_min") not in ("", None) else fallback.revenue_min,
        revenue_max=payload.get("revenue_max") if payload.get("revenue_max") not in ("", None) else fallback.revenue_max,
        keywords=str(payload.get("keywords") or industry or fallback.keywords or "").strip(),
        exclude=str(payload.get("exclude") or fallback.exclude or "").strip(),
    )


def _parse_with_anthropic(mandate, model, api_key=""):
    key = api_key or ANTHROPIC_API_KEY
    if not key:
        raise ValueError("Missing ANTHROPIC_API_KEY")
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 500,
            "temperature": 0,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": mandate}],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    return _criteria_from_payload(mandate, _json_from_text(text))


def _parse_with_openrouter(mandate, model, api_key=""):
    key = api_key or OPENROUTER_API_KEY
    if not key:
        raise ValueError("Missing OPENROUTER_API_KEY")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://streamlit.io",
            "X-Title": "ListingsFinder AI",
        },
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": mandate},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
    return _criteria_from_payload(mandate, _json_from_text(text))


def parse_mandate_with_ai(mandate, provider="Rule-based", model="", api_key=""):
    provider = (provider or "Rule-based").strip()
    if provider == "Anthropic":
        return _parse_with_anthropic(mandate, model or ANTHROPIC_MODELS[0], api_key), "Anthropic"
    if provider == "OpenRouter":
        return _parse_with_openrouter(mandate, model or OPENROUTER_MODELS[0], api_key), "OpenRouter"
    return parse_mandate(mandate), "Rule-based"


def ai_status(provider, api_key=""):
    if provider == "Anthropic":
        return bool(api_key or ANTHROPIC_API_KEY), "Configured" if (api_key or ANTHROPIC_API_KEY) else "Missing Anthropic API key"
    if provider == "OpenRouter":
        return bool(api_key or OPENROUTER_API_KEY), "Configured" if (api_key or OPENROUTER_API_KEY) else "Missing OpenRouter API key"
    return True, "Rule-based parser does not require an AI key"
