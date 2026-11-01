"""Question-log encryption and IP pseudonymization. No network."""
import sqlite3

from cryptography.fernet import Fernet

from app import db, log_crypto
from app.config import config


def test_round_trip_and_ciphertext_hides_text():
    secret = "My phone is 9123 4567 and I'm allergic to peanuts"
    token = log_crypto.encrypt(secret)
    assert token.startswith(log_crypto.PREFIX)
    assert "9123" not in token and "peanuts" not in token
    assert log_crypto.decrypt(token) == secret


def test_same_text_encrypts_differently_each_time():
    assert log_crypto.encrypt("hello") != log_crypto.encrypt("hello")


def test_plaintext_from_before_encryption_passes_through():
    assert log_crypto.decrypt("What time do you close?") == "What time do you close?"
    assert log_crypto.decrypt(None) is None


def test_wrong_key_is_reported_not_raised():
    foreign = Fernet(Fernet.generate_key()).encrypt(b"secret").decode()
    assert log_crypto.decrypt(log_crypto.PREFIX + foreign) == log_crypto.UNREADABLE


def test_ip_is_hashed_one_way_and_consistently():
    h = log_crypto.pseudonymize("203.0.113.7")
    assert h.startswith(log_crypto.HASH_PREFIX) and "203.0.113.7" not in h
    assert h == log_crypto.pseudonymize("203.0.113.7")
    assert h != log_crypto.pseudonymize("203.0.113.8")
    assert log_crypto.pseudonymize(h) == h  # already hashed: unchanged
    assert log_crypto.pseudonymize(None) is None


def test_key_comes_from_environment():
    assert log_crypto.key_source() == "env"


def test_plaintext_rows_are_encrypted_at_startup():
    db.init()
    with sqlite3.connect(config.data_dir / "app.db") as c:
        c.execute("INSERT INTO question_log (ts, question, classification, client) VALUES (?,?,?,?)",
                  ("2026-01-01T00:00:00+00:00", "legacy plaintext question", "in_scope", "198.51.100.4"))
    db.init()
    with sqlite3.connect(config.data_dir / "app.db") as c:
        q, client = c.execute("SELECT question, client FROM question_log "
                              "WHERE ts='2026-01-01T00:00:00+00:00'").fetchone()
    assert q.startswith(log_crypto.PREFIX) and "legacy" not in q
    assert client.startswith(log_crypto.HASH_PREFIX)
    assert any(r["question"] == "legacy plaintext question" for r in db.list_logs(1000))
