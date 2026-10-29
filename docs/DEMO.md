# Demonstration: maximum three minutes

Record only behaviour actually observed on your machine. Do not record a mocked success path as evidence.

1. 0:00–0:20: Ask “Can we trust an AI safety result if the test environment itself was compromised?” Explain the distinction between model performance and environment validity.
2. 0:20–0:40: Introduce BoundaryLab and the fixed scope. Show required checks and runtime availability.
3. 0:40–1:05: Run weak positive control. Explicitly call it synthetic. Show the forbidden authorization and INVALID result; note model execution was halted.
4. 1:05–1:45: Show a completed hardened run. Expand measured network/HTTP results and fresh model container identities. If Docker or model checks have not run, say so and show INCONCLUSIVE. Do not call this full isolation proof.
5. 1:45–2:15: Click “Test altered copy”. Show original VERIFIED and changed copy REJECTED. Explain the checkpoint is retained by the trusted operator.
6. 2:15–2:40: Show manifest, actual model identity and reproducible startup/test commands. Explain the remaining trusted host and bounded canary limitation.
7. 2:40–3:00: State current implementation status and next extension. Close with “Before trusting a score, inspect the conditions behind it.”

A 90-second version can combine the introduction and omit the architecture explanation. Required organiser tags and submission links should come from the current official instructions. The application does not publish social posts or submit any form.
