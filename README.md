# BoundaryLab

**Evidence before confidence.** An operator console for checking the environment behind an AI evaluation.

Team **God's Favorite** · Rahul Gautam · Hack in Hills ’26

## Start the app

Requires Python 3.12+; the local application has no third-party Python dependencies.

Windows PowerShell:

```powershell
cd boundarylab
py -3 server.py
```

macOS / Linux:

```sh
cd boundarylab
python3 server.py
```

Open **http://127.0.0.1:8080** and paste the operator token printed in the terminal. The token stays in the current browser page's memory and resets when the page reloads. A new random operator token is generated each server start. There is no default password. Windows users can also double-click `start.bat` after installing Python.

Click **Weak positive control**, then **Run hardened checks**. Run history survives restart in the local data directory. If Docker is missing, hardened execution intentionally stays **INCONCLUSIVE**. Weak is an explicitly synthetic in-process authorization control and produces **INVALID**; it does not deploy a vulnerable network.

## What this version implements

- Local authenticated operator UI, run history, measured check details and evidence export.
- SQLite runs, explicit lifecycle, role/run/expiry-scoped opaque credentials stored as hashes.
- Fixed-profile trusted host Docker controller; separate private red/blue/model networks; broker connected to each necessary network.
- Disposable non-root network fixtures with read-only root filesystem, dropped capabilities, resource limits and no Docker socket.
- Actual worker HTTP implementation with fixed operations and strict schemas; no arbitrary URL/command proxy.
- Connectivity positive controls, denied direct connections by DNS and IP, one bounded egress probe, and observed container security configuration.
- Real CPU inference adapter using the official llama.cpp light image, a local GGUF file, read-only weights and a separate container for every invocation.
- Synthetic exact-token positive control, bounded fresh-session carryover check and a legitimate inference example. The model outcome is not a comprehensive safety score.
- Canonical event hash chain and separately retained operator checkpoints; altered-copy test; CLI verification against an explicitly supplied original checkpoint.
- Fail-closed final verdicts. Missing, errored or unmeasured checks do not pass. Confirmed boundary violation halts model execution.

## Verification status — 30 October 2026

**A corrected live local run completed on the developer's Windows machine with all six bounded checks passing.** Run `26a4c588d5fa07ce19023dbd`, controller 0.2.2, used Docker Desktop 4.97.0 / Engine 29.9.2 and Qwen2.5-0.5B-Instruct Q4_K_M. The model answered “Two plus two equals four.” Generated-answer-only canary detection passed its positive control; the canary was absent from the clean invocation. Three distinct inference containers exited successfully and cleanup passed.

The exported event chain was recomputed and matched its included checkpoint. This establishes internal consistency, not independent external attestation. No complete claim of model safety or universal isolation is made.

25 regression tests passed locally and on the developer's Windows/Python 3.15 setup. This source package also closes HTTPError response handles to address the test cleanup warnings seen on Windows. Browser screenshots confirmed the connected dashboard and a 6/6 completed run. The on-screen altered-copy workflow still needs final demonstration; automated API/CLI tamper checks pass. See `docs/VALIDATION.md` for scope.

This is a local hackathon prototype, not a production sandbox or security certification.

## Enable the real Docker checks

1. Install and start Docker Desktop with Linux containers on Windows/macOS, or Docker Engine on Linux. On Windows, enable the WSL2 backend and allocate sufficient memory. Use a **local Docker context**, because model weights are mounted from this machine.
2. From this project directory build the small probe image:

```powershell
py -3 cli.py prepare
py -3 cli.py doctor
```

Use `python3` in place of `py -3` on macOS/Linux. The prepare step downloads the Python base image; it is not an offline operation.

3. Start the app and run hardened checks. Without weights, network and broker measurements can execute, but the final verdict stays INCONCLUSIVE because model checks are missing.

## Enable real model checks

Obtain a compatible **small instruction-tuned GGUF** from its original publisher or a trusted distributor. Check its licence and provenance. For a 16 GB RAM laptop, start with a small quantized model around 0.5–1.5 billion parameters; speed and exact compatibility need measurement. No model weights are bundled, and no specific model has been validated in this workspace.

Pull the official llama.cpp image using:

```powershell
py -3 cli.py prepare --with-model
```

Set an absolute path **in the same terminal that starts the app**:

```powershell
$env:BOUNDARYLAB_MODEL = 'C:\models\your-small-instruct-model.gguf'
py -3 server.py
```

macOS/Linux equivalent:

```sh
export BOUNDARYLAB_MODEL=/absolute/path/to/model.gguf
python3 server.py
```

The controller records the GGUF SHA-256, size and resolved image ID before workload execution; runs use the resolved local image IDs instead of mutable tags. Each of three sequential model invocations has a four-minute timeout and a 4 GB memory limit. The CLI uses single-turn mode. If image flags, permissions or model compatibility fail, the result is an error, not a pass. Model mounts need Docker file-sharing access; commas in paths are unsupported by the current mount argument.

The first model invocation must reproduce a random canary to establish detector sensitivity. If it cannot, the fresh-session result is ERROR/inconclusive. Canary absence in the clean invocation does not prove all memory was erased. Model output shown in the UI is from a fixed synthetic arithmetic prompt; user secrets are never required.

## Tests

```powershell
py -3 -m unittest discover -s tests -v
```

Tests with mocked runtimes are controller regression tests, **not live container evidence**. `test_worker.py` starts the actual HTTP worker in a separate local process; it does not prove container isolation. The production UI starts no background Docker activity until an authenticated operator requests a run.

## CLI and evidence verification

```powershell
py -3 cli.py doctor
py -3 cli.py run --profile weak
py -3 cli.py run --profile hardened
py -3 cli.py export RUN_ID --output evidence.json
py -3 cli.py verify evidence.json --checkpoint data/operator-checkpoints/RUN_ID.json
```

Checkpoint and database are separate files owned by the operator; workloads receive neither. For independent review, retain the original checkpoint on another trusted medium before sharing or editing evidence. A checkpoint supplied by the same party as an altered chain is not independent proof. The host operator remains trusted and can replace both files. The CLI verifies the event chain, not arbitrary unanchored JSON summary fields. The server reconstructs completed result fields from the retained anchored event stream.

Run **one controller process per data directory**. Don’t run the server and CLI execution simultaneously against the same directory. Exporting is read-only apart from initial schema setup. The app supports one live evaluation per server, not distributed concurrency. Do not publicly expose the local HTTP service.

## If interrupted

Use Ctrl+C for graceful shutdown; the server waits for the active controller to clean up. A hard kill or host crash can leave runs incomplete and Docker resources behind. They remain INCONCLUSIVE, never automatically resumed or marked complete. Inspect resources labelled `boundarylab.run` using Docker Desktop, then remove only the containers/networks belonging to that interrupted run. Do not globally prune Docker. Start a new run after cleanup. Automatic crash recovery and checkpoint disaster recovery are outside this prototype.

## Scope and trust

The host kernel, Docker daemon, controller, broker, verifier and original operator checkpoint are trusted. Docker shares its host kernel. Probe endpoints are network fixtures; they are not a general red-team attack execution service. The blue endpoint authorizes a configuration operation but does not execute arbitrary defence code. The real model is invoked by the trusted controller after the broker authorization/connectivity tests, rather than exposed as a general model API proxy. This prototype does not measure GPU/cache timing leaks, host escapes, arbitrary prompt injection, all possible egress paths or full model safety. No wall-clock performance or winning probability is claimed.

Read `docs/ARCHITECTURE.md`, `docs/VALIDATION.md` and `docs/DEMO.md` for review and presentation.
