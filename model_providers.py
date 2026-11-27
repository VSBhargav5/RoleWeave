"""Explicit structured-output provider contracts; fixed cloud hosts or numeric loopback."""
import hashlib
import http.client
import json
import re
import time
import ssl
from email.utils import parsedate_to_datetime

from ai_tailoring import parse_response, validate_draft
from network_io import Cancelled, json_object
from runtime_paths import APP_VERSION

KINDS = {"openrouter": "OpenRouter (free models only)", "openai": "OpenAI", "anthropic": "Anthropic", "mistral": "Mistral", "ollama": "Ollama (loopback)", "lmstudio": "LM Studio / compatible (loopback)"}
DEFAULT = {"kind": "openrouter", "model": "openrouter/free", "port": 0}
LOCAL = {"ollama", "lmstudio"}

# Only controlled categories leave a worker. Provider bodies and exception text
# may contain credentials or resume text and must never become UI diagnostics.
ERRORS = {
    'section_shape': ('RW-AI-SHAPE', 'The model returned valid JSON but the wrong section structure. No wording was accepted. A complete cited headline/summary or selected-entry response is required.'),
    'section_references': ('RW-AI-SOURCES', 'The model omitted, duplicated or invented a source reference. No wording was accepted. Source IDs must come from the selected facts; this is not an input-size error.'),
    'section_length': ('RW-AI-TEXT-LIMIT', 'The returned wording exceeded a section limit: headline 120 characters, summary 1200, each experience edit 700, letter intro 900, closing 300, each question 200. No wording was accepted. Request shorter wording; fewer selected facts are not required for this error.'),
    'authentication': ('RW-AI-AUTH', 'The provider rejected the API key. Check that it is valid and belongs to the selected provider, then review a new request.'),
    'account_limit': ('RW-AI-ACCOUNT', 'The provider refused the account or key budget. Check your account/key limits. No automatic retry or fallback was attempted.'),
    'forbidden': ('RW-AI-PERMISSION', 'The provider refused this request. Check account permissions and provider/privacy restrictions; the app has not changed them.'),
    'rate_limited': ('RW-AI-RATE', 'The provider rate-limited this request. Wait before reviewing a new request. No automatic retry or paid fallback was attempted.'),
    'cooldown': ('RW-AI-COOLDOWN', 'A previous request on this route was rate-limited. This send was held locally; no new provider request was made.'),
    'unavailable': ('RW-AI-UNAVAILABLE', 'No available model/provider route could complete this request. Free endpoints with the required JSON support may be unavailable. Try later or choose another compatible free model.'),
    'request_rejected': ('RW-AI-REQUEST', 'The provider rejected the request format, size or parameters. Try fewer selected facts or another model that supports the required structured output.'),
    'timeout': ('RW-AI-TIMEOUT', 'The model request timed out. Remote processing may have occurred. No result was accepted; review a new request before another attempt.'),
    'network': ('RW-AI-NETWORK', 'The model connection failed. Check connectivity to the selected provider. No automatic retry was attempted.'),
    'tls': ('RW-AI-TLS', 'The secure provider connection could not be verified. Check your network and system certificate setup; verification was not bypassed.'),
    'output_limit': ('RW-AI-OUTPUT-LIMIT', 'The model stopped at its output limit before completing the draft. The budget may include internal reasoning. Use a smaller section or an exact JD excerpt for assessment, or choose a compatible model. Partial output was not accepted.'),
    'refused': ('RW-AI-REFUSED', 'The model refused this request or its content filter stopped the response. No wording was accepted.'),
    'invalid_output': ('RW-AI-OUTPUT', 'The model response did not meet the required JSON or source-reference checks. No wording was accepted. Try fewer facts or another compatible model.'),
    'invalid_json': ('RW-AI-JSON', 'The model returned malformed JSON instead of a complete structured draft. No wording was accepted. Choose another compatible free model; selecting fewer facts does not guarantee valid JSON.'),
    'provider_error': ('RW-AI-PROVIDER', 'The provider returned an error or unusable response. No wording was accepted. Review a new request before trying again.'),
    'internal': ('RW-AI-INTERNAL', 'The request could not complete locally. No wording was accepted. Reopen the request; diagnostic contents were not logged.'),
}


class ModelError(ValueError):
    def __init__(self, code, http_status=None, retry_after=None):
        self.code = code if isinstance(code, str) and code in ERRORS else 'provider_error'
        self.http_status = http_status if type(http_status) is int and 400 <= http_status <= 599 else None
        self.retry_after = min(86400,max(1,retry_after)) if type(retry_after) is int else None
        super().__init__(ERRORS[self.code][1] + (f' (HTTP {self.http_status})' if self.http_status else '') + (f' Wait at least {self.retry_after} seconds.' if self.retry_after else ''))


def http_error(status):
    code = {400: 'request_rejected', 401: 'authentication', 402: 'account_limit', 403: 'forbidden',
            404: 'unavailable', 408: 'timeout', 413: 'request_rejected', 422: 'request_rejected',
            429: 'rate_limited', 500: 'unavailable', 502: 'unavailable', 503: 'unavailable', 504: 'timeout'}.get(status, 'provider_error')
    return ModelError(code, status)


def failure_info(exc, default='internal'):
    safe = ModelError(exc.code, exc.http_status,exc.retry_after) if isinstance(exc, ModelError) else ModelError(default)
    result = {'error_code': ERRORS[safe.code][0], 'error': str(safe)}
    if safe.http_status: result['http_status'] = safe.http_status
    if safe.retry_after:result['retry_after']=safe.retry_after
    return result


def response_error(value):
    if not isinstance(value, dict): return ModelError('provider_error')
    status = value.get('code')
    if type(status) is int and 400 <= status <= 599: return http_error(status)
    types = {'authentication': 'authentication', 'rate_limit_exceeded': 'rate_limited',
             'provider_overloaded': 'unavailable', 'provider_unavailable': 'unavailable',
             'max_tokens_exceeded': 'output_limit', 'refusal': 'refused', 'invalid_request': 'request_rejected'}
    metadata = value.get('metadata')
    kind = metadata.get('error_type') if isinstance(metadata, dict) else None
    return ModelError(types.get(kind, 'provider_error') if isinstance(kind, str) else 'provider_error')


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {"kind", "model", "port"}:
        raise ValueError("Provider preferences accept kind, model and port only; no credentials")
    if not isinstance(config["kind"], str) or config["kind"] not in KINDS: raise ValueError("Unsupported model provider")
    if not isinstance(config["model"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,199}", config["model"]):
        raise ValueError("Enter a model identifier of at most 200 ASCII characters")
    if type(config["port"]) is not int or (config["kind"] in LOCAL and not 1 <= config["port"] <= 65535) or (config["kind"] not in LOCAL and config["port"] != 0):
        raise ValueError("Use a numeric loopback port for local servers, or zero for fixed cloud providers")
    if config['kind'] == 'openrouter' and config['model'] != 'openrouter/free' and not config['model'].endswith(':free'):
        raise ValueError('Choose openrouter/free or an exact model ID ending in :free; paid OpenRouter routes are refused')
    return config


def destination(config):
    validate_config(config)
    kind = config["kind"]
    if kind == "openai": return "https://api.openai.com/v1/responses"
    if kind == "anthropic": return "https://api.anthropic.com/v1/messages"
    if kind == "mistral": return "https://api.mistral.ai/v1/chat/completions"
    if kind == "openrouter": return "https://openrouter.ai/api/v1/chat/completions"
    return "http://127.0.0.1:" + str(config["port"]) + ("/api/chat" if kind == "ollama" else "/v1/chat/completions")


def request_payload(original, config):
    validate_config(config); base = json_object(original)
    budget=base.get('max_output_tokens',4096)
    if type(budget) is not int or not 1<=budget<=8192:raise ValueError('Unsupported model output budget')
    if config["kind"] == "openai":
        result = dict(base, model=config["model"])
    else:
        messages = [{"role": "system", "content": base["instructions"]}, {"role": "user", "content": base["input"][0]["content"]}]
        schema = base["text"]["format"]["schema"]
        if config["kind"] == "anthropic":
            result = {"model": config["model"], "max_tokens": budget, "stream": False, "system": base["instructions"],
                      "messages": messages[1:], "output_config": {"format": {"type": "json_schema", "schema": schema}}}
        elif config["kind"] == "ollama":
            result = {"model": config["model"], "messages": messages, "stream": False, "format": schema, "options": {"num_predict": budget}}
        else:
            result = {"model": config["model"], "messages": messages, "stream": False, "max_tokens": budget,
                      "response_format": {"type": "json_schema", "json_schema": {"name": "application_draft", "strict": True, "schema": schema}}}
    if config['kind'] == 'openrouter':
        result['reasoning']={'effort':'minimal'}
        result['plugins']=[{'id':'response-healing'}]
        result['provider'] = {'require_parameters': True, 'allow_fallbacks': False,
                              'max_price': {'prompt': 0, 'completion': 0, 'request': 0}}
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


def structured_response(payload, config):
    validate_config(config)
    if not isinstance(payload, bytes) or len(payload) > 1024 * 1024: raise ValueError("Model response exceeds 1 MiB")
    if config["kind"] == "openai":
        result=json_object(payload)
        if not isinstance(result,dict) or result.get('status')!='completed':raise ValueError('Model response incomplete or refused')
        output=result.get('output')
        if not isinstance(output,list) or len(output)!=1 or not isinstance(output[0],dict):raise ValueError('Unsupported model output')
        message=output[0];content=message.get('content')
        if message.get('type')!='message' or message.get('role')!='assistant' or message.get('status')!='completed' or not isinstance(content,list) or len(content)!=1 or not isinstance(content[0],dict) or content[0].get('type')!='output_text' or not isinstance(content[0].get('text'),str):
            raise ValueError('Unsupported model message')
        return json_object(content[0]['text'].encode())
    result = json_object(payload)
    if not isinstance(result, dict): raise ValueError("Unsupported model response")
    if 'error' in result: raise response_error(result['error'])
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
        if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
            if 'error' in choices[0]: raise response_error(choices[0]['error'])
            if choices[0].get('finish_reason') == 'length': raise ModelError('output_limit')
            if choices[0].get('finish_reason') == 'content_filter': raise ModelError('refused')
            if choices[0].get('finish_reason') == 'error': raise ModelError('provider_error')
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict) or choices[0].get("finish_reason") != "stop": raise ValueError("Model response incomplete or refused")
        message = choices[0].get("message")
        if isinstance(message, dict) and message.get('refusal'): raise ModelError('refused')
        if not isinstance(message, dict) or message.get("role") != "assistant" or message.get("tool_calls") or message.get("refusal"): raise ValueError("Unsupported model message")
        value = message.get("content")
    if not isinstance(value, str): raise ValueError("Model did not return JSON text")
    # Some compatible endpoints wrap otherwise valid JSON in one Markdown fence.
    # Accept only the entire fenced document, never a fragment or truncated output.
    if kind=='openrouter':
        fenced=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',value,re.S|re.I)
        if fenced:value=fenced[1]
    try:return json_object(value.encode())
    except ValueError:raise ModelError('invalid_json') from None


def parse_provider_response(payload, facts, config):
    try:
        return validate_draft(structured_response(payload,config),facts)
    except ModelError:
        raise
    except (ValueError, KeyError, TypeError):
        raise ModelError('invalid_output') from None


def request_model(config, payload, key, cancel):
    validate_config(config); validate_key(config, key)
    if not isinstance(payload, bytes) or len(payload) > 256 * 1024: raise ValueError("Model request exceeds 256 KiB")
    kind = config["kind"]
    if kind == 'openrouter':
        body = json_object(payload)
        policy = {'require_parameters': True, 'allow_fallbacks': False, 'max_price': {'prompt': 0, 'completion': 0, 'request': 0}}
        if (not isinstance(body, dict) or body.get('model') != config['model'] or body.get('provider') != policy
                or body.get('reasoning',{'effort':'minimal'}) != {'effort':'minimal'}
                or body.get('plugins',[{'id':'response-healing'}]) != [{'id':'response-healing'}]
                or set(body) - {'model', 'messages', 'stream', 'max_tokens', 'response_format', 'provider','reasoning','plugins'}):
            raise ValueError('OpenRouter request must retain the reviewed free-only routing policy')
    path = {"openrouter": "/api/v1/chat/completions", "openai": "/v1/responses", "anthropic": "/v1/messages", "mistral": "/v1/chat/completions", "ollama": "/api/chat", "lmstudio": "/v1/chat/completions"}[kind]
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "RoleWeave/" + APP_VERSION}
    if key: headers["Authorization"] = "Bearer " + key
    if kind == "anthropic": headers["anthropic-version"] = "2026-10-21"
    connection = None; deadline = time.monotonic() + 60
    def check():
        if cancel.is_set(): raise Cancelled('Cancelled locally')
        if time.monotonic() >= deadline: raise ModelError('timeout')
    def response_timeout():
        check()
        if kind == 'openrouter' and connection.sock is not None:
            connection.sock.settimeout(max(0.001, deadline - time.monotonic()))
    try:
        check()
        if kind in LOCAL: connection = http.client.HTTPConnection("127.0.0.1", config["port"], timeout=5)
        else: connection = http.client.HTTPSConnection({"openrouter": "openrouter.ai", "openai": "api.openai.com", "anthropic": "api.anthropic.com", "mistral": "api.mistral.ai"}[kind], timeout=5)
        if kind == 'openrouter':
            # Establish TCP/TLS with the existing five-second connect timeout,
            # then allow non-streaming generation the remaining request budget.
            connection.connect()
        response_timeout()
        connection.request("POST", path, body=payload, headers=headers)
        response_timeout()
        response = connection.getresponse()
        check()
        if response.status != 200:
            error=http_error(response.status)
            if response.status==429:
                hint=response.getheader('Retry-After','')
                try:delay=int(hint) if re.fullmatch(r'[0-9]{1,8}',hint or '') else int(parsedate_to_datetime(hint).timestamp()-time.time())
                except (ValueError,TypeError,OverflowError):delay=60
                error.retry_after=min(86400,max(1,delay))
            raise error
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json": raise ModelError('provider_error')
        parts = []; size = 0
        while True:
            response_timeout()
            part = response.read1(min(65536, 1024 * 1024 + 1 - size))
            if not part: break
            parts.append(part); size += len(part)
            if size > 1024 * 1024: raise ModelError('invalid_output')
        if getattr(response,"length",None) not in (None,0): raise ModelError('provider_error')
        check()
        return b"".join(parts)
    except ssl.SSLError:
        raise ModelError('tls') from None
    except TimeoutError:
        raise ModelError('timeout') from None
    except (OSError, http.client.HTTPException):
        raise ModelError('network') from None
    finally:
        if connection is not None: connection.close()


def propose(config, payload, facts, key, cancel):
    return parse_provider_response(request_model(config, payload, key, cancel), facts, config)
