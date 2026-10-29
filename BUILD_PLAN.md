# BoundaryLab execution checkpoint — 30 October 2026

## Decision

Continue BoundaryLab, the submitted Hack in Hills idea, within the bounded local prototype scope. Rahul evaluates behaviour and records/submits; Codex implements and investigates failures. Do not call an unmeasured security feature complete.

## Implemented now

Persistent operator app, SQLite history, scoped expiring credentials, run lifecycle, fail-closed gate, evidence anchoring/export/verification, fixed Docker controller, private-network fixtures, scoped container broker, real llama.cpp container adapter, fresh-session protocol, cleanup, responsive dashboard, CLI, Windows/Linux launchers and security/integration tests.

## What is verified

See `docs/VALIDATION.md`. Corrected live Docker/model run 26a4c588d5fa07ce19023dbd passed all six bounded checks on Rahul's PC. The generated-answer parser and SQLite connection cleanup fixes are included. 25 regression tests passed on Windows. Preserve the old runs as historical evidence, but do not present their pre-fix fresh-session PASS as a validated result.

## Next, on Rahul's PC

1. Extract this folder. Run `py -3 server.py`. Paste terminal token into local UI. Run weak control; confirm INVALID; test altered evidence.
2. Install/start Docker Desktop with Linux containers and WSL2. Run `py -3 cli.py prepare`, then `py -3 cli.py doctor`.
3. Run hardened checks without a model. Confirm actual network and broker results; retain INCONCLUSIVE for model checks. Investigate errors before adding scope.
4. Obtain an appropriately licensed small instruction-tuned GGUF; run `prepare --with-model`; set `BOUNDARYLAB_MODEL` before starting the app.
5. Run hardened checks with actual inference. Inspect all six requirements. Do not accept VALID if a positive control is missing or if a required check errored.
6. Reproduce on a fresh data directory, stop gracefully and confirm cleanup. Keep the original checkpoint separately. Export evidence.
7. Capture the demo, update the pitch to exactly match measured results, prepare a public GitHub repository without model weights/data/tokens, and submit current required links.

## Freeze

No new framework integrations, multi-agent orchestration, public deployment, arbitrary attack execution, Kubernetes or broad benchmark ingestion before this sequence passes. If model compatibility is slow, preserve honest partial results rather than replacing inference with a fake.

## Learning alongside implementation

Rahul should be able to explain container versus VM, scoped HTTP authorization, shared-kernel trust, distinct private networks, hash chains plus independent checkpoints, why missing evidence is inconclusive and why canary absence is bounded. Practice starting/stopping the app and explaining one failed check from its actual evidence.
