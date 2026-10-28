# BoundaryLab: one-day execution plan

## Goal and frozen scope

Build a reproducible local prototype showing when an AI safety evaluation's environment can be trusted under a specific tested configuration. Do not switch to ZeroLeak during this build. Keep model outcome separate from environment validity. The gate reports INVALID for a confirmed violation; INCONCLUSIVE for missing, failed-to-execute or timed-out checks; VALID_UNDER_TESTED_MANIFEST only when all required checks pass.

Team: God's Favorite. Rahul owns product decisions, local execution, reviewing results, recording and submission. Codex writes implementation and tests, explains changes and investigates failures. Rahul must be able to explain each demo claim.

## Architecture

Trusted host controller starts a fixed Docker profile and retains checkpoints. It alone controls Docker. Red, blue and model workloads have separate private networks with the trusted broker on the necessary networks. Broker exposes fixed, role-scoped and run-scoped operations, never a general URL proxy. Evidence storage is private. Workloads receive no Docker socket, host credentials or arbitrary host mounts. Blue submits allowlisted versioned defence configuration rather than executable arbitrary code. A dashboard reads operator summaries.

The broker, controller, host kernel and verifier are trusted. This prototype does not prove resistance to host compromise, GPU/cache side channels or all memory leakage.

## Delivery sequence and stop conditions

| Budget from start | Work | Acceptance criterion |
|---|---|---|
| 0–2 hours | Environment and core | Reproducible startup; allowed and denied broker requests; core regression tests |
| 2–6 hours | Durable broker and controller | Explicit run lifecycle; frozen manifest hash; no user-controlled Docker commands; persistent events; checkpoints outside workload-writable store |
| 6–10 hours | Container boundaries | Real allowed connection; denied red-to-blue and red-to-model using DNS and known IP; denied unwanted egress; resource/time limits and disposable state |
| 10–13 hours | Real local inference | One small CPU model with pinned weights metadata; fresh process each run; bounded canary test with contaminated positive control |
| 13–16 hours | Dashboard and integration | Dashboard uses measured backend results; weak control invalidates; hardened gates only measured checks; clean-machine run |
| 16–18 hours | Evidence and delivery | Public repo prepared, reproducible README, limitations, demo recording and required links |
| Remaining time | Buffer | Fix failures and complete organiser form/social requirements |

These are planning budgets, not completion guarantees. If Docker setup stalls, fix the local environment before expanding UI. If real inference cannot run, mark it NOT_RUN and explain the incomplete submission; do not relabel a mock as a model run. Never skip a missing check to obtain VALID.

## Current implemented slice

- Opaque random credentials bound to role and run in memory.
- Fixed action permissions with deny-by-default behaviour.
- Synthetic weak control that intentionally bypasses role/run checks.
- Canonical JSON hash-chain evidence and verification against a supplied checkpoint.
- Gate that keeps unknown checks inconclusive.
- Local dashboard showing core results and missing checks.
- Four regression tests covering authorization, evidence alteration/reorder/truncation/rewrite, gate states, and positive controls.

Not implemented yet: Docker isolation, actual broker HTTP authentication, persistent run management, independent checkpoint retention, real inference, canary carryover measurement and final demo packaging. Dashboard demo endpoints are orchestration demonstrations, not protected workload endpoints.

## Next implementation contracts

1. Run controller: CREATED → PRECHECK → RUNNING → VERIFYING → COMPLETE. A confirmed precheck violation halts execution; timeout/error yields inconclusive. Record manifest and software versions before workloads start.
2. Broker: scoped credentials passed in authorization headers, not URLs or logs; fixed request schemas and size limits; expired/completed run credentials denied; authenticated operator view. Use a maintained framework and authentication library if adopting JWT; do not invent JWT cryptography.
3. Networks: distinct internal networks per workload, broker with multiple interfaces. `internal: true` does not isolate peers sharing a network. Validate both names and known IPs. Run positive allowed connectivity tests so a broken network is not mistaken for isolation.
4. Model: select a small model after checking actual RAM/CPU. Pin model identity/revision/hash and licence. Fresh model worker process for every sequential run, read-only weights, ephemeral writable state, bounded requests/timeouts. Clean up process/state in finally paths. No training, GPU requirement or OpenAI API requirement.
5. Evidence: append-only private events with run and sequence binding; never record raw prompts, secrets or credentials. Keep operator checkpoints separately. Externally supplied malformed evidence must fail verification cleanly. A host operator able to replace both evidence and checkpoints remains trusted.
6. UI: show model outcome, environment verdict, every required check, profile, manifest hash, evidence verification and limitations. Never hardcode passing status. Add export only after persistent evidence works.

## Essential acceptance tests

- Valid red request accepted; wrong role, other run, invalid/expired token and unknown operation denied.
- Red cannot directly reach blue/model by DNS or known IP. Broker-approved path succeeds. An expected denial counts as a passing boundary check.
- Weak synthetic control demonstrably triggers a failed check. Keep it disposable and local.
- Model performs real inference and its version is recorded; legitimate request completes under the hardened profile.
- Fresh-process identifiers and cleanup observed. Unique synthetic canary checked across sequential sessions. Contaminated positive control proves the detector works. Canary absence only supports the bounded test, not universal memory erasure.
- Event mutation, deletion, reorder and truncation fail against the retained checkpoint. Full rewritten chain also fails against the original checkpoint.
- Required check missing/error/timeout yields INCONCLUSIVE. Confirmed boundary violation yields INVALID. No model outcome can override that result.

## Demo script

Explain the problem in one sentence. Show the frozen profile and required checks. Run the weak positive control: forbidden action succeeds and evaluation becomes INVALID. Run the hardened profile: legitimate action succeeds, forbidden action is denied; show actual model and container checks when available. Export evidence, alter a copy, and show verification failure against the retained original checkpoint. Finish with limitations and reproducibility steps. Suggested recording length: about three minutes, unless the organiser specifies otherwise.

## What Rahul needs to learn

- Explain a container versus a virtual machine, and why a shared kernel remains trusted.
- Read an HTTP request, status code and authorization scope.
- Understand separate Docker networks and why shared internal networks allow peer communication.
- Explain a hash chain, an independent checkpoint and the remaining trusted operator.
- Distinguish model failure from environment failure and missing evidence.
- Run tests, inspect failures, start/stop the demo, and demonstrate a clean reproduction.

Learn these while checking real outputs; no large course or model training is needed before building.

## Submission pack

Prepare repository source with dependency versions, licence/attribution, startup instructions, screenshots and explicit limitations; a working prototype recording; and the links requested by the current official submission form. Prior instructions require GitHub, prototype video, LinkedIn pitch and Instagram Reel. Use the extended deadline supplied by the organiser, and verify the current WhatsApp/form instructions before posting. Do not publish credentials or private group links. No public posting or submission has been performed by this project.

## Research foundations

These are references for implementation and limitations, not evidence that our implementation passes:

- https://inspect.aisi.org.uk/sandboxing.html
- https://github.com/UKGovernmentBEIS/sandbox_escape_bench
- https://gvisor.dev/docs/architecture_guide/security/
- https://docs.docker.com/compose/how-tos/networking/
- https://github.com/Azure/PyRIT
- https://github.com/NVIDIA/garak
- https://github.com/ethz-spylab/agentdojo

Defer gVisor integration, Kubernetes, broad benchmark ingestion, arbitrary defence code, multi-agent orchestration and public hosting until the narrow prototype is reproducible.
