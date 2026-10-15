"""Tests for Rust scanner (Phase 4B) — protocol, evidence extraction, robustness, fixture."""

from __future__ import annotations

from pathlib import Path

from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import EvidenceKind, SignalKind
from sdat.scanners.base import LanguageScanner
from sdat.scanners.registry import (
    extension_to_scanner,
    get_scanner,
    get_scanner_for_file,
)
from sdat.scanners.rust_scanner import RustScanner


class TestRustScannerProtocol:
    """Protocol conformance and file discovery tests."""

    def setup_method(self):
        self.scanner = RustScanner()

    def test_protocol_conformance(self):
        assert isinstance(self.scanner, LanguageScanner)
        assert self.scanner.language_id == "rust"
        assert ".rs" in self.scanner.file_extensions

    def test_discover_files_empty_dir(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path) == []

    def test_discover_files_finds_rs(self, tmp_path: Path):
        (tmp_path / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
        (tmp_path / "lib.rs").write_text("pub fn lib() {}\n", encoding="utf-8")
        (tmp_path / "readme.md").write_text("# Rust", encoding="utf-8")
        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 2
        assert all(f.suffix == ".rs" for f in files)

    def test_discover_files_excludes_target_and_git(self, tmp_path: Path):
        (tmp_path / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "build.rs").write_text("fn main() {}\n", encoding="utf-8")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hook.rs").write_text("fn main() {}\n", encoding="utf-8")

        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "main.rs"

    def test_discover_files_nonexistent_root(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path / "ghost") == []


class TestRustScannerEvidenceExtraction:
    """Validate extraction of typed EvidenceFacts across Rust system design patterns."""

    def setup_method(self):
        self.scanner = RustScanner()

    def test_detect_tokio_async_and_concurrency(self, tmp_path: Path):
        code = """use std::sync::Arc;
use tokio::sync::Mutex;
#[tokio::main]
async fn main() {
    let counter = Arc::new(Mutex::new(0));
    tokio::spawn(async move {
        println!("worker");
    });
}
"""
        f = tmp_path / "main.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        kinds = {fact.kind for fact in facts}
        assert EvidenceKind.ASYNC_PATTERN in kinds or EvidenceKind.CONCURRENCY in kinds
        concurrency_facts = [f for f in facts if "tokio::spawn" in f.subject or "Arc<Mutex<" in f.subject]
        assert len(concurrency_facts) >= 1

    def test_detect_axum_web_framework(self, tmp_path: Path):
        code = """use axum::{routing::get, Router};
pub fn app() -> Router {
    Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/api/items", get(|| async { "items" }))
}
"""
        f = tmp_path / "web.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        axum_facts = [f for f in facts if "axum" in (f.framework or "") or "Router::new" in f.subject]
        assert len(axum_facts) >= 1

    def test_detect_sqlx_connection_pooling(self, tmp_path: Path):
        code = """use sqlx::postgres::PgPoolOptions;
use sqlx::PgPool;
pub async fn init_db(url: &str) -> Result<PgPool, sqlx::Error> {
    PgPoolOptions::new()
        .max_connections(25)
        .min_connections(5)
        .connect(url)
        .await
}
"""
        f = tmp_path / "db.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        pool_facts = [f for f in facts if "PgPoolOptions" in f.subject or "max_connections" in f.subject]
        assert len(pool_facts) >= 1

    def test_detect_redis_caching(self, tmp_path: Path):
        code = """use redis::AsyncCommands;
pub async fn cache_data(client: &redis::Client, key: &str, val: &str) -> redis::RedisResult<()> {
    let mut conn = client.get_multiplexed_async_connection().await?;
    conn.set_ex(key, val, 300).await?;
    Ok(())
}
"""
        f = tmp_path / "cache.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cache_facts = [f for f in facts if "redis" in (f.library or "") or ".set_ex" in f.subject]
        assert len(cache_facts) >= 1
        assert any(f.ttl_observed is True for f in cache_facts)

    def test_detect_retries_and_backoff(self, tmp_path: Path):
        code = """use backoff::ExponentialBackoff;
pub async fn fetch_with_retry() {
    let b = ExponentialBackoff::default();
    let _ = backoff::future::retry(b, || async { Ok(()) }).await;
}
"""
        f = tmp_path / "retry.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        retry_facts = [f for f in facts if "backoff" in f.subject]
        assert len(retry_facts) >= 1

    def test_detect_message_queue_lapin_rdkafka(self, tmp_path: Path):
        code = """use rdkafka::producer::FutureProducer;
pub fn new_producer() -> FutureProducer {
    unimplemented!()
}
"""
        f = tmp_path / "mq.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        mq_facts = [f for f in facts if "rdkafka" in f.subject or "FutureProducer" in f.subject]
        assert len(mq_facts) >= 1

    def test_detect_logging_tracing(self, tmp_path: Path):
        code = """use tracing::info;
pub fn log_event() {
    tracing::info!("request handled");
}
"""
        f = tmp_path / "log.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        log_facts = [f for f in facts if "tracing" in f.subject]
        assert len(log_facts) >= 1

    def test_detect_no_std_embedded(self, tmp_path: Path):
        code = """#![no_std]
use cortex_m::asm::nop;
pub fn init() {
    nop();
}
"""
        f = tmp_path / "lib.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        embedded_facts = [f for f in facts if "#![no_std]" in f.snippet or "cortex_m" in f.subject]
        assert len(embedded_facts) >= 1

    def test_detect_hardcoded_secrets_weakness(self, tmp_path: Path):
        code = """pub const API_KEY: &str = "sk_live_99887766554433221100";\n"""
        f = tmp_path / "secret.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)
        signals = self.scanner.scan_file(f)

        assert any(f.kind == EvidenceKind.CONFIG_KEY and "hardcoded_credential" in f.subject for f in facts)
        assert any(s.kind == SignalKind.WEAKNESS for s in signals)

    def test_detect_networking_and_p2p(self, tmp_path: Path):
        code = """use std::net::TcpListener;
use libp2p::Swarm;
pub fn init_node() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
}
"""
        f = tmp_path / "net.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("TcpListener" in s for s in subjects)
        assert any("libp2p" in s for s in subjects)

    def test_detect_cli_and_tooling(self, tmp_path: Path):
        code = """use clap::Parser;
use std::process::Command;
#[derive(Parser)]
pub struct CliArgs {
    pub name: String,
}
pub fn run_worker() {
    Command::new("ls").status().unwrap();
}
"""
        f = tmp_path / "cli.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("clap" in s for s in subjects)
        assert any("Command" in s for s in subjects)

    def test_detect_web3_structural_evidence(self, tmp_path: Path):
        code = """use ethers::providers::{Provider, Http};
use ethers::types::TransactionRequest;
pub async fn send_eth() {
    let provider = Provider::<Http>::try_from("https://rpc.example.com").unwrap();
    let tx = TransactionRequest::new();
    let _ = provider.send_transaction(tx, None).await;
}
"""
        f = tmp_path / "web3.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("Provider" in s for s in subjects)
        assert any("TransactionRequest" in s for s in subjects)
        assert any("send_transaction" in s for s in subjects)

    def test_evidence_provenance(self, tmp_path: Path):
        code = """use std::time::Duration;
pub fn handler() {
    let _ = tokio::time::sleep(Duration::from_secs(1));
}
"""
        f = tmp_path / "prov.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        scoped_facts = [f for f in facts if f.scope == "handler"]
        assert len(scoped_facts) >= 1
        fact = scoped_facts[0]
        assert fact.file_path == f
        assert fact.line_range[0] >= 1
        assert "tokio::time::sleep" in fact.snippet
        assert fact.scope == "handler"
        assert fact.language == "rust"

    def test_aggregator_compatibility(self, tmp_path: Path):
        code = """use redis::AsyncCommands;
pub async fn cache_val(con: &mut redis::aio::Connection) {
    let _: () = con.set("k", "v").await.unwrap();
}
"""
        f = tmp_path / "agg.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        aggregator = EvidenceAggregator()
        bundles = aggregator.aggregate(facts)
        assert isinstance(bundles, list)
        caching = [b for b in bundles if b.concept_id == "foundation.caching"]
        assert len(caching) >= 1


class TestRustScannerRobustness:
    """Validate meaningless names and misleading names."""

    def setup_method(self):
        self.scanner = RustScanner()

    def test_meaningless_names_with_real_architecture(self, tmp_path: Path):
        code = """use sqlx::postgres::PgPoolOptions;
use std::time::Duration;
pub async fn fn_x9(u: &str) {
    let p = PgPoolOptions::new()
        .max_connections(32)
        .connect(u)
        .await;
    tokio::time::sleep(Duration::from_secs(1)).await;
}
"""
        f = tmp_path / "m1.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("PgPoolOptions" in s or "max_connections" in s for s in subjects)

    def test_misleading_names_without_architecture(self, tmp_path: Path):
        code = """pub fn retry_payment() -> bool {
    true
}
pub fn circuit_breaker_manager() -> i32 {
    42
}
"""
        f = tmp_path / "fake.rs"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)
        signals = self.scanner.scan_file(f)

        assert len([f for f in facts if "backoff" in f.subject.lower()]) == 0
        assert len([f for f in facts if "failsafe" in f.subject.lower()]) == 0
        retry_signals = [s for s in signals if s.concept_id == "foundation.retries" and s.kind == SignalKind.PRESENCE]
        assert len(retry_signals) == 0


class TestRustScannerRegistryAndEdgeCases:
    """Registry resolution and edge cases."""

    def setup_method(self):
        self.scanner = RustScanner()

    def test_registry_lookup(self):
        cfg = get_scanner("rust")
        assert cfg is not None
        assert cfg.get("enabled") is True
        assert ".rs" in cfg.get("extensions", [])

    def test_registry_extension_to_scanner(self):
        assert extension_to_scanner(".rs") == "rust"
        assert extension_to_scanner("rs") == "rust"

    def test_registry_get_scanner_for_file(self, tmp_path: Path):
        f = tmp_path / "main.rs"
        scanner = get_scanner_for_file(f)
        assert isinstance(scanner, RustScanner)

    def test_empty_file_returns_no_facts(self, tmp_path: Path):
        f = tmp_path / "empty.rs"
        f.write_text("", encoding="utf-8")
        assert self.scanner.scan_file_evidence(f) == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        assert self.scanner.scan_file_evidence(tmp_path / "ghost.rs") == []

    def test_determinism(self, tmp_path: Path):
        code = "use tokio::spawn;\nfn run() { tokio::spawn(async {}); }\n"
        f = tmp_path / "det.rs"
        f.write_text(code, encoding="utf-8")
        r1 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        r2 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        assert r1 == r2


class TestRustScannerFixture:
    """Validate Rust scanner on tests/fixtures/rust_project/."""

    def setup_method(self):
        self.scanner = RustScanner()
        self.fixture_dir = Path("tests/fixtures/rust_project")

    def test_fixture_directory_exists(self):
        assert self.fixture_dir.exists()
        assert self.fixture_dir.is_dir()

    def test_fixture_file_discovery(self):
        discovered = self.scanner.discover_files(self.fixture_dir)
        names = {f.name for f in discovered}
        expected = {"main.rs", "config.rs", "db.rs", "cache.rs", "worker.rs"}
        assert expected == names

    def test_fixture_evidence_categories_exceeds_threshold(self):
        file_evidence = self.scanner.scan_project_evidence(self.fixture_dir)
        assert len(file_evidence) == 5

        categories: set[str] = set()
        for fe in file_evidence:
            for fact in fe.facts:
                for hint in fact.identifier_hints:
                    if "." in hint:
                        categories.add(hint)

        assert len(categories) >= 10
        assert "api.rest" in categories
        assert "foundation.concurrency" in categories
        assert "foundation.connection-pooling" in categories
        assert "foundation.caching" in categories
        assert "foundation.retries" in categories
        assert "foundation.logging" in categories
        assert "foundation.config" in categories
        assert "foundation.health-checks" in categories
