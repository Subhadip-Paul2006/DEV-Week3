---
id: nlp.attention-masking
domain: nlp
category: nlp
name: Attention Masking & Numerical Probability Soundness
owning_agent: M-35
maturity: active
status: active
languages:
- any
tags:
- attention
- masking
- softmax
- numerical-stability
related:
- core.performance
---

# Concept: Attention Masking Soundness

## Architectural Definition
Evaluates whether attention masking mechanisms correctly zero out probability mass on masked tokens:
1. In additive attention masking preceding softmax, masked positions must receive sufficiently large negative constants ($-\infty$, $-1e4$ for float16, or $-1e9$ for float32) so that $e^z \to 0$. Masking with non-negative or finite zero values erroneously assigns positive attention weight ($e^0 = 1.0$) to padding or future tokens.
2. Valid alternatives include boolean multiplicative masking (`masked_fill(mask == 0, -inf)`).
