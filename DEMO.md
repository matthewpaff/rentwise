# Rentwise walkthrough

Run `python server.py` from this repository. No packages are required.

1. Start the server and compare a room with a whole apartment. Confirm that listing type stays visible.
2. Toggle optional fees and change the stay length. Inspect the known monthly cost, upfront cost, and term total separately.
3. Compare a listing with unknown fees. Its total is explicitly incomplete; the source excerpt remains visible.
4. Submit a sandbox request with consent. Retry the same request: it retains one idempotency key and one database record.
5. Reconcile after five seconds. The simulation changes pending to sandbox_confirmed; no external booking occurs.
6. Optionally configure an already-running local Ollama model, request filter suggestions, inspect them, and apply them explicitly. Model availability and quality require separate live validation.

## Review evidence

Run `python -m unittest discover -s tests -v`. Tests include a real loopback HTTP server with an isolated temporary database, malformed request handling, cross-site write denial, and the main application path. The GitHub workflow checks Python 3.11 and 3.13 on Linux and Windows; a configured workflow is not evidence that a run has passed.

The interface has been reviewed from source and HTTP responses. An automated visual browser check was unavailable in the development session. These local servers are development demonstrations. See README.md for limits.
