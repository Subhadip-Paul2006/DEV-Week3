---
id: ml.mathematical-correctness
domain: ml
category: ml-ai
name: Mathematical & Numerical Correctness in ML
owning_agent: M-35
maturity: active
status: active
languages:
- any
tags:
- math
- numerical-stability
- loss-function
- logits
related:
- core.performance
---

# Concept: Mathematical & Numerical Correctness in ML

## Architectural Definition
Evaluates whether machine learning algorithms, loss functions, and activation pipelines adhere to foundational numerical stability and mathematical contracts:
1. Logit vs Probability compatibility: Cross-entropy losses that internally compute log-softmax must receive unconstrained logits, not outputs of an explicit softmax or sigmoid.
2. Numerical stability: Operations computing log-probabilities, attention distributions, or normalizations must avoid overflow/underflow through numerically stable formulations (such as log-sum-exp with max-subtraction or dedicated library primitives).
