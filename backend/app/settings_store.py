"""Company-editable bot settings, persisted as JSON in the data directory."""
from __future__ import annotations

import json
import threading
from typing import Any

from .config import config

_PATH = config.data_dir / "settings.json"
_LOCK = threading.Lock()

DEFAULTS: dict[str, Any] = {
    "company_name": "Blaze Burger Co.",
    "bot_name": "Blaze",
    "allowed_topics": [
        "menu", "prices", "ingredients and allergens", "orders and delivery",
        "store hours", "locations", "promotions", "refunds", "loyalty program",
    ],
    "support_contact": "support@blazeburger.example or +65 6000 1234",
    "refusal_message": (
        "Sorry, I can only help with questions about {company_name}, like our menu, "
        "orders, store hours and refunds. What can I help you with today?"
    ),
    "relevance_threshold": config.default_relevance_threshold,
    # Links point at the bundled demo site (frontend/public/sample-site.html).
    # A real deployment replaces them with the company's own pages.
    "order_url": "/sample-site.html#order",
    "quick_links": [
        {"label": "Full menu and prices", "url": "/sample-site.html#menu",
         "keywords": ["menu", "price", "cost", "how much", "burger", "fries", "side", "drink",
                      "milkshake", "kids meal", "add-on", "meal upgrade"]},
        {"label": "Outlets and opening hours", "url": "/sample-site.html#locations",
         "keywords": ["hours", "open", "opening", "close", "closing", "outlet", "location", "address",
                      "directions", "parking", "nearest", "closest", "public holiday", "last order"]},
        {"label": "Blaze Rewards and promotions", "url": "/sample-site.html#rewards",
         "keywords": ["points", "loyalty", "reward", "birthday", "member", "promotion", "promo", "deal",
                      "discount", "student", "two-for-one", "tuesday"]},
        {"label": "Allergen and dietary guide", "url": "/sample-site.html#allergens",
         "keywords": ["allergen", "allergy", "allergies", "gluten", "halal", "vegan", "vegetarian",
                      "peanut", "nut", "dairy", "egg", "sesame"]},
        {"label": "Gift cards", "url": "/sample-site.html#gift-cards",
         "keywords": ["gift card", "voucher"]},
        {"label": "Refund request form", "url": "/sample-site.html#refunds",
         "keywords": ["refund", "missing", "wrong item", "incorrect", "cancel", "complaint",
                      "late delivery"]},
    ],
}


def get() -> dict[str, Any]:
    with _LOCK:
        if not _PATH.exists():
            return dict(DEFAULTS)
        try:
            stored = json.loads(_PATH.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return dict(DEFAULTS)
    return {**DEFAULTS, **{k: v for k, v in stored.items() if k in DEFAULTS}}


def update(values: dict[str, Any]) -> dict[str, Any]:
    merged = {**get(), **{k: v for k, v in values.items() if k in DEFAULTS}}
    with _LOCK:
        tmp = _PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(merged, indent=2, ensure_ascii=False), "utf-8")
        tmp.replace(_PATH)  # atomic swap so a crash never leaves half-written settings
    return merged


def render(template: str, s: dict[str, Any]) -> str:
    """Fill {company_name}/{bot_name}/{support_contact} without using str.format,
    so stray braces in admin-written text can't raise or leak attributes."""
    return (
        template.replace("{company_name}", s["company_name"])
        .replace("{bot_name}", s["bot_name"])
        .replace("{support_contact}", s["support_contact"])
    )


def refusal_message(s: dict[str, Any]) -> str:
    return render(s["refusal_message"], s)


def fallback_message(s: dict[str, Any]) -> str:
    return f"I don't have that information right now. Please contact {s['support_contact']} for help."
