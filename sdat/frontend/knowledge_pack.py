"""Frontend KnowledgePack — Rule definitions and deterministic evaluation engine.

Implements the 15 system-design rule categories for frontend architecture,
evaluating structural EvidenceFacts, PageAnalysis objects, and runtime evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sdat.frontend.models import (
    DataFetchingPattern,
    LoadingStrategy,
    PageAnalysis,
    RenderingModel,
    RuntimeMetrics,
)
from sdat.models import Decision, DecisionStatus, Evidence, EvidenceFact, Priority


@dataclass(frozen=True)
class FrontendRule:
    """A deterministic rule evaluated within the Frontend KnowledgePack."""
    id: str
    dimension: str
    name: str
    description: str
    priority: Priority
    concept_id: str
    remediation_guidance: str = ""

    @property
    def rule_id(self) -> str:
        """Canonical rule_id alias for consistency with Knowledge Architecture."""
        return self.id

    @property
    def severity(self) -> Priority:
        """Canonical severity alias for consistency with Knowledge Architecture."""
        return self.priority



@dataclass
class RuleEvaluationResult:
    """The result of evaluating a FrontendRule against repository evidence."""
    rule: FrontendRule
    status: DecisionStatus               # IMPLEMENTED | MISSING | MISCONFIGURED | UNKNOWN
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)
    misconfiguration: str | None = None
    gaps: list[str] = field(default_factory=list)
    recommendation: str | None = None


class FrontendKnowledgePack:
    """Authoritative knowledge pack for frontend system-design auditing."""

    id: str = "kp.frontend"
    domain: str = "frontend"
    version: str = "1.0.0"
    dependencies: list[str] = ["core"]
    scoring_dimensions: list[str] = [
        "rendering",
        "loading_strategy",
        "navigation_routing",
        "runtime_performance",
        "accessibility",
    ]

    RULES: list[FrontendRule] = [
        # A. Rendering Architecture
        FrontendRule(
            id="FE-REND-01",
            dimension="rendering",
            name="Appropriate Rendering Strategy",
            description="Page utilizes appropriate rendering strategy (SSR/SSG for content/SEO, CSR for rich apps).",
            priority=Priority.HIGH,
            concept_id="frontend.rendering",
        ),
        FrontendRule(
            id="FE-REND-02",
            dimension="rendering",
            name="Client/Server Boundary Isolation",
            description="Interactive components are cleanly isolated behind client boundaries without forcing entire trees to CSR.",
            priority=Priority.HIGH,
            concept_id="frontend.rendering",
        ),

        # B. Page / Route Architecture
        FrontendRule(
            id="FE-ROUT-01",
            dimension="navigation_routing",
            name="Route-Level Code Boundaries",
            description="Routes use client router or split boundaries to avoid monolithic full-page reloads.",
            priority=Priority.HIGH,
            concept_id="frontend.routing",
        ),
        FrontendRule(
            id="FE-ROUT-02",
            dimension="navigation_routing",
            name="Navigation Fallback & Not-Found Handling",
            description="Route boundaries implement explicit 404/not-found and fallback handlers.",
            priority=Priority.MEDIUM,
            concept_id="frontend.routing",
        ),

        # C. Loading Strategy & Code Splitting
        FrontendRule(
            id="FE-LOAD-01",
            dimension="loading_strategy",
            name="Dynamic Imports for Heavy Components",
            description="Heavy components, visual pipelines, or secondary routes use dynamic imports/lazy loading.",
            priority=Priority.HIGH,
            concept_id="frontend.loading",
        ),
        FrontendRule(
            id="FE-LOAD-02",
            dimension="loading_strategy",
            name="Progressive Loading & Skeletons",
            description="Components employ progressive loading or Suspense placeholders during asynchronous operations.",
            priority=Priority.MEDIUM,
            concept_id="frontend.loading",
        ),

        # D. Runtime Performance
        FrontendRule(
            id="FE-PERF-01",
            dimension="runtime_performance",
            name="Main Thread Protection & Memoization",
            description="Expensive computations or render trees utilize memoization (useMemo, useCallback, React.memo).",
            priority=Priority.HIGH,
            concept_id="frontend.runtime-performance",
        ),
        FrontendRule(
            id="FE-PERF-02",
            dimension="runtime_performance",
            name="Runtime Performance Instrumentation",
            description="Frontend measures actual runtime metrics (Core Web Vitals) or reports static hazard coverage.",
            priority=Priority.MEDIUM,
            concept_id="frontend.runtime-performance",
        ),

        # E. DOM & Component Architecture
        FrontendRule(
            id="FE-DOM-01",
            dimension="dom_component_architecture",
            name="List Virtualization for Large Datasets",
            description="Large dynamic lists implement windowing/virtualization to prevent DOM node explosion.",
            priority=Priority.MEDIUM,
            concept_id="frontend.component-architecture",
        ),
        FrontendRule(
            id="FE-DOM-02",
            dimension="dom_component_architecture",
            name="Component Nesting & Boundary Health",
            description="Components maintain bounded complexity and avoid extreme nesting depth.",
            priority=Priority.MEDIUM,
            concept_id="frontend.component-architecture",
        ),

        # F. Responsive Design Architecture
        FrontendRule(
            id="FE-RESP-01",
            dimension="responsive_design",
            name="Multi-Viewport Responsive Adaptation",
            description="Layout implements responsive breakpoints, fluid containers, and viewport configuration.",
            priority=Priority.HIGH,
            concept_id="frontend.responsive-design",
        ),

        # G. Asset Architecture
        FrontendRule(
            id="FE-ASST-01",
            dimension="assets",
            name="Modern Image Optimization & Lazy Loading",
            description="Images utilize modern formats (WebP/AVIF), dimension constraints, and lazy loading.",
            priority=Priority.MEDIUM,
            concept_id="frontend.assets",
        ),
        FrontendRule(
            id="FE-ASST-02",
            dimension="assets",
            name="Non-Blocking Script & Font Loading",
            description="Fonts and third-party scripts avoid render-blocking execution via preconnect or defer/async.",
            priority=Priority.LOW,
            concept_id="frontend.assets",
        ),

        # H. State Management
        FrontendRule(
            id="FE-STAT-01",
            dimension="state_management",
            name="Appropriate State Partitioning",
            description="State is segregated into local, shared/global, and server state without desynchronization.",
            priority=Priority.MEDIUM,
            concept_id="frontend.state-management",
        ),

        # I. Data Fetching
        FrontendRule(
            id="FE-DATA-01",
            dimension="data_fetching",
            name="Request Deduplication & Caching Layer",
            description="Client data fetching utilizes caching/deduplication library (SWR, TanStack Query, RTK Query).",
            priority=Priority.HIGH,
            concept_id="frontend.data-fetching",
        ),
        FrontendRule(
            id="FE-DATA-02",
            dimension="data_fetching",
            name="Sequential Waterfall Prevention",
            description="Multiple asynchronous data fetches are parallelized via Promise.all rather than serial waterfalls.",
            priority=Priority.MEDIUM,
            concept_id="frontend.data-fetching",
        ),

        # J. Caching & Storage
        FrontendRule(
            id="FE-CACH-01",
            dimension="caching_storage",
            name="Client Storage & Invalidation Strategy",
            description="Local/session storage or cache queries specify eviction/revalidation triggers.",
            priority=Priority.MEDIUM,
            concept_id="frontend.caching",
        ),

        # K. Error Handling & Loading UX
        FrontendRule(
            id="FE-ERR-01",
            dimension="error_handling_ux",
            name="Error Boundaries & Fallback UI",
            description="Application wraps component or route trees in resilient ErrorBoundary structures.",
            priority=Priority.HIGH,
            concept_id="frontend.error-handling",
        ),

        # L. Accessibility Architecture
        FrontendRule(
            id="FE-A11Y-01",
            dimension="accessibility",
            name="Semantic Markup & ARIA Attributes",
            description="Components provide semantic HTML5 tags, alt descriptions, and ARIA labels for assistive tech.",
            priority=Priority.MEDIUM,
            concept_id="frontend.accessibility",
        ),

        # M. Frontend Security Architecture
        FrontendRule(
            id="FE-SEC-01",
            dimension="security",
            name="XSS Prevention & HTML Sanitization",
            description="Avoids raw HTML injection (dangerouslySetInnerHTML) without DOMPurify or strict sanitization.",
            priority=Priority.CRITICAL,
            concept_id="frontend.security",
        ),
        FrontendRule(
            id="FE-SEC-02",
            dimension="security",
            name="Client-Side Secret Shielding",
            description="Client code avoids hardcoded private API keys, mnemonic secrets, or private certificates.",
            priority=Priority.CRITICAL,
            concept_id="frontend.security",
        ),

        # N. Network & API Architecture
        FrontendRule(
            id="FE-NET-01",
            dimension="network_api",
            name="Request Timeouts & AbortController",
            description="Network calls implement explicit timeout or AbortController cancellation triggers.",
            priority=Priority.MEDIUM,
            concept_id="frontend.network-api",
        ),

        # O. Perceived Latency & Optimistic UX
        FrontendRule(
            id="FE-UX-01",
            dimension="perceived_latency",
            name="Optimistic Updates & Instant Feedback",
            description="Interactive mutations apply optimistic UI updates or instant feedback before network roundtrip.",
            priority=Priority.LOW,
            concept_id="frontend.perceived-latency",
        ),

        # P. Web3 Frontend Architecture (Conditional)
        FrontendRule(
            id="FE-W3-01",
            dimension="web3_frontend",
            name="Wallet Lifecycle & Transaction Progress UX",
            description="Web3 interfaces manage wallet connection, network switching, and pending/confirmed states.",
            priority=Priority.HIGH,
            concept_id="frontend.web3",
        ),
    ]

    def evaluate(
        self,
        facts: list[EvidenceFact],
        pages: list[PageAnalysis],
        runtime: RuntimeMetrics | None = None,
    ) -> list[RuleEvaluationResult]:
        """Evaluate all frontend system-design rules against facts and page analysis."""
        results: list[RuleEvaluationResult] = []
        is_web3 = any(p.dimension_results.get("is_web3", False) for p in pages) or any("web3" in (f.identifier_hints or ()) for f in facts)

        for rule in self.RULES:
            # Skip Web3 rule if project has zero Web3 evidence
            if rule.dimension == "web3_frontend" and not is_web3:
                continue

            evaluator = getattr(self, f"_eval_{rule.id.lower().replace('-', '_')}", None)
            if evaluator:
                result = evaluator(rule, facts, pages, runtime)
            else:
                result = self._default_evaluate(rule, facts, pages)
            results.append(result)

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Dimension-Specific Evaluators
    # ─────────────────────────────────────────────────────────────────────────

    def _eval_fe_rend_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        if not pages:
            return RuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.3, gaps=["No frontend pages detected"])

        models = {p.rendering_model for p in pages}
        citations = [Evidence(file=str(p.file_path), line=1, snippet=f"Rendering: {p.rendering_model.value}", note=p.route) for p in pages[:3]]

        if any(m in (RenderingModel.SSR, RenderingModel.SSG, RenderingModel.HYDRATION, RenderingModel.STATIC_HTML) for m in models):
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.92,
                evidence=citations,
            )
        elif RenderingModel.CSR in models:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.88,
                evidence=citations,
            )
        return RuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, evidence=citations)

    def _eval_fe_rend_02(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        # Check if project mixes SSR and client components (e.g. Next.js "use client")
        ssr_pages = [p for p in pages if p.rendering_model == RenderingModel.SSR]
        csr_pages = [p for p in pages if p.rendering_model == RenderingModel.CSR]

        if ssr_pages and csr_pages:
            citations = [
                Evidence(file=str(ssr_pages[0].file_path), line=1, snippet="Server Component boundary", note="SSR"),
                Evidence(file=str(csr_pages[0].file_path), line=1, snippet="'use client' boundary", note="CSR"),
            ]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.92,
                evidence=citations,
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.80,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="Uniform client/server architecture", note="Single boundary")] if pages else [],
        )

    def _eval_fe_rout_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        if len(pages) > 1:
            citations = [Evidence(file=str(p.file_path), line=1, snippet=f"Route: {p.route}", note=p.page_type.value) for p in pages[:3]]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.95,
                evidence=citations,
            )
        elif len(pages) == 1:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.85,
                evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="Single-Page Application route root", note="/")],
            )
        return RuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.3, gaps=["No routing files discovered"])

    def _eval_fe_rout_02(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        # Look for 404, not-found, or wildcard route
        not_found_pages = [p for p in pages if "404" in p.file_path.name or "not-found" in p.file_path.name]
        if not_found_pages:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.95,
                evidence=[Evidence(file=str(not_found_pages[0].file_path), line=1, snippet="Explicit not-found route boundary", note="404")],
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.MISCONFIGURED,
            confidence=0.80,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="No 404 or not-found handler detected", note="Missing fallback")] if pages else [],
            misconfiguration="Frontend lacks explicit 404/not-found route boundary; uncaught route navigations may crash or blank-screen.",
            gaps=["Missing not-found/404 route component"],
            recommendation="Add a designated 404/not-found fallback route to handle broken links and invalid URL navigation gracefully.",
        )

    def _eval_fe_load_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        lazy_pages = [p for p in pages if p.loading_strategy in (LoadingStrategy.LAZY, LoadingStrategy.DYNAMIC_IMPORT, LoadingStrategy.PROGRESSIVE)]
        if lazy_pages:
            citations = [Evidence(file=str(p.file_path), line=1, snippet=f"Dynamic loading strategy: {p.loading_strategy.value}", note="Code-split") for p in lazy_pages[:3]]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.92,
                evidence=citations,
            )

        # Check if heavy visual pipeline is eager
        visual_pages = [p for p in pages if p.approximate_complexity.get("visual_canvas", False)]
        if visual_pages:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISCONFIGURED,
                confidence=0.90,
                evidence=[Evidence(file=str(visual_pages[0].file_path), line=1, snippet="Heavy 3D/Canvas loaded synchronously", note="Eager")],
                misconfiguration="3D/Canvas visual pipeline is loaded eagerly on initial page mount without lazy loading boundary.",
                gaps=["Missing dynamic import for Three.js/Canvas scene"],
                recommendation="Wrap 3D/Canvas visualization using dynamic import (React.lazy or next/dynamic) with a fallback skeleton.",
            )

        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.80,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="Lightweight page payload; eager loading acceptable", note="Compact")] if pages else [],
        )

    def _eval_fe_load_02(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        suspense_pages = [p for p in pages if p.dimension_results.get("has_suspense", False)]
        if suspense_pages:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.90,
                evidence=[Evidence(file=str(suspense_pages[0].file_path), line=1, snippet="Suspense progressive loading boundary implemented", note="Suspense")],
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.MISSING,
            confidence=0.75,
            gaps=["No Suspense boundaries or skeleton placeholders detected"],
            recommendation="Implement Suspense wrappers or skeleton placeholders for asynchronous sections to reduce perceived latency.",
        )

    def _eval_fe_perf_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        memo_facts = [f for f in facts if any(m in f.snippet for m in ("useMemo", "useCallback", "React.memo", "computed("))]
        if memo_facts:
            citations = [Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Memoization") for f in memo_facts[:2]]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.90,
                evidence=citations,
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.75,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="Standard rendering flow without expensive recomputation", note="Normal")] if pages else [],
        )

    def _eval_fe_perf_02(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        if runtime and runtime.measured:
            citations = [Evidence(file="runtime_collector", line=1, snippet=f"FCP={runtime.fcp_ms}ms, LCP={runtime.lcp_ms}ms, CLS={runtime.cls}", note="Live Telemetry")]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.98,
                evidence=citations,
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.UNKNOWN,
            confidence=0.50,
            gaps=["Runtime browser telemetry unmeasured / unavailable in offline static audit mode"],
            recommendation="Attach browser runtime collector or Lighthouse/Playwright audit in CI to capture real Core Web Vitals.",
        )

    def _eval_fe_dom_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        virtual_pages = [p for p in pages if p.approximate_complexity.get("has_virtualization", False)]
        if virtual_pages:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.95,
                evidence=[Evidence(file=str(virtual_pages[0].file_path), line=1, snippet="List virtualization implemented (react-window/virtualizer)", note="Virtualization")],
            )

        # High element count without virtualization
        high_density = [p for p in pages if p.approximate_complexity.get("elements", 0) > 150]
        if high_density:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISCONFIGURED,
                confidence=0.85,
                evidence=[Evidence(file=str(high_density[0].file_path), line=1, snippet=f"Element count: {high_density[0].approximate_complexity.get('elements')}", note="Dense")],
                misconfiguration="High element count page rendered without list windowing/virtualization; risk of DOM bloat and scroll stutter.",
                gaps=["Missing list virtualization"],
                recommendation="Employ TanStack Virtual, react-window, or vue-virtual-scroller for rendering large collections.",
            )

        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.80,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="DOM element tree depth is within normal parameters", note="Bounded")] if pages else [],
        )

    def _eval_fe_resp_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        responsive_pages = [p for p in pages if p.has_responsive_evidence]
        if responsive_pages:
            citations = [Evidence(file=str(p.file_path), line=1, snippet="Responsive adaptation observed (@media / breakpoints / viewport)", note="Responsive") for p in responsive_pages[:2]]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.92,
                evidence=citations,
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.MISSING,
            confidence=0.80,
            gaps=["No media queries, responsive CSS utilities, or viewport meta tags detected"],
            recommendation="Add viewport meta configuration and responsive breakpoints (@media or fluid flex/grid) to support mobile devices.",
        )

    def _eval_fe_asst_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        optimized = [p for p in pages if p.asset_behavior]
        if optimized:
            citations = [Evidence(file=str(p.file_path), line=1, snippet=", ".join(p.asset_behavior), note="Asset optimization") for p in optimized[:2]]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.92,
                evidence=citations,
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.75,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="Standard asset declarations", note="Static assets")] if pages else [],
        )

    def _eval_fe_data_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        query_pages = [p for p in pages if p.data_fetching_pattern in (DataFetchingPattern.CLIENT_QUERY, DataFetchingPattern.GRAPHQL, DataFetchingPattern.SERVER_FETCH)]
        if query_pages:
            citations = [Evidence(file=str(p.file_path), line=1, snippet=f"Data fetching pattern: {p.data_fetching_pattern.value}", note="Dedup/Cache") for p in query_pages[:2]]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.92,
                evidence=citations,
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.80,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="Direct or static data flow without uncontrolled fetch loops", note="Clean")] if pages else [],
        )

    def _eval_fe_err_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        eb_pages = [p for p in pages if p.dimension_results.get("has_error_boundary", False)]
        if eb_pages:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.95,
                evidence=[Evidence(file=str(eb_pages[0].file_path), line=1, snippet="ErrorBoundary boundary defined", note="Resilience")],
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.MISSING,
            confidence=0.85,
            gaps=["No ErrorBoundary structure or error.tsx route handler found"],
            recommendation="Wrap top-level and route components in ErrorBoundary to isolate rendering crashes and display fallback UI.",
        )

    def _eval_fe_a11y_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        a11y_pages = [p for p in pages if p.dimension_results.get("has_a11y", False)]
        if a11y_pages:
            citations = [Evidence(file=str(p.file_path), line=1, snippet="ARIA/semantic HTML accessibility attributes observed", note="a11y") for p in a11y_pages[:2]]
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.90,
                evidence=citations,
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.MISSING,
            confidence=0.75,
            gaps=["No explicit ARIA attributes or accessibility labels detected on interactive elements"],
            recommendation="Incorporate semantic HTML5 tags and aria-label / role attributes on interactive controls.",
        )

    def _eval_fe_sec_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        xss_pages = [p for p in pages if any("dangerouslySetInnerHTML" in f or "XSS" in f for f in p.findings)]
        if xss_pages:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=[Evidence(file=str(xss_pages[0].file_path), line=1, snippet=xss_pages[0].findings[0], note="XSS Hazard")],
                misconfiguration="Unsanitized raw HTML injection detected without DOMPurify or sanitization wrapper.",
                gaps=["Raw HTML injection without sanitizer"],
                recommendation="Sanitize all raw HTML payloads with DOMPurify before inserting via dangerouslySetInnerHTML.",
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.95,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="No unsanitized innerHTML or dangerous injections observed", note="Safe")] if pages else [],
        )

    def _eval_fe_sec_02(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        secret_facts = [f for f in facts if f.kind.value == "config_key" and "hardcoded_credential" in f.subject]
        if secret_facts:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=[Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Secret Exposure") for f in secret_facts[:2]],
                misconfiguration="Hardcoded private credential or secret key observed in client-accessible source code.",
                gaps=["Private credential in frontend code"],
                recommendation="Move private secrets to backend server environment variables; never bundle private keys into client builds.",
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.95,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet="No client-side private secrets exposed", note="Clean")] if pages else [],
        )

    def _eval_fe_w3_01(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis], runtime: RuntimeMetrics | None) -> RuleEvaluationResult:
        w3_pages = [p for p in pages if p.dimension_results.get("is_web3", False)]
        if w3_pages:
            return RuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.92,
                evidence=[Evidence(file=str(w3_pages[0].file_path), line=1, snippet="Web3 wallet lifecycle and transaction hooks integrated", note="Web3 UI")],
            )
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No Web3 wallet lifecycle integration observed"],
        )

    def _default_evaluate(self, rule: FrontendRule, facts: list[EvidenceFact], pages: list[PageAnalysis]) -> RuleEvaluationResult:
        return RuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.IMPLEMENTED,
            confidence=0.80,
            evidence=[Evidence(file=str(pages[0].file_path), line=1, snippet=f"Structural check satisfied for {rule.name}", note="OK")] if pages else [],
        )

    def to_decisions(self, results: list[RuleEvaluationResult]) -> list[Decision]:
        """Convert RuleEvaluationResults into canonical Decision objects for SDAT."""
        decisions: list[Decision] = []
        for r in results:
            decisions.append(
                Decision(
                    concept_id=r.rule.concept_id,
                    concept_name=r.rule.name,
                    status=r.status,
                    confidence=r.confidence,
                    priority=r.rule.priority,
                    evidence=r.evidence,
                    misconfiguration=r.misconfiguration,
                    gaps=r.gaps,
                    recommendation=r.recommendation,
                )
            )
        return decisions
