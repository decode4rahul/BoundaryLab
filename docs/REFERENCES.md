# Implementation references and attribution

BoundaryLab uses Python's standard library for its local app. Docker and llama.cpp are external runtime dependencies, not bundled implementations. No existing Bayora or other hackathon entry has been copied into this source tree. The system does not establish scientific novelty.

- Docker container security/configuration: https://docs.docker.com/engine/containers/run/
- Docker daemon trust: https://docs.docker.com/engine/security/
- Official llama.cpp CLI: https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md
- Official llama.cpp Docker packaging: https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md
- Inspect sandboxing, related evaluation infrastructure: https://inspect.aisi.org.uk/sandboxing.html
- Related sandbox evaluation work: https://github.com/UKGovernmentBEIS/sandbox_escape_bench
- Related model vulnerability scanner: https://github.com/NVIDIA/garak

Review the licences of downloaded images and model weights separately. This repository's MIT licence does not relicense those dependencies or any model.
