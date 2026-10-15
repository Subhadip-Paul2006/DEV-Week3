---
id: ml.nlp
category: ml-ai
name: NLP Pipelines
owning_agent: M-35
maturity: stable
languages:
- python
- typescript
tags:
- transformers
- spacy
- nltk
- llm
- openai
- embedding
related:
- ml.transformers
- ml.model-serving
domain: core
---

# NLP Pipelines

## 1. Overview

NLP Pipelines applies machine learning to text data: classification, generation, summarization, and embedding. Modern NLP is dominated by transformer-based models accessed via APIs or self-hosted inference.

## 2. Core Principles

- NLP Pipelines must be implemented with clear ownership and documented operational procedures.
- The implementation must be testable, observable, and recoverable in failure scenarios.
- Configuration must be externalised and never hardcoded in source control.
- Failure modes must be explicitly handled with appropriate fallbacks and timeouts.
- The concept's effectiveness must be measurable through metrics, logs, or traces.

## 3. Sub-Concepts


### 3.1 Core Components

Each concept can be decomposed into its primary components, each with distinct responsibilities, failure modes, and scaling characteristics.


## 4. Implementation Patterns

```python
# NLP — Hugging Face Transformers
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
model = AutoModelForSequenceClassification.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')

inputs = tokenizer('I love this product!', return_tensors='pt', truncation=True, max_length=512)
outputs = model(**inputs)
prediction = torch.softmax(outputs.logits, dim=-1)
print(f'Positive: {prediction[0][1].item():.2%}')
```

```python
# Embeddings — sentence-transformers
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(['Hello world', 'SDAT is awesome'])
print(embeddings.shape)  # (2, 384)
```

## 5. Anti-Patterns


**Skipping this concept** — The most common anti-pattern is simply not implementing the concept at all, trading short-term velocity for long-term technical debt.


## 6. Real-World Examples


- **OpenAI** — GPT-4 via API for conversational AI.

- **Hugging Face** — Hosted inference for 500,000+ models.

- **LangChain** — Framework for building LLM-powered applications.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to NLP Pipelines.

**Absence:** No evidence of this concept's implementation in the codebase.

