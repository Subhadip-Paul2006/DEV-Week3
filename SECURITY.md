# Security Architecture & Threat Model — System Design Audit Tool (SDAT)

**Status:** 🔵 Planned (Phase 0 / 1)
**Owner:** Subhadip Paul
**Last updated:** 2026-09-30

SDAT runs against codebases that may be untrusted. Starting with v0.3.0, the **Research Agent** also makes outbound web requests to fetch similar projects and references. This document defines the trust model, threat boundaries, and defense invariants for the full five-layer pipeline (Classifier + Research Agent + Swarm + Renderer).

---

## 1. Trust Model

```
Trusted:                           Untrusted:
  Your local machine                 Any repository SDAT audits
  Your agent CLI config             Host repo source code
  The knowledge base (SDAT's own)   Host repo dependencies
  SDAT repo itself                  Web search results (Research Agent)
  Configured AI provider            Web pages fetched by Research Agent
  Allowlisted domains only          Any subprocess spawned by host code
```

**The cardinal rules:**

1. SDAT reads from the target repo. It never executes host code. It never fetches from the internet on behalf of the host repo.
2. SDAT's Research Agent makes outbound requests, but only to a configured allowlist of trusted domains, and never sends host-repo content in queries.
3. The classifier and renderer never access the network. Only the Research Agent does, and only if `research.enabled: true`.

---

## 2. Trust Boundaries

### Boundary T-1: SDAT ↔ Host Repository Filesystem

Same as before. Path validation, no execution of host code, no reads of secret files.

### Boundary T-2: SDAT ↔ AI Auditor CLI

Same as before. Allowlisted CLI tools, tokenized args, `shell=False`.

### Boundary T-3: SDAT ↔ Host Repository Git Remotes

Same as before. No `git push`, no PR creation.

### Boundary T-4: SDAT ↔ Secrets

Same as before. No `.env`, `*.key`, `*.pem` reads; no secret values in artifacts.

### Boundary T-5: Research Agent ↔ Internet (NEW)

The Research Agent is the first layer with outbound network access. This is a major expansion of the attack surface.

| Direction | What crosses | Validation |
|-----------|-------------|------------|
| SDAT → Internet | Search queries (only metadata, no host code) | Queries contain only classification + manifest metadata; never host source |
| Internet → SDAT | Web pages, README content, paper abstracts | Strict domain allowlist (see §3.4); sanitized excerpt extraction; length caps |
| Internet → SDAT | GitHub repo metadata (search results) | Public unauthenticated API only; rate-limited |
| Internet → SDAT | arxiv.org paper metadata | Public unauthenticated; rate-limited |

### Boundary T-6: Research Agent → LLM Prompt

| Direction | What crosses | Validation |
|-----------|-------------|------------|
| Research Agent → LLM | Synthesized peer patterns + structured summaries | Strip all raw HTML/markdown; only structured JSON extracted |
| LLM → Research Agent | Structured JSON responses | Schema-validated; free-form prose rejected |

---

## 3. Threat Model

### Threats T-1 through T-4 (unchanged from v0.2.0)

| Threat | Mitigation |
|--------|-----------|
| T-1: Malicious source code | Tree-sitter only, no execution |
| T-2:  via host repo | Structured prompts, schema validation, context budget |
| T-3: Path traversal | `resolve()` + subpath check |
| T-4: Dependency confusion | Pinned versions, hash mode |

### Threat T-5:  via Research Agent Web Results (NEW)

**Attack vector:** A malicious GitHub repo or web page contains crafted text designed to manipulate the Research Agent into:
- Generating false positive priority overrides
- Injecting false concept claims
- Including harmful recommendations in the research report

**Likelihood:** Medium. Search results are untrusted. A determined attacker could publish a crafted README that ranks well for common queries.

**Mitigation:**

1. **Strict domain allowlist:** Only configured trusted domains are fetched. Default allowlist: `github.com`, `raw.githubusercontent.com`, `arxiv.org`, official documentation sites.
2. **Content sanitization:** Strip all HTML tags, scripts, iframes before LLM ingestion. Markdown is parsed, not raw.
3. **Length caps:** Fetched content truncated at 5000 chars per source.
4. **Structured extraction:** The Research Agent extracts only specific JSON fields (project name, stars, framework, patterns). Free-form prose from search results is NEVER injected directly into LLM prompts.
5. **Schema validation:** All extracted data validated against schemas before use.
6. **No host-repo content in queries:** Search queries contain only classification metadata, manifest summaries, and category labels — never snippets of the target repo's code.
7. **Rate limiting:** Max queries per session enforced (default: 10).

**Residual risk:** Low-Medium. A well-crafted MITM page on an allowlisted domain could still inject malicious content. Mitigation: prefer HTTPS, validate TLS certs, fetch through `web_fetch` primitive (which validates).

### Threat T-6: Network Exfiltration of Target Repo Content (NEW)

**Attack vector:** A compromised Research Agent or malicious search result could be tricked into including target repo file contents in outbound HTTP requests (e.g., as a "user agent" or query parameter).

**Likelihood:** Low. The Research Agent code path does not have access to host repo file contents beyond what the classifier produced (which is metadata only).

**Mitigation:**

1. The Research Agent receives only `classification.json` and `target-summary.md` (auto-generated, no raw code)
2. All HTTP requests go through a single wrapper that logs request URLs and bodies
3. Users can review request logs in `.sdat-cache/run-<ts>/research/network.log`
4. The Research Agent's network wrapper enforces: no host file paths in query strings, no host code in request bodies

**Residual risk:** Low.

### Threat T-7: DoS via Slow / Large Web Responses (NEW)

**Attack vector:** A target web server deliberately serves huge pages to slow down the Research Agent.

**Likelihood:** Low.

**Mitigation:**
- Per-request timeout: 30s default
- Per-page size cap: 5 MB
- Total Research Agent timeout: 120s

### Threat T-8: GitHub API Abuse / Rate Limiting (NEW)

**Attack vector:** Research Agent makes too many unauthenticated GitHub API requests and gets throttled.

**Likelihood:** Low-Medium. Unauthenticated GitHub API has 60 req/hour limit.

**Mitigation:**
- Cache GitHub search results in `.sdat-cache/research/github-cache/`
- Enforce max queries (default: 10)
- Document GITHUB_TOKEN env var for higher rate limits (optional, user-provided)

### Threat T-9: Custom KB Slice Pollution (NEW)

**Attack vector:** The self-improvement mode (no peers found) generates concept files from literature. A malicious paper or book review could inject false claims that pollute the knowledge base.

**Likelihood:** Low.

**Mitigation:**
- Custom KB slices live in `.sdat-cache/research/custom-kb-slice/`, NOT in the main `concepts/` directory
- Custom slices are marked with `confidence: low` and `auto_generated: true` in frontmatter
- The user must explicitly review and approve a custom slice before it can be promoted to the main KB (future Phase 12 enhancement)

---

## 4. Invariants (Non-Negotiable)

Same as v0.2.0, plus:

| # | Invariant | Enforcement |
|---|-----------|-------------|
| INV-8 | Research Agent queries MUST NOT contain host repo source code | Hardcoded query templates; content filter at request wrapper |
| INV-9 | Research Agent MUST only fetch from allowlisted domains | Domain allowlist enforced before any HTTP request |
| INV-10 | Research Agent responses MUST be schema-validated before LLM ingestion | JSON schema validation in `peer_analyzer.py` and `literature_search.py` |
| INV-11 | Custom KB slices MUST NOT be written to `concepts/` | Custom slices only in `.sdat-cache/research/custom-kb-slice/` |
| INV-12 | All Research Agent HTTP requests MUST be logged | Network log in `.sdat-cache/run-<ts>/research/network.log` |
| INV-13 | Blockchain private keys, seeds, and wallet secrets MUST NEVER be logged or extracted into EvidenceFacts | AST sanitization & secret filtering |
| INV-14 | External research data MUST NEVER be converted into or cited as target repository EvidenceFacts | Strict type distinction & provenance checks |

---

## 5. Network Allowlist (Default)

```
github.com
raw.githubusercontent.com
api.github.com
arxiv.org
openreview.net
python.org
rust-lang.org
nodejs.org
golang.org
docs.docker.com
kubernetes.io
langchain.com
python.langchain.com
docs.llamaindex.ai
fastapi.tiangolo.com
nestjs.com
reactjs.org
vuejs.org
svelte.dev
angular.io
swift.org
dart.dev
flutter.dev
soliditylang.org
ethereum.org
polygon.technology
```

Users can extend this list in `config.yaml > research.allowed_domains`. The Research Agent will refuse to fetch any URL whose host is not in this list.

---

## 6. Secrets & Cryptographic Hygiene

1. **Host Repository Secrets:** SDAT never extracts, logs, or transmits secret values, API keys, database credentials, or private cryptographic material.
2. **Blockchain & Wallet Credentials:** SDAT never accesses, reads, or records wallet private keys, seed phrases, mnemonic phrases, keystore files, or hardware wallet credentials. Scanners only detect structural signing API calls and library usages (e.g. `web3.eth.account.sign_transaction`), never the actual private keys or secrets.
3. **AI Gateway & Research Provider Credentials:** All provider API keys (Groq, Gemini, OpenAI, Anthropic, GitHub) resolve strictly via environment variables or OS credential stores. They are never written to cache files, report artifacts, or version-controlled configs.
4. **Evidence Provenance & Research Separation:** Every `EvidenceFact` maintains strict provenance (file, line range, AST node). External research data from the Research Agent is quarantined into `.sdat-cache/research/` and is strictly labeled as contextual external data, preventing it from ever being cited as target codebase evidence.

---

## 7. Dependency Security

**Updated dependency list (v0.3.0 additions):**

- `httpx` — async HTTP client (Research Agent)
- `beautifulsoup4` — HTML parsing (Research Agent, sanitization)
- `pygithub` — GitHub API client (optional, if GITHUB_TOKEN provided)

Pinned versions in `pyproject.toml`. `pip install --require-hashes` in CI. Dependabot enabled. Monthly `pip audit`.

---

## 8. Research Agent User Controls

```yaml
research:
  enabled: true              # master switch
  network_access: trusted    # trusted | unrestricted | disabled
  network_timeout_seconds: 30
  log_all_requests: true     # writes network.log
  github_token: null         # optional, user-provided for higher rate limits
  custom_kb_auto_promote: false  # never auto-promote; require explicit user action
```

When `network_access: disabled`, the Research Agent skips web searches entirely and proceeds directly to audit.

---

## 9. Security Review Checklist (Per Phase)

Before marking any phase as complete, verify:

- [ ] All new code paths validated against INV-1 through INV-12
- [ ] No new `.env` or config file introduces real secrets
- [ ] No new subprocess invocation without `shell=False`
- [ ] No new filesystem access without path validation
- [ ] No new external network calls unless explicitly authorized
- [ ] Research Agent queries contain no host repo source code
- [ ] Research Agent respects allowlist before any HTTP request
- [ ] Research Agent responses schema-validated before LLM ingestion
- [ ] Custom KB slices isolated to `.sdat-cache/`
- [ ] All network requests logged
- [ ] `tests/` includes at least one security test per new module
- [ ] No secrets in `git diff` or `git log`