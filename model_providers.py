"""Explicit structured-output provider contracts; fixed cloud hosts or numeric loopback."""
import hashlib
import http.client
import json
import re
import time

from ai_tailoring import parse_response, validate_draft
from network_io import Cancelled, json_object
from runtime_paths import APP_VERSION

KINDS = {"openai": "OpenAI", "anthropic": "Anthropic", "mistral": "Mistral", "ollama": "Ollama (loopback)", "lmstudio": "LM Studio / compatible (loopback)"}
DEFAULT = {"kind": "openai", "model": "gpt-4.1-mini", "port": 0}
LOCAL = {"ollama", "lmstudio"}


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {"kind", "model", "port"}:
        raise ValueError("Provider preferences accept kind, model and port only; no credentials")
    if not isinstance(config["kind"], str) or config["kind"] not in KINDS: raise ValueError("Unsupported model provider")
    if not isinstance(config["model"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,199}", config["model"]):
        raise ValueError("Enter a model identifier of at most 200 ASCII characters")
    if type(config["port"]) is not int or (config["kind"] in LOCAL and not 1 <= config["port"] <= 65535) or (config["kind"] not in LOCAL and config["port"] != 0):
        raise ValueError("Use a numeric loopback port for local servers, or zero for fixed cloud providers")
    return config


def destination(config):
    validate_config(config)
    kind = config["kind"]
    if kind == "openai": return "https://api.openai.com/v1/responses"
    if kind == "anthropic": return "https://api.anthropic.com/v1/messages"
    if kind == "mistral": return "https://api.mistral.ai/v1/chat/completions"
    return "http://127.0.0.1:" + str(config["port"]) + ("/api/chat" if kind == "ollama" else "/v1/chat/completions")


def request_payload(original, config):
    validate_config(config); base = json_object(original)
    if config["kind"] == "openai":
        result = dict(base, model=config["model"])
    else:
        messages = [{"role": "system", "content": base["instructions"]}, {"role": "user", "content": base["input"][0]["content"]}]
        schema = base["text"]["format"]["schema"]
        if config["kind"] == "anthropic":
            result = {"model": config["model"], "max_tokens": 4096, "stream": False, "system": base["instructions"],
                      "messages": messages[1:], "output_config": {"format": {"type": "json_schema", "schema": schema}}}
        elif config["kind"] == "ollama":
            result = {"model": config["model"], "messages": messages, "stream": False, "format": schema, "options": {"num_predict": 4096}}
        else:
            result = {"model": config["model"], "messages": messages, "stream": False, "max_tokens": 4096,
                      "response_format": {"type": "json_schema", "json_schema": {"name": "application_draft", "strict": True, "schema": schema}}}
    payload = json.dumps(result, ensure_ascii=False, indent=2).encode()
    if len(payload) > 256 * 1024: raise ValueError("Provider request exceeds 256 KiB")
    return payload


def request_fingerprint(payload, config):
    return hashlib.sha256(json.dumps({"endpoint": destination(config), "payload_sha256": hashlib.sha256(payload).hexdigest()}, sort_keys=True).encode()).hexdigest()


def validate_key(config, key, demo=False):
    validate_config(config)
    if demo: return
    if not isinstance(key, str) or len(key) > 1000 or not key.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("Enter a valid one-request key/token without whitespace")
    if config["kind"] not in LOCAL and not key: raise ValueError("This cloud provider needs a one-request API key")


def parse_provider_response(payload, facts, config):
    validate_config(config)
    if not isinstance(payload, bytes) or len(payload) > 1024 * 1024: raise ValueError("Model response exceeds 1 MiB")
    if config["kind"] == "openai": return parse_response(payload, facts)
    result = json_object(payload)
    if not isinstance(result, dict): raise ValueError("Unsupported model response")
    kind = config["kind"]
    if kind == "anthropic":
        content = result.get("content")
        if result.get("type") != "message" or result.get("role") != "assistant" or result.get("stop_reason") != "end_turn" or not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict) or content[0].get("type") != "text":
            raise ValueError("Model response incomplete, refused or unsupported")
        value = content[0].get("text")
    elif kind == "ollama":
        message = result.get("message")
        if result.get("done") is not True or result.get("done_reason") not in (None, "stop") or not isinstance(message, dict) or message.get("role") != "assistant" or message.get("tool_calls"):
            raise ValueError("Local model response incomplete or unsupported")
        value = message.get("content")
    else:
        choices = result.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict) or choices[0].get("finish_reason") != "stop": raise ValueError("Model response incomplete or refused")
        message = choices[0].get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant" or message.get("tool_calls") or message.get("refusal"): raise ValueError("Unsupported model message")
        value = message.get("content")
    if not isinstance(value, str): raise ValueError("Model did not return JSON text")
    return validate_draft(json_object(value.encode()), facts)


def request_model(config, payload, key, cancel):
    validate_config(config); validate_key(config, key)
    if not isinstance(payload, bytes) or len(payload) > 256 * 1024: raise ValueError("Model request exceeds 256 KiB")
    kind = config["kind"]
    path = {"openai": "/v1/responses", "anthropic": "/v1/messages", "mistral": "/v1/chat/completions", "ollama": "/api/chat", "lmstudio": "/v1/chat/completions"}[kind]
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "RoleWeave/" + APP_VERSION}
    if key: headers["Authorization"] = "Bearer " + key
    if kind == "anthropic": headers["anthropic-version"] = "2026-10-21"
    connection = None; deadline = time.monotonic() + 60
    try:
        if cancel.is_set(): raise Cancelled("Cancelled locally")
        if kind in LOCAL: connection = http.client.HTTPConnection("127.0.0.1", config["port"], timeout=5)
        else: connection = http.client.HTTPSConnection({"openai": "api.openai.com", "anthropic": "api.anthropic.com", "mistral": "api.mistral.ai"}[kind], timeout=5)
        if cancel.is_set(): raise Cancelled("Cancelled locally")
        connection.request("POST", path, body=payload, headers=headers)
        response = connection.getresponse()
        if response.status != 200: raise ValueError("Model provider returned HTTP " + str(response.status) + "; no redirect or retry")
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json": raise ValueError("Model provider did not return JSON")
        parts = []; size = 0
        while True:
            if cancel.is_set(): raise Cancelled("Cancelled locally")
            if time.monotonic() > deadline: raise ValueError("Model request exceeded 60-second local deadline")
            part = response.read1(min(65536, 1024 * 1024 + 1 - size))
            if not part: break
            parts.append(part); size += len(part)
            if size > 1024 * 1024: raise ValueError("Model response exceeds 1 MiB")
        if getattr(response,"length",None) not in (None,0): raise ValueError("Model response ended before its declared length")
        if cancel.is_set(): raise Cancelled("Cancelled locally")
        return b"".join(parts)
    except (OSError, http.client.HTTPException):
        raise ValueError("Model connection failed or timed out; no automatic retry") from None
    finally:
        if connection is not None: connection.close()


def propose(config, payload, facts, key, cancel):
    return parse_provider_response(request_model(config, payload, key, cancel), facts, config)
