# Rentwise

A source-aware rental decision dashboard and local booking simulation, created November 5, 2026. The four San Diego listings, addresses implied by neighborhoods, prices and source excerpts are **synthetic sample data**, authored for this project on that date. They are not collected offers or evidence of historical work. Architecture illustrations are CSS, not property photographs.

## Run

Requires Python 3.10+; no packages, credentials or installation needed.

```powershell
cd rentwise
python server.py
```

Open http://127.0.0.1:8761. Alternate port/database: `python server.py --port 8762 --db sandbox-test.sqlite3`. Stop with Ctrl+C. The application binds only to IPv4 loopback. `GET /api/health` reports readiness and model configuration. The generated SQLite file is ignored by Git.

```powershell
python -m unittest discover -s tests -v
```

## What works

- Filter room versus entire place, monthly known-cost budget, stay length and fee completeness. Include optional services explicitly.
- Calculate recurring base plus required charges, optional recurring charges if selected, and one-time upfront costs using Python `Decimal`. Monthly cost × term + upfront = known total. Unspecified fees never become zero-cost or a claim of a complete price. Upfront fees in the sample are nonrefundable fees, not deposits.
- Compare up to three visible homes, including source ID, dated provenance, exact source excerpt, unknown fees and optional fee handling.
- Edit the full JSON listing corpus in the UI. Server validates money, required fields, listing types and unique IDs. Imported data is session-only; booking is limited to bundled synthetic IDs. This is a structured-data engine; it does not parse real listings or verify claims.
- Create a consent-gated sandbox request. The browser reuses its idempotency key on retries; SQLite enforces uniqueness across restarts. Conflicting reuse is rejected. An acknowledgement intentionally stays pending until you reconcile after five seconds. Reconciliation produces `sandbox_confirmed` with no payment, external request, host contact or reservation. A page refresh loses the browser's active key; the record remains in SQLite, and the API can reconcile a known key. The demo does not implement cancellation, accounts or real provider reconciliation.

## Optional real local model integration

The default workflow is deterministic and calls no model. An optional Ollama adapter sends a structured extraction request to **http://127.0.0.1:11434/api/chat** only. You must separately install/run Ollama and have a model available; this project neither installs nor downloads models.

```powershell
python server.py --ollama-model YOUR_INSTALLED_MODEL
```

Open “Optional local model assistant,” enter a preference, click the explicit model button, inspect its JSON, then apply it. Only that opt-in prompt is sent to local Ollama. A model suggests filters; trusted validation, cost arithmetic and booking consent stay outside it. No remote provider is configured. `model_adapter.py` implements the HTTP boundary with JSON output, a 15-second timeout, a 64 KiB response cap, disabled proxies and redirects. `engine.ModelAdapter` documents the provider-independent contract. Transport-injected tests exercise structured output, invalid model fields and failure without making network requests. Actual model quality/availability has not been tested.

## Architecture and API

`server.py` provides an allowlisted static server and JSON routes. `engine.py` owns validated Decimal costs and transactional SQLite state. `model_adapter.py` owns optional model I/O. `app.js` builds UI nodes with textContent rather than interpolating untrusted HTML. `style.css` provides the responsive dashboard. There are no third-party assets or dependencies.

| Route | Purpose |
|---|---|
| GET /api/listings | Bundled synthetic corpus |
| POST /api/evaluate | Optional listings array and filters: budget, kind, months, optional, known_only |
| POST /api/book | Sample listing ID, explicit boolean consent, idempotency key |
| POST /api/reconcile | Resolve an existing sandbox key after simulated delay |
| POST /api/preferences | Optional configured local model filter suggestion |

Requests require JSON objects and are capped at 100 KB. Responses use a restrictive same-origin CSP; cross-origin browser POSTs are rejected. Static file serving is allowlisted. These are defense-in-depth measures for a **local development demo**, not a production authentication or security model. The stdlib server has no TLS, user identities, deployment hardening, rate limiting, model concurrency controls or real listing integrations. Do not expose it publicly. Public repository hosting is distinct from running this server publicly.

## Provenance

`data.json` contains all four authored source excerpts, IDs and creation/observation date (2026-11-05). “Observed” means the date this synthetic fixture was created, not a scrape or a visit to an actual property. No historical experience, deployment, users or benchmark results are claimed. Prices are illustrative USD and do not constitute rental guidance.

## Demo and review

See [DEMO.md](DEMO.md) for a repeatable walkthrough and the distinction between measured checks and simulated records. See [HISTORY.md](HISTORY.md) for project provenance.
