"""Tests for FrontendPageAnalyzer across frameworks and architectural styles."""

from __future__ import annotations

from pathlib import Path

from sdat.frontend.models import (
    DataFetchingPattern,
    LoadingStrategy,
    PageType,
    RenderingModel,
)
from sdat.frontend.page_analyzer import FrontendPageAnalyzer


def test_discover_pages_nextjs_app_router(tmp_path: Path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "page.tsx").write_text("export default function Home() { return <h1>Home</h1>; }", encoding="utf-8")
    dash_dir = app_dir / "dashboard"
    dash_dir.mkdir()
    (dash_dir / "page.tsx").write_text("export default function Dashboard() { return <h1>Dash</h1>; }", encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    pages = analyzer.discover_page_files()
    assert len(pages) == 2
    analyses = analyzer.analyze_all_pages()
    routes = {a.route for a in analyses}
    assert routes == {"/", "/dashboard"}


def test_discover_pages_nextjs_pages_router(tmp_path: Path):
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    (pages_dir / "index.tsx").write_text("export default function Index() { return <div />; }", encoding="utf-8")
    (pages_dir / "about.tsx").write_text("export default function About() { return <div />; }", encoding="utf-8")
    (pages_dir / "_app.tsx").write_text("export default function App() { return <div />; }", encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    pages = analyzer.discover_page_files()
    assert len(pages) == 2
    analyses = analyzer.analyze_all_pages()
    routes = {a.route for a in analyses}
    assert routes == {"/", "/about"}


def test_discover_pages_html_multi_page(tmp_path: Path):
    (tmp_path / "index.html").write_text("<!DOCTYPE html><html><body><h1>Home</h1></body></html>", encoding="utf-8")
    (tmp_path / "contact.html").write_text("<!DOCTYPE html><html><body><h1>Contact</h1></body></html>", encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    analyses = analyzer.analyze_all_pages()
    assert len(analyses) == 2
    assert all(a.rendering_model == RenderingModel.STATIC_HTML for a in analyses)
    routes = {a.route for a in analyses}
    assert routes == {"/", "/contact"}


def test_analyze_react_csr_page_with_hooks_and_virtualization(tmp_path: Path):
    code = """'use client';
import React, { useState, useEffect, useMemo } from 'react';
import { FixedSizeList as List } from 'react-window';

export default function UserList() {
    const [users, setUsers] = useState([]);
    useEffect(() => { fetch('/api/users').then(r => r.json()).then(setUsers); }, []);
    const count = useMemo(() => users.length, [users]);

    return (
        <div className="sm:p-4 md:p-8">
            <button onClick={() => setUsers([])}>Clear</button>
            <List height={500} itemCount={count} itemSize={35} width={300}>
                {({ index, style }) => <div style={style}>User {index}</div>}
            </List>
        </div>
    );
}
"""
    f = tmp_path / "UserList.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    analysis = analyzer.analyze_page(f)

    assert analysis.rendering_model == RenderingModel.CSR
    assert analysis.approximate_complexity["has_virtualization"] is True
    assert analysis.approximate_complexity["hooks"] >= 3
    assert analysis.has_responsive_evidence is True
    assert analysis.data_fetching_pattern == DataFetchingPattern.REST


def test_analyze_heavy_3d_canvas_page(tmp_path: Path):
    code = """import * as THREE from 'three';
export default function CanvasDemo() {
    return <canvas id="scene" width="800" height="600"></canvas>;
}
"""
    f = tmp_path / "CanvasDemo.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    analysis = analyzer.analyze_page(f)

    assert analysis.page_type == PageType.VISUAL_3D
    assert analysis.approximate_complexity["visual_canvas"] is True
    assert any("3D/Canvas" in finding for finding in analysis.findings)


def test_analyze_page_with_xss_hazard(tmp_path: Path):
    code = """export default function RawHtmlView({ unsafeContent }) {
    return <div dangerouslySetInnerHTML={{ __html: unsafeContent }} />;
}
"""
    f = tmp_path / "RawView.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    analysis = analyzer.analyze_page(f)

    assert any("XSS" in finding for finding in analysis.findings)


def test_analyze_page_with_async_waterfall(tmp_path: Path):
    code = """export default async function ProfilePage() {
    const user = await fetchUser();
    const orders = await fetchOrders();
    const settings = await fetchSettings();
    return <div>{user.name}</div>;
}
"""
    f = tmp_path / "Profile.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    analysis = analyzer.analyze_page(f)

    assert any("waterfall" in finding.lower() for finding in analysis.findings)


def test_analyze_lazy_loaded_component_strategy(tmp_path: Path):
    code = """import React, { Suspense } from 'react';
const HeavyChart = React.lazy(() => import('./HeavyChart'));

export default function Dashboard() {
    return (
        <Suspense fallback={<div>Loading chart...</div>}>
            <HeavyChart />
        </Suspense>
    );
}
"""
    f = tmp_path / "Dashboard.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    analysis = analyzer.analyze_page(f)

    assert analysis.loading_strategy == LoadingStrategy.LAZY
    assert analysis.dimension_results["has_suspense"] is True
