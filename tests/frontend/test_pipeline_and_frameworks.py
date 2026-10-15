"""Multi-framework validation and end-to-end frontend pipeline tests.

Verifies that the Frontend KnowledgePack and Agent audit system-design
principles across HTML/CSS/JS, React, Next.js, GraphQL, WebSockets,
Visual/3D, and Web3, independent of framework labels.
"""

from __future__ import annotations

from pathlib import Path

from sdat.frontend.agent import FrontendAgent
from sdat.frontend.knowledge_pack import FrontendKnowledgePack
from sdat.frontend.models import DataFetchingPattern, RenderingModel
from sdat.frontend.page_analyzer import FrontendPageAnalyzer
from sdat.models import DecisionStatus, EvidenceFact, EvidenceKind


def test_framework_neutral_static_html(tmp_path: Path):
    """HTML + CSS + vanilla JS without any framework."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @media (min-width: 768px) { .container { display: flex; } }
    </style>
</head>
<body>
    <header><h1>Static Portfolio</h1></header>
    <main>
        <img src="avatar.webp" alt="Author Profile" loading="lazy" width="200" height="200">
        <button aria-label="Open Navigation" id="menu-btn">Menu</button>
    </main>
</body>
</html>
"""
    (tmp_path / "index.html").write_text(html, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    pages = analyzer.analyze_all_pages()
    assert len(pages) == 1
    page = pages[0]
    assert page.rendering_model == RenderingModel.STATIC_HTML
    assert page.has_responsive_evidence is True
    assert "Native image lazy-loading" in page.asset_behavior

    kp = FrontendKnowledgePack()
    results = kp.evaluate(facts=[], pages=pages)

    # Both responsive and a11y rules should pass
    resp_res = [r for r in results if r.rule.id == "FE-RESP-01"][0]
    assert resp_res.status == DecisionStatus.IMPLEMENTED

    a11y_res = [r for r in results if r.rule.id == "FE-A11Y-01"][0]
    assert a11y_res.status == DecisionStatus.IMPLEMENTED


def test_framework_neutral_graphql_frontend(tmp_path: Path):
    """Frontend utilizing GraphQL client query architecture."""
    code = """import { useQuery, gql } from '@apollo/client';
const GET_FEED = gql`query GetFeed { feed { id title } }`;

export default function FeedView() {
    const { loading, error, data } = useQuery(GET_FEED);
    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error loading feed</div>;
    return <ul>{data.feed.map(item => <li key={item.id}>{item.title}</li>)}</ul>;
}
"""
    f = tmp_path / "Feed.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    page = analyzer.analyze_page(f)
    assert page.data_fetching_pattern == DataFetchingPattern.GRAPHQL

    kp = FrontendKnowledgePack()
    results = kp.evaluate(facts=[], pages=[page])
    data_res = [r for r in results if r.rule.id == "FE-DATA-01"][0]
    assert data_res.status == DecisionStatus.IMPLEMENTED


def test_framework_neutral_websocket_frontend(tmp_path: Path):
    """Frontend utilizing WebSocket bidirectional streaming."""
    code = """import { useEffect, useState } from 'react';
export default function LiveTicker() {
    const [price, setPrice] = useState(0);
    useEffect(() => {
        const ws = new WebSocket('wss://stream.exchange.com/ticker');
        ws.onmessage = (e) => setPrice(JSON.parse(e.data).price);
        return () => ws.close();
    }, []);
    return <div>Live Price: {price}</div>;
}
"""
    f = tmp_path / "Ticker.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    page = analyzer.analyze_page(f)
    assert page.data_fetching_pattern == DataFetchingPattern.WEBSOCKET


def test_framework_neutral_web3_frontend(tmp_path: Path):
    """Web3 React frontend utilizing wagmi and wallet connect hooks."""
    code = """import { useAccount, useConnect, useDisconnect } from 'wagmi';
export default function Web3Header() {
    const { address, isConnected } = useAccount();
    return (
        <div>
            {isConnected ? <span>Connected: {address}</span> : <button>Connect Wallet</button>}
        </div>
    );
}
"""
    f = tmp_path / "Web3Header.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    page = analyzer.analyze_page(f)
    assert page.dimension_results["is_web3"] is True

    kp = FrontendKnowledgePack()
    results = kp.evaluate(facts=[], pages=[page])
    w3_res = [r for r in results if r.rule.id == "FE-W3-01"]
    assert len(w3_res) == 1
    assert w3_res[0].status == DecisionStatus.IMPLEMENTED


def test_misleading_names_without_architecture(tmp_path: Path):
    """File named 'virtual_list.tsx' without real list windowing architecture."""
    code = """export default function MyComponent() {
    return <div>Fake virtual list placeholder</div>;
}
"""
    f = tmp_path / "virtual_list.tsx"
    f.write_text(code, encoding="utf-8")

    analyzer = FrontendPageAnalyzer(tmp_path)
    page = analyzer.analyze_page(f)
    assert page.approximate_complexity["has_virtualization"] is False


def test_full_pipeline_with_scanner_facts(tmp_path: Path):
    """Simulates the full SDAT pipeline: facts -> page analysis -> agent -> score."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "page.tsx").write_text("""import Link from 'next/link';
import Image from 'next/image';
export default function Landing() {
    return (
        <div className="sm:m-2 md:m-4">
            <Image src="/hero.webp" alt="Hero banner" width={600} height={300} priority />
            <Link href="/about">About Us</Link>
        </div>
    );
}
""", encoding="utf-8")

    fact = EvidenceFact(
        kind=EvidenceKind.IMPORT,
        subject="next/image",
        language="typescript",
        file_path=app_dir / "page.tsx",
        line_range=(2, 2),
        snippet="import Image from 'next/image';",
        framework="nextjs",
    )

    agent = FrontendAgent()
    context = {
        "target_root": str(tmp_path),
        "run_id": "pipeline-test",
        "evidence_facts": [fact],
    }

    result = agent.audit(context)
    assert result["agent_id"] == "D-21"
    fa = result["frontend_audit"]
    assert len(fa["pages"]) == 1
    assert "rendering" in fa["dimension_scores"]
    assert "assets" in fa["dimension_scores"]
    assert fa["overall_score"] is not None
