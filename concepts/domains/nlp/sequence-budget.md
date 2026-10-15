---
id: nlp.sequence-budget
domain: nlp
category: nlp
name: Sequence Length Budget & Context Boundaries
owning_agent: M-35
maturity: active
status: active
languages:
- any
tags:
- sequence-length
- truncation
- max-length
- context-window
related:
- core.performance
---

# Concept: Sequence Length Budget & Context Boundaries

## Architectural Definition
Evaluates whether NLP processing pipelines and API endpoints enforce strict sequence bounds:
1. External or variable-length text inputs ingested by tokenization pipelines must specify bounded length constraints (`max_length` paired with `truncation=True`) to prevent quadratic memory blowup ($O(S^2)$ attention matrices) and Denial of Service via uncontrolled GPU memory allocation.
2. Context boundaries must be enforced unless the architecture explicitly utilizes streaming window protocols or bounded upstream gateways.
