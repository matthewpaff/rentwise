# Workspace contracts

All state is in the SQLite file passed with `--db`. There is one local workspace, without users or access control. Back up that file while the server is stopped if you need to retain research. The application does not migrate, synchronize, verify or contact real listing sources. Tables are created additively, preserving the original sandbox booking table.

## Canonical listing

The executable example is [fee-lab.json](fee-lab.json). `id`, `name`, `area`, `kind` (`room` or `whole`), `source`, `excerpt` and ISO calendar `observed_at` are required text fields. Dates are provenance assertions, not proof of a scrape. Imported source text is rendered as text, never HTML. Unsupported currencies are rejected.

```json
{
  "id": "authored-room",
  "name": "Illustrative room",
  "area": "Fictional neighborhood",
  "kind": "room",
  "currency": "USD",
  "source": "Authored example · 2026-11-05",
  "excerpt": "Fictional room: $1,000 rent, $500 refundable deposit, internet amount unspecified.",
  "observed_at": "2026-11-05",
  "price_completeness": "partial",
  "fees": [
    {"id":"rent","label":"Rent","amount":"1000.00","cadence":"monthly","required":true},
    {"id":"deposit","label":"Deposit","amount":"500.00","cadence":"once","required":true,"refundable":true},
    {"id":"internet","label":"Internet","amount":null,"cadence":"monthly","required":true}
  ],
  "credits": []
}
```

Fee IDs must be unique. Each fee has an ID, label, amount and `monthly`/`once` cadence. `required` defaults true; `refundable` defaults false and is allowed only for one-time charges. `source` is optional per-fee text. An unknown selected charge makes the calculation incomplete; an unknown excluded optional charge does not. Canonical `price_completeness` defaults to `unspecified`. Required fee completeness cannot establish undocumented charges are absent, so an explicit complete claim is also needed. The legacy aggregate format retains its prior default inference from `unknown`, but accepts explicit `partial` or `unspecified` to withhold a completeness claim.

Credits have `label`, nonnegative `amount`, optional `source`, and `minimum_months` (default 1, range 1–60). They are one-time concessions, not recurring discounts. Eligible credits cannot exceed known nonrefundable cost. Each listing supports at most 60 fees and 20 credits. Money is nonnegative, no more than $1,000,000 per input amount, with no sub-cent precision. Lease lengths are integer months 1–60. This engine does not interpret real lease eligibility or availability.

## Filters and decisions

`budget` is a known recurring monthly cap, not a total affordability guarantee. `kind` is `all`, `room` or `whole`. `months` defaults 12. `optional` and `known_only` are strict booleans. `sort` is `total` (default), `monthly`, `effective` or `completeness`. Ranking uses exact values; tie-breaks use completeness, total cost and stable ID. With a uniform stay length, total and effective cost produce the same order. All results include source text; exclusion records explain budget, type and completeness mismatches. Source ages over 30 days and future dates produce verification warnings, not automatic exclusion.

```json
{"budget":"1800.00","kind":"whole","months":12,"optional":false,"known_only":true,"sort":"total"}
```

## HTTP routes

POST bodies are JSON objects, with only the listed fields. All routes are local. Validation failures return 400 with an `error` message; unknown routes return 404; untrusted Host/origin return 403. No HTTP response constitutes a real reservation. Collections accept 1–50 unique listing IDs. Keys are local opaque strings.

| Method / route | Body or response |
|---|---|
| GET `/api/health` | Readiness, sandbox true, model_enabled |
| GET `/api/listings` | Four bundled synthetic listings |
| GET `/api/fee-lab` | Synthetic deposit/credit scenario |
| POST `/api/evaluate` | Filter fields and optional `listings` corpus |
| POST `/api/export` | `preferences`, optional `listings`, optional `ids`, `format` (`json`/`csv`); returns content string |
| GET `/api/collections` | Active and archived collection summaries |
| POST `/api/collections/create` | `name`, `listings`, `provenance` |
| POST `/api/collections/load` | `id`, optional integer `version` (latest default) |
| POST `/api/collections/revise` | `id`, `listings`, `provenance`, integer `expected_version` |
| POST `/api/collections/versions` | `id`; immutable version metadata |
| POST `/api/collections/archive` | `id`, boolean `archived` (default true); false restores |
| POST `/api/collections/diff` | `id`, integer `before`, integer `after`; added/removed IDs and changed fields |
| GET `/api/searches` | Saved preference sets |
| POST `/api/searches/save` | `name`, validated `preferences` |
| POST `/api/searches/delete` | `id` |
| GET `/api/snapshots` | Immutable decision record summaries |
| POST `/api/snapshots/save` | `name`, `listings`, `preferences`; recomputes server-side |
| POST `/api/snapshots/load` | `id`; computed results, filters, provenance and save timestamp |
| GET `/api/bookings` | Latest 100 local sandbox requests |
| POST `/api/book` | Bundled `listing` ID, 8–100 character idempotency `key`, literal `consent:true` |
| POST `/api/bookings/status` | `key`; read without transition |
| POST `/api/bookings/events` | `key`; append-only local transition trail |
| POST `/api/reconcile` | `key`; pending → sandbox_confirmed after simulated five-second delay |
| POST `/api/bookings/cancel` | `key`, literal `consent:true`; pending/confirmed → cancelled |
| POST `/api/preferences` | `text`; configured local model filter proposal only, 503 if disabled |

Snapshots contain the full evaluated listings and calculated values at save time. They are never silently refreshed. Collection revisions retain the source `observed_at` dates; version timestamps record actual local save time independently. Archive is reversible and does not delete provenance. Saved searches contain filters only, not a corpus reference.

## Sandbox state rules

```text
new + explicit consent → pending
pending + reconcile after 5 seconds → sandbox_confirmed
pending or sandbox_confirmed + explicit cancellation consent → cancelled
cancelled → cancelled (terminal)
```

Retries with the same key and listing return the existing record even if cancelled. Reusing a key for a different listing is rejected. A second key for a listing with an active pending/confirmed request is rejected; inspect history instead. Cancelling allows a separately consented new request with a new key. SQLite transactions serialize competing transitions, and retries do not duplicate audit events. Existing databases created before audit support may contain bookings without an initial event; no historical consent event is fabricated for them.

## Module boundaries

`finance.py` validates canonical fees and computes exact costs. `engine.py` preserves aggregate compatibility and owns sandbox state. `workspace.py` stores collections, searches and snapshots. `decision.py` evaluates/ranks/filter-explains. `exports.py` emits provenance-rich JSON and formula-safe CSV. `contracts.py` enforces JSON and route contracts. `server.py` exposes local HTTP; `cli.py` uses the same deterministic engine. `app.js` and `workspace-ui.js` render text-only DOM. The optional `model_adapter.py` returns suggestions through the same preference validator; it has no action transport, database handle, cost authority or booking method.
