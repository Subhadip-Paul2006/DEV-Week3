"""Frontend Page & Route Analyzer.

Discovers and evaluates individual pages, entrypoints, and route boundaries
across modern frameworks (React, Next.js, Vue, Svelte, Astro, HTML/JS/CSS).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Set

from sdat.frontend.models import (
    DataFetchingPattern,
    LoadingStrategy,
    PageAnalysis,
    PageType,
    RenderingModel,
    RuntimeMetrics,
)

DEFAULT_EXCLUDES: Set[str] = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".output",
    "vendor",
    "coverage",
    ".sdat-cache",
}

FRONTEND_EXTENSIONS = {".tsx", ".jsx", ".ts", ".js", ".html", ".vue", ".svelte", ".astro"}


class FrontendPageAnalyzer:
    """Extracts structural architecture, complexity, and behaviors for frontend pages."""

    def __init__(self, target_root: str | Path) -> None:
        self.target_root = Path(target_root)

    def discover_page_files(self) -> List[Path]:
        """Find candidate page, route, and entrypoint files."""
        if not self.target_root.exists() or not self.target_root.is_dir():
            return []

        candidates: List[Path] = []
        for p in self.target_root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in FRONTEND_EXTENSIONS:
                continue
            if any(part in DEFAULT_EXCLUDES for part in p.parts):
                continue

            rel_str = str(p.relative_to(self.target_root)).replace("\\", "/")
            name_lower = p.name.lower()

            # Next.js App Router (app/**/page.*)
            if "/app/" in f"/{rel_str}" and (name_lower.startswith("page.") or name_lower.startswith("route.")):
                candidates.append(p)
            # Next.js Pages Router or Nuxt / Astro pages (pages/**/*)
            elif "/pages/" in f"/{rel_str}" and not name_lower.startswith("_app.") and not name_lower.startswith("_document."):
                candidates.append(p)
            # SvelteKit routes (+page.svelte)
            elif name_lower.startswith("+page."):
                candidates.append(p)
            # HTML entrypoints / pages
            elif p.suffix.lower() == ".html":
                candidates.append(p)
            # SPA entrypoints / root components
            elif name_lower in ("app.tsx", "app.jsx", "app.vue", "app.svelte", "main.tsx", "main.jsx", "index.tsx", "index.jsx", "router.tsx", "routes.tsx"):
                candidates.append(p)

        return sorted(candidates)

    def analyze_page(self, file_path: Path, runtime: RuntimeMetrics | None = None) -> PageAnalysis:
        """Perform static structural analysis on a single page or entrypoint."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""

        route = self._infer_route(file_path)
        rendering_model = self._detect_rendering_model(content, file_path)
        loading_strategy = self._detect_loading_strategy(content)
        data_fetching_pattern = self._detect_data_fetching(content)
        complexity = self._estimate_complexity(content)
        has_responsive = self._detect_responsive_evidence(content)
        asset_behaviors = self._detect_asset_behaviors(content)

        # Detect page type
        page_type = self._determine_page_type(file_path, content, rendering_model, complexity)

        # Generate page findings
        findings: list[str] = []
        if complexity.get("visual_canvas", False) and loading_strategy == LoadingStrategy.EAGER:
            findings.append("Heavy 3D/Canvas visual pipeline detected without lazy loading or code-splitting boundary")
        if complexity.get("elements", 0) > 150 and not complexity.get("has_virtualization", False):
            findings.append("High element density detected without list virtualization safeguard")
        if data_fetching_pattern in (DataFetchingPattern.REST, DataFetchingPattern.SERVER_FETCH) and "await " in content and content.count("await ") >= 2:
            if "Promise.all" not in content and "Promise.allSettled" not in content:
                findings.append("Multiple sequential asynchronous fetches detected; potential request waterfall")
        if "dangerouslySetInnerHTML" in content or "v-html" in content:
            if "DOMPurify" not in content and "sanitize" not in content.lower():
                findings.append("Unsanitized raw HTML injection detected; XSS risk")

        dimension_results = {
            "rendering": rendering_model.value,
            "loading": loading_strategy.value,
            "data_fetching": data_fetching_pattern.value,
            "interactive_elements": complexity.get("interactive_elements", 0),
            "has_virtualization": complexity.get("has_virtualization", False),
            "has_error_boundary": "ErrorBoundary" in content or "error.tsx" in file_path.name.lower(),
            "has_suspense": "Suspense" in content or "loading.tsx" in file_path.name.lower(),
            "has_a11y": bool(re.search(r"aria-[a-z]+=|role=[\"']|alt=[\"']", content)),
            "is_web3": bool(re.search(r"\bwagmi\b|\buseAccount\b|\buseConnect\b|\bRainbowKit\b|\bWeb3Modal\b", content)),
        }

        return PageAnalysis(
            file_path=file_path,
            route=route,
            page_type=page_type,
            rendering_model=rendering_model,
            loading_strategy=loading_strategy,
            data_fetching_pattern=data_fetching_pattern,
            approximate_complexity=complexity,
            has_responsive_evidence=has_responsive,
            asset_behavior=tuple(asset_behaviors),
            findings=tuple(findings),
            dimension_results=dimension_results,
            runtime_measurements=runtime or RuntimeMetrics(),
        )

    def analyze_all_pages(self, runtime: RuntimeMetrics | None = None) -> List[PageAnalysis]:
        """Discover and analyze all pages across the repository."""
        pages = self.discover_page_files()
        return [self.analyze_page(p, runtime=runtime) for p in pages]

    # ─────────────────────────────────────────────────────────────────────────
    # Heuristics & Classifiers
    # ─────────────────────────────────────────────────────────────────────────

    def _infer_route(self, file_path: Path) -> str:
        """Infer URL route pattern from file path."""
        try:
            rel = file_path.relative_to(self.target_root).as_posix()
        except ValueError:
            rel = file_path.name

        # Next.js App Router
        if "app/" in rel:
            sub = rel.split("app/", 1)[1]
            parts = [p for p in sub.split("/") if not p.startswith("page.") and not p.startswith("route.") and not p.startswith("(")]
            return "/" + "/".join(parts)
        # Next.js Pages Router
        if "pages/" in rel:
            sub = rel.split("pages/", 1)[1]
            sub = re.sub(r"\.[^.]+$", "", sub)
            if sub == "index":
                return "/"
            return "/" + sub.replace("index", "")
        # SvelteKit
        if "routes/" in rel:
            sub = rel.split("routes/", 1)[1]
            sub = re.sub(r"\+page\.[^.]+$", "", sub).strip("/")
            return f"/{sub}" if sub else "/"
        # Plain HTML
        if file_path.suffix.lower() == ".html":
            stem = file_path.stem
            return "/" if stem == "index" else f"/{stem}"

        return f"/{file_path.stem}"

    def _detect_rendering_model(self, content: str, file_path: Path) -> RenderingModel:
        if file_path.suffix.lower() == ".html":
            return RenderingModel.STATIC_HTML

        if '"use client"' in content or "'use client'" in content:
            return RenderingModel.CSR

        if "getStaticProps" in content or "generateStaticParams" in content:
            return RenderingModel.SSG

        if "getServerSideProps" in content:
            return RenderingModel.SSR

        # Next.js App router default without "use client"
        if "app/" in str(file_path).replace("\\", "/") and ("export default async function" in content or "export default function" in content):
            return RenderingModel.SSR

        if "hydrateRoot" in content or "ReactDOM.hydrate" in content:
            return RenderingModel.HYDRATION

        if "createRoot" in content or "ReactDOM.render" in content or "createApp" in content:
            return RenderingModel.CSR

        if "Suspense" in content and "readableStream" in content.lower():
            return RenderingModel.STREAMING

        return RenderingModel.CSR

    def _detect_loading_strategy(self, content: str) -> LoadingStrategy:
        if "React.lazy" in content or "next/dynamic" in content or "defineAsyncComponent" in content:
            return LoadingStrategy.LAZY
        if re.search(r"\bimport\s*\(", content):
            return LoadingStrategy.DYNAMIC_IMPORT
        if "Suspense" in content:
            return LoadingStrategy.PROGRESSIVE
        return LoadingStrategy.EAGER

    def _detect_data_fetching(self, content: str) -> DataFetchingPattern:
        if re.search(r"\bgql\b|\buseMutation\b|\bApolloClient\b|\bgraphql\b", content):
            return DataFetchingPattern.GRAPHQL
        if re.search(r"\buseQuery\b|\buseSWR\b|\buseSuspenseQuery\b", content):
            return DataFetchingPattern.CLIENT_QUERY
        if re.search(r"\bWebSocket\b|\bio\s*\(|\bwss?://", content):
            return DataFetchingPattern.WEBSOCKET
        if re.search(r"\bEventSource\b", content):
            return DataFetchingPattern.SSE
        if "getServerSideProps" in content or "export default async function" in content:
            return DataFetchingPattern.SERVER_FETCH
        if re.search(r"\bfetch\s*\(|\baxios\.(?:get|post|put|delete)\(", content):
            return DataFetchingPattern.REST
        return DataFetchingPattern.NONE

    def _estimate_complexity(self, content: str) -> dict[str, Any]:
        tags = len(re.findall(r"<[A-Za-z0-9_]+", content))
        hooks = len(re.findall(r"\buse[A-Z]\w*", content))
        interactive = len(re.findall(r"\b(?:onClick|onChange|onSubmit|onKeyDown|<button|<input|<select|<textarea)\b", content))
        canvas_3d = bool(re.search(r"\bTHREE\b|\bWebGL\b|<canvas\b|\bScene\b|\bPerspectiveCamera\b", content))
        has_virtualization = bool(re.search(r"\bFixedSizeList\b|\bVariableSizeList\b|\buseVirtualizer\b|\breact-window\b", content))

        return {
            "elements": tags,
            "hooks": hooks,
            "interactive_elements": interactive,
            "visual_canvas": canvas_3d,
            "has_virtualization": has_virtualization,
            "lines": len(content.splitlines()),
        }

    def _detect_responsive_evidence(self, content: str) -> bool:
        if "@media" in content:
            return True
        if re.search(r"\b(?:sm:|md:|lg:|xl:|2xl:)", content):
            return True
        if re.search(r'<meta[^>]*name=[\'"]viewport[\'"]', content, re.IGNORECASE):
            return True
        if "useMediaQuery" in content:
            return True
        return False

    def _detect_asset_behaviors(self, content: str) -> list[str]:
        behaviors: list[str] = []
        if "next/image" in content or "<Image" in content:
            behaviors.append("next/image optimized component")
        if 'loading="lazy"' in content or "loading='lazy'" in content:
            behaviors.append("Native image lazy-loading")
        if "next/font" in content:
            behaviors.append("next/font self-hosted font optimization")
        if "@font-face" in content:
            behaviors.append("Custom font-face declaration")
        if re.search(r"<script[^>]+(?:defer|async)", content):
            behaviors.append("Deferred/Async script tags")
        if re.search(r"\.webp|\.avif", content, re.IGNORECASE):
            behaviors.append("Modern image format (WebP/AVIF)")
        return behaviors

    def _determine_page_type(
        self,
        file_path: Path,
        content: str,
        rendering: RenderingModel,
        complexity: dict[str, Any],
    ) -> PageType:
        if complexity.get("visual_canvas", False):
            return PageType.VISUAL_3D
        if file_path.suffix.lower() == ".html":
            return PageType.STATIC
        if rendering in (RenderingModel.SSR, RenderingModel.STREAMING):
            return PageType.SSR
        if rendering == RenderingModel.SSG:
            return PageType.STATIC
        if re.search(r"\bBrowserRouter\b|\bcreateBrowserRouter\b|\bRoutes\b", content):
            return PageType.SPA
        if complexity.get("interactive_elements", 0) > 10:
            return PageType.DYNAMIC
        return PageType.SPA
