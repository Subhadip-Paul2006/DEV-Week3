# Foundation Concept Authoring Prompt

Copy this entire prompt into your AI coding assistant context. Replace `{CONCEPT_NAME}`, `{CONCEPT_ID}`, and `{CONCEPT_TIER}` with the target concept details before running.

---

## Your Task

You are writing a **foundation concept file** for the SDAT (System Design Audit Tool) knowledge base.

This file is the single source of truth for one system-design concept. It will be read by an AI audit agent that scans real codebases and decides whether this concept is implemented, missing, or misconfigured.

**Your output must be exhaustive.** Every sub-concept, every common mistake, every scanner signal, every configuration parameter — it all goes in this file. An agent with only this file must be able to audit any project thoroughly without missing anything.

---

## File Location

Write to: `sdav1/concepts/foundation/{concept-slug}.md`

The slug is the concept name in kebab-case. Example: `circuit-breaker.md`, `rate-limiting.md`

---

## YAML Frontmatter (exact format)

```yaml
---
id: foundation.{concept-slug}
category: foundation
owning_agent: F-{XX}
maturity: draft              # draft | stable | mature
languages: [any]             # or specific: [python, typescript, go, ...]
tags: [tag1, tag2, tag3]     # searchable keywords, minimum 3
related: [foundation.other-concept, foundation.another-concept]  # minimum 2
---
```

Fill in:
- `id`: matches the filename slug
- `owning_agent`: the F-XX agent number (see AGENTS.md)
- `maturity`: use `draft` for new concepts, `stable` for polished ones
- `languages`: `[any]` for universal concepts, specific list otherwise
- `tags`: at least 3 relevant keywords
- `related`: at least 2 related foundation concepts

---

## Markdown Body Structure (MANDATORY — follow this exact order)

Write every section below. If a section doesn't apply, write "N/A for this concept" and explain why.

---

### 1. Overview

One-paragraph definition. What is this concept? Why does it exist in system design?

**Audience:** A developer who has never heard of this concept should understand it after reading this section.

**Length:** 3–6 sentences.

---

### 2. Core Principles

The fundamental truths that underpin this concept. These are non-negotiable rules.

Write 3–7 principles. Each principle should be a single sentence stating a rule that is always true for this concept.

**Example for caching:**
- "Cached data must have a TTL or invalidation strategy — cached data without expiry is stale data."
- "Cache keys must be namespaced to prevent collision between different data types."
- "Caching is a performance optimization, not a data storage solution — the source of truth must always be the database."

---

### 3. Sub-Concepts (EXHAUSTIVE — this is the most important section)

Break the concept into every meaningful sub-component. Each sub-concept gets its own subsection with:

- **Definition:** What this sub-concept means
- **Why it matters:** Consequences of getting it wrong
- **Implementation patterns:** How it's typically done in real code
- **Common mistakes:** What engineers get wrong
- **Scanner signals:** What the code scanner should look for (both positive and negative signals)

**Required sub-concepts by concept type:**

For **state/behavior concepts** (caching, circuit-breaker, retries, rate-limiting, message-queues):
- Configuration parameters (every knob that can be tuned)
- State transitions (lifecycle of this concept)
- Integration points (how it connects to other system components)
- Failure modes (what happens when it breaks)
- Observability (how to monitor it)
- Performance characteristics (latency, throughput, resource usage)

For **structural concepts** (HLD, LLD, proxies, load-balancers, protocols):
- Architectural patterns (the common ways to implement this)
- Component responsibilities (what each part does)
- Communication patterns (how components talk)
- Scaling characteristics (how it behaves under load)
- Tradeoffs (pros/cons of each approach)
- Security considerations

For **data concepts** (CAP, database-scaling, idempotency, connection-pooling):
- Consistency models
- Partitioning strategies
- Replication approaches
- Conflict resolution
- Failure recovery
- Data integrity guarantees

**Length:** This section should be 60–80% of the entire file. Do not rush it.

---

### 4. Scanner Signals (DETAILED)

The scanner is a static-analysis script that looks at code and emits signals. This section tells the scanner WHAT to look for.

#### 4.1 Presence Signals

Signals that prove this concept IS implemented. Be as specific as possible.

Format:
```markdown
| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Import of `redis` client library | Python, TypeScript, Go | regex: `import redis|import ioredis|import go-redis|require predis` | High |
| Cache decorator on function | Python, TypeScript | AST: function has `@cache` or `@cache_page` decorator | High |
| In-memory LRU cache initialization | Python, Go | regex: `lru_cache|NewEvictingLRU|sync.Map` | Medium |
```

Include at least 8–15 presence signals covering:
- Library/framework imports
- Configuration file entries
- Function/method signatures
- Decorator patterns
- Middleware registration
- Environment variables
- Database schema indicators

#### 4.2 Absence Signals

Signals that prove this concept is MISSING or NOT APPLICABLE.

Format: same table as above.

Include signals like:
- No relevant imports found
- No configuration entries
- No middleware registered
- No environment variables set

#### 4.3 Misconfiguration Signals

Signals that prove this concept exists but is WRONG or FRAGILE.

Format: same table as above.

Include signals like:
- TTL set to 0 or -1 (infinite)
- No eviction policy configured
- Hardcoded credentials
- Missing error handling
- Synchronous blocking calls in async context
- Unbounded resource usage (no max connections, no max queue size, no max retries)

**Length:** This section must have minimum 20 total signals (presence + absence + misconfiguration combined).

---

### 5. Anti-Patterns (EXHAUSTIVE)

Every common way engineers implement this concept incorrectly.

For each anti-pattern:
- **Name:** What it's called
- **Description:** What it looks like in code
- **Why it's dangerous:** The specific failure mode it causes
- **Detection:** How to spot it in a codebase
- **Fix:** The correct approach

Include at least 6 anti-patterns. Prioritize:
- Patterns that cause crashes or data loss (highest priority)
- Patterns that cause performance degradation
- Patterns that create security vulnerabilities
- Patterns that are technically correct but architecturally wrong

**Example for caching:**
```markdown
#### Anti-Pattern: Cache Without TTL

**Description:**
```python
r.set('user:123', user_data)  # No EXPIRE set
```

**Why it's dangerous:**
Data changes in the database but the cache never invalidates. Users see stale data indefinitely. In a user profile system, this means a user updates their email and still sees the old one for hours or days.

**Detection:**
Scanner looks for `SET`/`SETEX` calls. If `SET` is used without a corresponding `EXPIRE` within 3 lines of context → flag.

**Fix:**
```python
r.setex('user:123', 3600, user_data)  # TTL of 1 hour
# OR
r.set('user:123', user_data, ex=3600)
```
```

---

### 6. Configuration Reference

Every parameter, flag, environment variable, and configuration option related to this concept.

Format as a table:

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `cache_ttl` | int | 300 | 3600 | Time-to-live in seconds for cached entries |
| `redis_max_connections` | int | 10 | 50 | Max connections in the Redis connection pool |

Include:
- Library-specific settings (Redis, Memcached, etc.)
- Framework-specific settings (Django CACHES, FastAPI CacheControl, etc.)
- Environment variables (REDIS_URL, CACHE_TTL, etc.)
- OS-level settings (file descriptors, ulimit, etc.)

**Length:** Minimum 5 configuration parameters.

---

### 7. Integration Points

How this concept interacts with other system components.

- **Depends on:** What this concept requires from other components (e.g., caching depends on a data store)
- **Used by:** What uses this concept (e.g., caching is used by API handlers, background jobs)
- **Related concepts:** Which other foundation concepts interact with this one (e.g., caching ↔ connection pooling, circuit breaker ↔ retries)

Write 3–5 integration points with specific examples.

---

### 8. Observability

How to monitor, measure, and alert on this concept in production.

Include:
- **Key metrics** (e.g., cache hit rate, circuit breaker state, retry count)
- **Log messages** (what to log when this concept triggers)
- **Alert thresholds** (when to page an engineer)
- **Health indicators** (how to know this concept is working correctly)

Format as a table:

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Cache hit rate | Prometheus | < 80% → warn, < 60% → page | Check eviction policy, increase memory |
| Circuit breaker open count | Prometheus | Any → page | Check upstream service health |

---

### 9. Evolution / Version Tracking

How this concept has changed over time in the industry.

Include:
- Original approach (e.g., "Early systems used manual caching with memcached")
- Current best practice
- Emerging patterns (e.g., "Cache-aside is being replaced by write-through in event-sourced systems")
- Deprecated patterns (what to avoid)

**Length:** 2–4 paragraphs.

---

### 10. References

Links to authoritative sources:
- Official documentation (Redis docs, IETF RFCs, etc.)
- Key blog posts or papers
- Relevant GitHub projects
- Books or chapters

Use real URLs. No placeholder links.

Minimum 3 references.

---

## Quality Standards

### Tone
- Technical but accessible
- Authoritative without being dogmatic
- Practical — every principle should have a "why" and a "how"
- No marketing language, no hype

### Precision
- Give specific numbers, not ranges: "TTL of 3600 seconds" not "a few hours"
- Name specific libraries and versions: "tenacity >= 8.0" not "a retry library"
- Give specific error messages and HTTP status codes
- Include actual code snippets (Python, TypeScript, Go) showing correct and incorrect usage

### Completeness
- Do NOT leave any subsection empty
- Do NOT use "etc." — list everything
- Do NOT use "and so on" — write it all out
- If you're unsure about a sub-concept, mark it as `[needs-review]` but still write something

### Code Examples
Every anti-pattern and every correct implementation MUST include a real code snippet.
- Use Python, TypeScript, and Go where applicable
- Show the WRONG way first (marked with ❌ or // WRONG:)
- Show the RIGHT way second (marked with ✅ or // CORRECT:)
- Keep snippets under 20 lines each

---

## Final Checklist

Before finishing, verify:

- [ ] YAML frontmatter is complete and valid
- [ ] All 10 sections are present
- [ ] Sub-concepts section has at least 5 subsections
- [ ] Scanner signals table has at least 20 total entries
- [ ] Anti-patterns has at least 6 entries with code examples
- [ ] Configuration reference has at least 5 parameters
- [ ] Observability has at least 3 metrics with thresholds
- [ ] References has at least 3 real URLs
- [ ] Every section has actual content, no placeholders
- [ ] Code examples are correct and tested (mentally verify they compile/run)

---

## The Target Concept

- **Concept name:** {CONCEPT_NAME}
- **Concept ID:** {CONCEPT_ID}
- **Agent number:** F-{XX}
- **Related concepts:** (see AGENTS.md for F-agent mapping)

Now write the complete concept file. Do not summarize. Do not abbreviate. Write the full exhaustive reference.

---

## Foundation Concept Authoring Prompt — v1.0
*For use with SDAT v0.4.0+*
