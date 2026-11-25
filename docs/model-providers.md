# Choose a drafting provider

V0.26 adds non-secret model preferences for application drafting. Open Settings &
backup, choose a provider and enter the exact model identifier available to you.
Saving makes no network request. V0.39 defaults to OpenRouter free when no provider
preference exists; previously saved selections are preserved. The free preset
switches an existing configuration explicitly. See [setup and limits](resume-import-and-free-models.md).
Other models are not recommended by cost or claimed compatible without your trial.

| Selection | Fixed destination / contract |
| --- | --- |
| OpenRouter free | HTTPS openrouter.ai/api/v1/chat/completions; openrouter/free or :free IDs only, zero price caps, JSON-schema support required, provider fallback disabled |
| OpenAI | HTTPS api.openai.com/v1/responses; selected model, store=false |
| Anthropic | HTTPS api.anthropic.com/v1/messages; 2026-10-21 API, Bearer key, output_config JSON schema |
| Mistral | HTTPS api.mistral.ai/v1/chat/completions; response_format JSON schema |
| Ollama | HTTP 127.0.0.1:port/api/chat; stream=false, format JSON schema |
| LM Studio / compatible | HTTP 127.0.0.1:port/v1/chat/completions; JSON schema |

For a local server, start it yourself, load a model supporting JSON-schema output,
and use its numeric port (commonly11434 for Ollama,1234 for LM Studio). RoleWeave
never starts/downloads a model or discovers endpoints. Only numeric127.0.0.1 is
accepted: no LAN address, DNS hostname, arbitrary cloud URL or proxy. A server
running on your computer can forward requests elsewhere; check its configuration.
Loopback is a destination boundary, not proof of fully offline processing.

## One reviewed request

Open a saved application, choose Tailor with AI and select reviewed facts. The
preview shows the exact destination, model and provider-specific JSON. Only selected
claims and the posting/instruction/previous proposal are included; contact values,
private source notes and unselected facts are excluded as before. The preview
freezes its configuration; changing Settings in another tab cannot reroute it.
The request fingerprint binds endpoint and payload. Re-preview to use new settings.

Enter a masked key for this send only (optional token for local servers), review
and explicitly consent. No file/environment key lookup, reuse, model-list request,
automatic test request, fallback, retry, redirect, tools or execution is added.
Keys are never stored in preferences, drafts, bundles or history. Input clears on
send/back/close; this is not a process-memory erasure guarantee.

Cloud charges/retention depend on your account. store=false is not zero retention.
Cancellation discards late results locally but cannot undo remote work or charges.
Requests are bounded256KiB, responses1MiB, output cap4096tokens, local deadline60s
with5s blocking-I/O timeouts. Unsupported, incomplete, refused, tool-call, malformed
or uncited results fail without accepting a partial draft. No silent output repair.
Human accuracy review remains necessary: a citation is not evidence of truth.
Accepted v2 drafts retain provider/model/port provenance; v1 drafts still load.

Only config(kind/model/port) is stored in the shelf's app_settings row. The managed
recovery ZIP includes a validated model-settings.json and restores into its new
workspace. Older bundles still work/default to OpenAI. Database-only record backups
do not include this preference; use the managed bundle. No credentials travel.

## Runnable offline verification and focused practice

```powershell
.build-venv/Scripts/python.exe -m unittest discover -s tests -p test_model_providers.py -v
```

The transport test uses an owned synthetic HTTP server on127.0.0.1, not a model.
Cloud contracts are mocked. No live API/model compatibility, quality, cost or account
acceptance has been established. Providers/models may reject structured output;
choose a compatible model rather than assuming an OpenAI-compatible URL guarantees it.

In a separate offline practice shelf, save Ollama/synthetic-local-model, reload and
predict the destination. Preview an application request, then change preferences
in another tab. Explain why the already reviewed request still names its original
destination. Run only the labelled offline fixture. Compare the wording with the
selected project fact, accept one corrected sentence and inspect recovery into a
separate workspace. Tradeoff: no arbitrary endpoint flexibility, but a smaller
explicit transmission boundary. No learning or personal usefulness is claimed.

## Primary contracts inspected16November2026

- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create) and
  [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
- [Mistral Chat](https://docs.mistral.ai/api/endpoint/chat).
- [Ollama chat](https://docs.ollama.com/api/chat) and
  [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
- [LM Studio JSON-schema output](https://lmstudio.ai/docs/developer/openai-compat/structured-output).
- [OpenAI Responses](https://developers.openai.com/api/reference/resources/responses).
