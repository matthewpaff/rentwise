> **Illustrative Git calendar:** 2023-04-03 through 2025-10-24, assigned November 6, 2026.
> Actual development occurred in November 2026. These dates are simulated,
> not evidence of historical work or employment. This supersedes older
> statements below about actual Git dates. See [HISTORY.md](HISTORY.md).

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
- Edit the JSON listing corpus, save it as a persistent local collection, append immutable revisions with provenance, compare version diffs, and archive or restore the collection. A revision requires the expected current version, preventing concurrent edits from overwriting each other. Booking remains limited to bundled synthetic IDs; imported assertions are not verified.
- Save reusable search preferences and immutable comparison snapshots. Export selected comparisons as source-cited JSON or CSV with spreadsheet formula prefixes escaped. Rank by known lease expense, recurring monthly cost, effective monthly expense or explicit completeness; inspect exclusion reasons, budget headroom and stale-source warnings.
- Create a consent-gated sandbox request. Persistent idempotency and active-listing deduplication protect retries. Requests stay pending until reconciliation after five seconds. History, current status and transition audit records survive refresh. Explicit cancellation moves a request to a terminal `cancelled` state. No payment, external reservation or host contact occurs.

## Canonical fees and lease arithmetic

The original aggregate JSON format remains supported. The canonical format uses individual `fees` with monthly or one-time cadence, required/optional flags and refundable deposit flags. Canonical money accepts decimal strings or integers, never binary floats, and supports USD only. Unknown amounts use `null`. Explicit `price_completeness` is `complete`, `partial` or `unspecified`; canonical input defaults to unspecified. A complete claim cannot contain an unknown required charge.

Known lease expense = selected monthly charges × months + selected nonrefundable one-time charges − eligible credits. Refundable deposits appear in cash outlay and move-in cash, not expense. Credits apply only when their minimum lease length is reached; they do not reduce the conservative move-in cash estimate. Effective monthly expense is displayed with ROUND_HALF_UP to cents; exact totals drive ranking. No interest, taxes inferred from location, prorating, deposit deductions or currency conversions are assumed.

Choose **Explore deposit & credit sample** for the authored `fee-lab.json` scenario. At 12 months without parking it has $18,545 known expense, $800 refundable deposit and $19,345 known cash outlay. This additional sample was authored November 5, 2026 and is not bookable. See [WORKSPACE.md](WORKSPACE.md) for schema and route examples.

## Command-line evaluation

```powershell
python cli.py --kind room --budget 1200 --months 12
python cli.py --input fee-lab.json --optional --format csv --sort effective
Get-Content -Raw data.json | python cli.py --input - --known-only
```

The CLI performs no actions and calls no model. It reads UTF-8 files or stdin, bounds input to 100 KB, emits UTF-8 JSON/CSV, and reports validation errors to stderr with exit code 2. Stdout redirection can use your shell's own encoding rules; direct subprocess output is UTF-8.

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

Requests require JSON objects and are capped at 100 KB. Duplicate fields, nonfinite JSON constants, excessive nesting, unsupported action fields and ambiguous request framing are rejected. Host headers must match the actual loopback address/name and server port; foreign browser origins are rejected. Static files are allowlisted and responses set a restrictive same-origin CSP. These measures support a local development demo. The stdlib server has no TLS, authentication, rate limiting, per-user isolation or real listing integrations. Do not expose it publicly. Public source hosting is distinct from running this server publicly. Saved data is local plaintext SQLite; anyone with access to the local server can read or change it. No storage quota or automatic retention policy is implemented.

Tests include financial boundaries, provenance retention, concurrent version conflicts, booking deduplication/state races, strict HTTP inputs, exports, CLI Unicode output and a fake loopback Ollama server. The fake server checks the actual HTTP envelope, response bounds and redirect refusal; it does not run a model or measure model quality. Browser JavaScript receives syntax checks; full automated visual/browser testing is not included.

## Provenance

`data.json` contains all four authored source excerpts, IDs and creation/observation date (2026-11-05). “Observed” means the date this synthetic fixture was created, not a scrape or a visit to an actual property. No historical experience, deployment, users or benchmark results are claimed. Prices are illustrative USD and do not constitute rental guidance.

## Demo and review

See [DEMO.md](DEMO.md) for a repeatable walkthrough and the distinction between measured checks and simulated records. See [HISTORY.md](HISTORY.md) for project provenance.
