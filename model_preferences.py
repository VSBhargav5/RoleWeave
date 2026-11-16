"""Non-secret per-workspace provider preferences, distinct from one-request credentials."""
from contextlib import closing
import hashlib
import json
import sqlite3

from career_profile import unique_json
from model_providers import DEFAULT, validate_config


def settings_bytes(config):
    validate_config(config)
    return json.dumps({"format": "roleweave-model-settings-v1", "config": config}, sort_keys=True).encode()


def parse_settings(payload):
    if not isinstance(payload, bytes) or len(payload) > 2048: raise ValueError("Model settings exceed 2 KiB")
    try: record = json.loads(payload, object_pairs_hook=unique_json)
    except (ValueError, UnicodeError, RecursionError): raise ValueError("Invalid model settings") from None
    if not isinstance(record, dict) or set(record) != {"format", "config"} or record["format"] != "roleweave-model-settings-v1": raise ValueError("Unsupported model preferences")
    return validate_config(record["config"])


def stored_settings(store):
    with closing(sqlite3.connect(store.path)) as db:
        row = db.execute("SELECT value FROM app_settings WHERE key='model_provider'").fetchone()
    if row is None: return None
    payload = row[0].encode()
    return settings_bytes(parse_settings(payload))


def read_settings(store):
    payload = stored_settings(store) or settings_bytes(DEFAULT)
    return {"config": parse_settings(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def save_settings(store, config, expected_sha256=None):
    payload = settings_bytes(config)
    with closing(sqlite3.connect(store.path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT value FROM app_settings WHERE key='model_provider'").fetchone()
        current = settings_bytes(parse_settings(row[0].encode())) if row else settings_bytes(DEFAULT)
        if expected_sha256 is not None and expected_sha256 != hashlib.sha256(current).hexdigest(): raise ValueError("Provider preferences changed; refresh and review again")
        db.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES ('model_provider',?)", (payload.decode(),))
    return read_settings(store)
