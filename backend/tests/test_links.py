"""Helpful links: purchase intent, keyword matching and URL safety. No network."""
import pytest

from app import links, settings_store

S = settings_store.DEFAULTS
ORDER = S["order_url"]


@pytest.mark.parametrize("msg", [
    "I'd like to order two Classic Blazes for delivery",
    "Can I get a Double Inferno and fries?",
    "How do I order?",
    "I want to buy a milkshake",
    "Can I order online?",
    "I'm hungry, get me a burger",
    "Where can I buy your food?",
    "I want to place an order",
])
def test_purchase_intent_detected(msg):
    assert links.wants_to_buy(msg.lower())


@pytest.mark.parametrize("msg", [
    "How much is the Classic Blaze?",
    "What time do you close on Sunday?",
    "My order was missing the fries, can I get a refund?",
    "I want to cancel my order",
    "Where is my order?",
    "I'd like to know your opening hours",
])
def test_no_purchase_intent(msg):
    assert not links.wants_to_buy(msg.lower())


def test_order_link_comes_first_for_purchase():
    out = links.links_for("I'd like to order two Classic Blaze burgers for delivery", S)
    assert out[0] == {"label": links.ORDER_LABEL, "url": ORDER}
    assert {"label": "Full menu and prices", "url": "/sample-site.html#menu"} in out


def test_topic_links_match_keywords():
    assert [l["url"] for l in links.links_for("How much is the Classic Blaze?", S)] == ["/sample-site.html#menu"]
    hours = links.links_for("What time does Jurong Point close on Saturday?", S)
    assert [l["url"] for l in hours] == ["/sample-site.html#locations"]
    assert links.links_for("Do you sell gift cards?", S)[0]["url"] == "/sample-site.html#gift-cards"


def test_refund_question_gets_refund_link_not_order_link():
    urls = [l["url"] for l in links.links_for("Can I get a refund if my delivery is very late?", S)]
    assert ORDER not in urls
    assert "/sample-site.html#refunds" in urls


def test_delivery_question_gets_order_link():
    assert links.links_for("What's the delivery fee?", S)[0]["url"] == ORDER


def test_plural_and_whole_word_matching():
    assert links.links_for("Are your burgers halal?", S)  # "burgers" matches "burger"
    assert not links.links_for("Tell me about your company history", S)  # no keyword inside other words


def test_at_most_three_links():
    msg = "I want to order a burger, what are your hours, points, allergens and gift cards?"
    assert len(links.links_for(msg, S)) == links.MAX_LINKS


def test_empty_order_url_turns_order_link_off():
    assert links.links_for("I want to order a burger", {**S, "order_url": ""})[0]["url"] != ORDER


@pytest.mark.parametrize("url,ok", [
    ("/sample-site.html#order", True),
    ("https://order.example.com/menu", True),
    ("http://example.com", True),
    ("javascript:alert(1)", False),
    ("data:text/html,hi", False),
    ("//evil.example.com", False),
    ("https://example.com/a b", False),
    ('https://example.com/"onmouseover', False),
    ("ftp://example.com", False),
    ("", False),
])
def test_safe_url(url, ok):
    assert links.is_safe_url(url) is ok
