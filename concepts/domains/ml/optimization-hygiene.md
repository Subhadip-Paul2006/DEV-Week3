---
id: ml.optimization-hygiene
domain: ml
category: ml-ai
name: Training Loop & Optimization Hygiene
owning_agent: M-36
maturity: active
status: active
languages:
- any
tags:
- optimization
- scheduler
- training-loop
- optimizer
related:
- core.performance
---

# Concept: Training Loop & Optimization Hygiene

## Architectural Definition
Evaluates whether training loops, optimizers, and learning rate schedulers maintain proper execution order and state synchronization:
1. Learning rate schedulers must execute `scheduler.step()` after `optimizer.step()` has updated model weights, avoiding skipped initial learning rates or silent gradient update desynchronization.
2. Weight decay parameters must align with optimizer update equations.
