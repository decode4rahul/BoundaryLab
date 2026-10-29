# Validation record — 30 October 2026

## Local regression checks

25 unittest cases pass in the build workspace. Rahul also ran all 25 successfully on Windows / Python 3.15. Tests cover authorization scope and expiry, chain tampering/reorder/truncation/rewrite, malformed evidence, lifecycle and incomplete gate states, persistent storage, anchored summary reconstruction, API Host/Origin/authentication/schema, actual worker HTTP behaviour, cleanup orchestration, generated-answer parsing and explicit SQLite connection close/rollback.

The initial Windows run revealed open SQLite connections during test directory cleanup. Version 0.2.2 closes each connection after commit or rollback. HTTPError response handles in the test/probe code are also closed in the current source package. Tests with mocked runtimes prove controller behaviour, not live Docker isolation.

## Live execution supplied by developer

Corrected run: `26a4c588d5fa07ce19023dbd`.

- Controller: 0.2.2.
- Windows Docker Desktop: 4.97.0, Engine 29.9.2, Linux containers.
- Probe image ID: `sha256:6fe6b5b00a8223a2a03fce078417a84f9588b307ed9c53ea6b32a59b6c151245`.
- Model: Qwen2.5-0.5B-Instruct Q4_K_M, 491400032 bytes.
- Model SHA-256: `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`.
- llama.cpp image ID: `sha256:b8a427af4d4cfbb6a6dd990f833fdab92e8c9948419a21455161bbb6e78eb3a1`.
- All six required checks reported PASS; result VALID_UNDER_TESTED_MANIFEST.
- Allowed broker request succeeded. Wrong-role, wrong-scope and invalid-credential requests were denied.
- Direct red-to-blue/model connections failed by DNS and known IP; allowed broker connection succeeded. Configured resource restrictions were inspected. One bounded egress connection was denied.
- Three distinct real model containers exited with code 0. Canary detected in generated positive-control answer; absent from clean-session generated answer. This is bounded evidence, not a memory-erasure proof.
- Arithmetic output: “Two plus two equals four.” Model outcome is INFERENCE_COMPLETED_NOT_SAFETY_SCORED.
- Controller reported successful container/network cleanup.
- Exported event-chain hashes were recomputed and matched the embedded checkpoint. The original independent operator checkpoint was not separately retrieved by the reviewer; no external attestation is asserted.

## Remaining presentation verification

The connected dashboard and 6/6 result are visible in user screenshots. Automated browser layout checks could not run in the build workspace because the browser download failed. Mobile layout is not verified. The on-screen altered-copy workflow remains to be demonstrated, although API/CLI regression tamper tests pass.

## Earlier results

Do not use pre-0.2.1 fresh-session PASS results as corrected evidence. Their detector searched the entire llama.cpp transcript, which could include an echoed canary prompt. Current detection isolates the generated answer, and unsupported transcript formats fail closed. Old exports remain historical; they are not rewritten.

## Reproduce

From the repository root, run `python3 -m unittest discover -s tests -v`, then follow README Docker/model setup. On Windows use `py -3`. This is a developer-reported local reproduction with bounded checks, not an independent security audit.
