# SDAT Architecture — AI Provider Gateway

**Status:** Implemented & Verified in Codebase  
**Core Source:** [sdat/ai/gateway.py](../../sdat/ai/gateway.py), [sdat/ai/config.py](../../sdat/ai/config.py), [sdat/ai/adapters/](../../sdat/ai/adapters/)

---

## 1. Gateway Purpose & Invariants

The **AI Provider Gateway** implements the provider abstraction layer mandated by [AGENTS.md](../../AGENTS.md#11-ai-layer-integration--developer-invariants):
1. **Never Bind Directly to a Vendor:** Agents, scanners, and report generators never call specific AI SDKs (OpenAI, Anthropic, Google) directly. All requests pass through the unified `AIGateway` interface.
2. **Deterministic Independence:** If AI credentials are not provided, or if an API fails, the audit engine completes normally with 100% deterministic output.
3. **Strict Context Budgeting:** A hard token ceiling (`context_budget_tokens: 4000`) prevents runaway costs and bounds latency.
4. **Zero Credential & Code Leakage:** No API keys are ever committed to code or logged. Source files designated as secrets (`.env`, `*.pem`, `*.key`) are completely pruned by `is_secret_file()` before any scanner or gateway process can access them.

---

## 2. Configuration & Provider Resolution

Configuration is resolved dynamically from environment variables and `config/sdat.config.yaml` without requiring code edits or application restarts:

### 2.1 Supported Provider Environment Keys

| Provider Identifier | Primary Environment Variable | Fallback Variable | Default Model Hint |
| :--- | :--- | :--- | :--- |
| `openrouter` | `OPENROUTER_API_KEY` | — | `qwen/qwen3-coder:free` |
| `gemini` / `gemma` | `GEMINI_API_KEY` | `GOOGLE_API_KEY` | `gemini-1.5-flash` / `gemma-2-9b-it` |
| `openai` | `OPENAI_API_KEY` | — | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | — | `claude-3-5-sonnet` |
| `groq` | `GROQ_API_KEY` | — | `llama-3.1-70b-versatile` |
| `ollama` | *(Local server: no key needed)* | `OLLAMA_HOST` | `qwen2.5-coder` |
| `none` *(Default)* | — | — | Deterministic fallback only |

### 2.2 Provider Resolution Order (`AIConfig.from_env()`)
1. Checks explicit `SDAT_AI_PROVIDER` override.
2. If unset or `none`, auto-detects based on available environment keys in order: `OPENROUTER_API_KEY` $\rightarrow$ `GEMINI_API_KEY` $\rightarrow$ `OPENAI_API_KEY` $\rightarrow$ `ANTHROPIC_API_KEY`.
3. If no provider keys are present, returns `AIConfig(enabled=False, provider="none")`.
4. Overrides can be passed directly from the CLI via `sdat audit --model <model-id>` or `sdat audit --no-ai`.

---

## 3. The `AIProvider` Protocol & Adapters

All backends implement the `AIProvider` abstract base class defined in [sdat/ai/gateway.py](../../sdat/ai/gateway.py#L99):

```python
class AIProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def enrich_decisions(
        self,
        decisions: List[Decision],
        facts: List[EvidenceFact],
        telemetry: Optional[AuditTelemetry] = None,
    ) -> AIEnrichmentResult:
        """Analyze deterministic decisions and produce executive summary + remediation cards."""
        ...
```

### Active Provider Adapters
* **`OpenRouterAdapter` (`sdat/ai/adapters/openrouter.py`):** Provides multi-model routing to open weights and free-tier hosted models (e.g. Qwen 2.5/3 Coder, DeepSeek) through a standardized OpenAI-compatible REST API.
* **`GemmaAdapter` (`sdat/ai/adapters/gemma.py`):** Native adapter for Google Gemma 4 / Gemini models using verified prompt templates.
* **`OfflineCachedProvider`:** Allows deterministic replay of previously verified reasoning passes (e.g. `docs/audit/cached_qwen_enrichment.json` and `cached_gemma_enrichment.json`) during offline or CI environments.

---

## 4. Fail-Open Architecture & Grounding

The AI Gateway enforces strict structural boundaries to prevent model hallucination:

```
[Deterministic Decisions & Evidence Facts]
                    │
                    ▼
          [Grounding Filter] ──► Discards ungrounded references
                    │
                    ▼
          [AI Provider Call] ──► (Timeout / Error / Invalid JSON?)
                    │
           ┌────────┴────────┐
        [Success]         [Failure]
           │                 │
           ▼                 ▼
   [AI Remediation]   [Deterministic Fallback]
           │                 │
           └────────┬────────┘
                    ▼
      [docs/audit/04-remediation.md]
```

### Safety and Validation Guardrails:
1. **Grounding Verification (`sdat/ai/grounding.py`):** AI responses are cross-checked against actual `EvidenceFact` citations. The AI cannot claim a file exists if it was not in the scanner inventory.
2. **JSON Schema Enforcement:** Responses must adhere to the `RemediationItem` structure (`why_it_matters`, `architectural_impact`, `recommended_solution`, `implementation_steps`, `validation`).
3. **Fail-Open Fallback:** If an AI provider returns an HTTP error, rate limit, or invalid payload, the gateway logs a warning in `AuditTelemetry` and constructs deterministic remediation guidance directly from the static knowledge base templates. The audit never fails due to an external AI error.

---

## 5. Verification & Implementation Status

| Feature / Adapter | Status | Details |
| :--- | :--- | :--- |
| `AIConfig` Environment Resolution | **Implemented & Verified** | Tested in `tests/ai/test_ai_layer.py` |
| `AIGateway` Abstraction | **Implemented & Verified** | Validated with multiple mock & live backends |
| OpenRouter REST Adapter | **Implemented & Verified** | Operates with OpenAI-compatible endpoint |
| Gemma / Gemini Adapter | **Implemented & Verified** | Verified in `sdat/ai/adapters/gemma.py` |
| Offline Cache Replay | **Implemented & Verified** | Loaded from `docs/audit/cached_*.json` |
| Fail-Open Fallback | **Implemented & Verified** | Tested when `OPENROUTER_API_KEY` is missing |
| Conversational Chat Assistant | **Planned (Future Phase)** | Described in architecture roadmap |
