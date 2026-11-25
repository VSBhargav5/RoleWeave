# AI request failures and bounded waits (v0.41)

V0.40 could display a generic failure under an animated "Preparing your application
draft" screen. The request had already failed, but the screen still looked busy.
The worker discarded the cause, so that old message cannot establish whether a
key, capacity, timeout or response-format problem occurred. No old provider body
or credential was retained to reconstruct the missing cause.

## What changed

OpenRouter connections still have a five-second TCP/TLS connection timeout.
After connection, non-streaming model generation can use the remaining portion
of the 60-second request budget. Socket timeouts are updated while the connection
socket is available; deadline/cancellation checks also run before and after I/O.
A late result is refused. Cancellation prevents local adoption but cannot undo
processing already sent to a remote provider.

AI send, preview and status calls to the local host have explicit client timeouts.
Polling has a 75-second local wait limit, including a timeout on a stalled status
fetch. Tailoring shows elapsed wait time and the configured model route. A failed
request replaces the wait screen with a terminal error card; no spinner remains.
Assessment and resume organization also leave their pending states on failure.

Only a controlled diagnostic category, optional numeric HTTP status and static
explanation leave a worker. Provider error messages/bodies, metadata, credentials
and arbitrary exception text are not copied into the UI or logs. Error objects
inside HTTP-200 responses are failures too; partial output and truncated JSON are
never accepted as a successful draft.

## Codes and next actions

| Code | Meaning / next step |
| --- | --- |
| RW-AI-AUTH | HTTP 401: check the key for the selected provider, then review a new request |
| RW-AI-ACCOUNT | HTTP 402: inspect account/key budget restrictions; no automatic payment or paid fallback |
| RW-AI-PERMISSION | HTTP 403: inspect permissions and provider/account restrictions |
| RW-AI-RATE | HTTP 429: wait before a new reviewed request |
| RW-AI-UNAVAILABLE | No route/model/provider could complete this request; free JSON-capable capacity can vary |
| RW-AI-REQUEST | Request format, size or parameters were rejected; try fewer selected facts or another compatible model |
| RW-AI-TIMEOUT | The network/model request timed out; remote processing may have occurred |
| RW-AI-NETWORK / RW-AI-TLS | Connection or certificate verification failed; verification is not bypassed |
| RW-AI-OUTPUT-LIMIT | The model stopped before completing its structured response; try a smaller scope |
| RW-AI-REFUSED | A refusal/content filter stopped the response |
| RW-AI-SHAPE | Section response has the wrong fields or structure |
| RW-AI-SOURCES | Section response omits, duplicates or invents source references |
| RW-AI-TEXT-LIMIT | Section wording exceeds its displayed character/count limits |
| RW-AI-OUTPUT | The JSON or source references failed validation; no partial wording is accepted |
| RW-AI-PROVIDER / RW-AI-INTERNAL | Unclassified provider/local failure; no raw diagnostic content is exposed |
| RW-AI-WAIT | The browser's 75-second local wait expired |
| RW-LOCAL-TIMEOUT | A local AI API call did not respond in its allowed time |

**Review a new request** creates a new preview; it does not call a model. The key
field is empty and send consent is unchecked. Each further send is deliberate.
**Change selected facts** returns to the source chooser. The app never retries
automatically, changes account privacy preferences, bypasses source validation or
switches to a paid route. An uncertain sent request can still have been processed
remotely; cancellation is not evidence that no processing occurred.

The browser's Save password popup is separate from the app. Request-only storage
inside RoleWeave does not control what a browser password manager offers to save.

## Verification and limits

Offline tests cover HTTP error/status propagation, HTTP-200 error envelopes,
safe redaction, longer response waits, late-body rejection, TLS/network/timeout
classification and worker failure propagation across the three AI tools. Browser
regressions simulate a rate limit, an expired generation wait and a hung status
fetch, verifying terminal UI, cleared keys, renewed consent and no automatic send.
They use synthetic data and mocked transport. No personal key or resume is read
or transmitted by the agent, and live account acceptance remains unverified.

Official contracts inspected for this correction:
[OpenRouter errors](https://openrouter.ai/docs/api_reference/errors-and-debugging),
[structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs),
[public model catalog](https://openrouter.ai/api/v1/models).
The catalog describes capabilities, not your account's current routing capacity.


## v0.46 free-route reliability

New section-tailoring requests use 8192 output tokens instead of4096; legacy full
requests keep their prior limit. OpenRouter requests specify minimal reasoning
and the free response-healing formatting plugin. Exact previews include both;
only approved payloads are sent, without automatic retries or paid fallback.
Response healing repairs syntax, not source truth. The app still rejects output
with a length stop, unsupported schema or unknown citations. Complete fenced JSON
is accepted only as a whole document; malformed output has RW-AI-JSON diagnostics.

HTTP429 Retry-After (seconds or HTTP date) is reduced to a bounded numeric delay.
Missing/unusable hints use a60-second local safeguard, not a claim about quota
reset. Tailoring blocks immediate sends on the same route for that interval,
including across newly prepared previews. Quotas may last longer and process
restart resets the local safeguard. No credential or provider-body text appears
in diagnostics. There is no live-model guarantee from the synthetic tests.

References: [Reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens),
[Response healing](https://openrouter.ai/docs/guides/features/plugins/response-healing),
[Free plugin cost](https://openrouter.ai/blog/announcements/response-healing-reduce-json-defects-by-80percent/),
[Rate limits](https://openrouter.ai/docs/api_reference/limits).
