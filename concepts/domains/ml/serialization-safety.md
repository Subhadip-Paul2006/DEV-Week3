---
id: ml.serialization-safety
domain: ml
category: security
name: Model Artifact Serialization & Deserialization Safety
owning_agent: M-36
maturity: active
status: active
languages:
- any
tags:
- security
- serialization
- safetensors
- pickle
related:
- core.security
---

# Concept: Model Serialization & Deserialization Safety

## Architectural Definition
Evaluates whether model weights, checkpoints, and artifact pipelines use secure, memory-mapped, and executable-free serialization formats:
1. Prohibits unverified standard `pickle` loading or `torch.load(..., weights_only=False)` on untrusted or external model files.
2. Recommends safe formats like `safetensors` or strict `weights_only=True` execution guards to mitigate Arbitrary Code Execution (RCE) vectors.
