# BoundaryLab — God's Favorite

Rahul Gautam · Full-stack Developer & Security Infrastructure Lead

BoundaryLab separates a model's safety result from the integrity of the environment that produced it.

## Run the first working slice

Python 3.12; no third-party dependencies for this slice.

```sh
cd boundarylab
python3 -m unittest discover -s tests -v
python3 server.py
```

Open http://127.0.0.1:8080. Compare the hardened profile with the weak positive control.

**Current status:** local core prototype, not a completed sandbox. Hardened produces INCONCLUSIVE because container and model checks have not run. Weak produces INVALID because it intentionally permits forbidden actions. These are actual core authorization decisions, not actual container network measurements.

The demo API creates synthetic runs and credentials internally. It is not the future public broker API. Bind to loopback only. The in-memory hash chain and displayed checkpoint demonstrate verification but are not durable independently anchored storage. The final controller must retain checkpoints outside workload-writable storage.

See [BUILD_PLAN.md](BUILD_PLAN.md) for the implementation sequence, tests, limits and delivery checklist.
