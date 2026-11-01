"""Helpful links shown under an answer: an "Order online" link when the customer
wants to buy something, plus self-service pages that match the question.

Every URL comes from the admin's settings, never from the model, so a reply can't
contain an invented link or one planted by a prompt-injection attempt."""
from __future__ import annotations

import re
from typing import Any

MAX_LINKS = 3
ORDER_LABEL = "Order online"

_FOOD = (r"(burgers?|fries|meals?|drinks?|shakes?|milkshakes?|lemonades?|food|combos?|"
         r"onion rings|slaw|blazes?|infernos?|stacks?|flames?|embers?|something to eat)")

# The customer wants to buy something now.
_PURCHASE = [re.compile(p, re.I) for p in [
    rf"\b(i'?d like|i would like|i want|i wanna|can i (get|have)|could i (get|have)|"
    rf"let me (get|have)|get me|give me)\b.{{0,40}}\b{_FOOD}",
    r"\b(want|like|wish) to (order|buy|purchase)\b",
    r"\b(place|make|start|put in) an? (new )?order\b",
    r"\b(how|where) (do|can|could|should) i (order|buy|purchase)\b",
    r"\b(order|buy|purchase|get)\b.{0,25}\b(online|for delivery|delivered|for pick ?up|for takeaway|to go)\b",
    r"\b(order|buy|purchase) (a|an|some|two|three|four|five|\d+)\b",
    r"\b(i'?m|i am|so|really) (hungry|starving)\b|\bcraving\b",
]]

# Questions about ordering or delivery, where the ordering page is still useful.
_ORDER_TOPIC = re.compile(
    r"\b(deliver(y|ies|s)?|takeaway|take away|pick ?up|order online|online order(ing)?|"
    r"(the|your) app|website|minimum order)\b", re.I)

# About an order that already exists: point to support or refunds, not to a new order.
_EXISTING_ORDER = re.compile(
    r"\b(refunds?|missing|wrong|incorrect|cancel(led|ling)?|late|complain(t)?|never arrived|"
    r"cold|status|track(ing)?|where is my|where's my)\b", re.I)


def wants_to_buy(text: str) -> bool:
    return any(p.search(text) for p in _PURCHASE) and not _EXISTING_ORDER.search(text)


def _keyword_pattern(keyword: str) -> re.Pattern:
    # Whole words or phrases, with an optional plural ("burger" also matches "burgers")
    return re.compile(r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(e?s)?(?![a-z0-9])")


def _matches(text: str, keywords: list[str]) -> bool:
    return any(k.strip() and _keyword_pattern(k.strip()).search(text) for k in keywords)


def links_for(message: str, s: dict[str, Any], limit: int = MAX_LINKS) -> list[dict[str, str]]:
    """Return up to `limit` links ({label, url}) for this message, most useful first."""
    text = message.lower()
    out: list[dict[str, str]] = []
    order_url = (s.get("order_url") or "").strip()
    if order_url and not _EXISTING_ORDER.search(text) and (wants_to_buy(text) or _ORDER_TOPIC.search(text)):
        out.append({"label": ORDER_LABEL, "url": order_url})
    for link in s.get("quick_links") or []:
        if len(out) >= limit:
            break
        url = (link.get("url") or "").strip()
        if url and url not in {o["url"] for o in out} and _matches(text, link.get("keywords") or []):
            out.append({"label": link.get("label") or url, "url": url})
    return out


def is_safe_url(url: str) -> bool:
    """Absolute http(s) URLs, or paths on this site. Rejects javascript:, data:,
    protocol-relative //host links and anything with spaces or quotes."""
    u = url.strip()
    if not u or re.search(r"[\s\"'<>\\]", u):
        return False
    if u.startswith("/"):
        return not u.startswith("//")
    return bool(re.match(r"^https?://[^/]+", u, re.I))
