"""Tests for Go scanner (Phase 4A) — protocol, evidence extraction, robustness, fixture."""

from __future__ import annotations

from pathlib import Path

from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import EvidenceKind, SignalKind
from sdat.scanners.base import LanguageScanner
from sdat.scanners.go_scanner import GoScanner
from sdat.scanners.registry import (
    extension_to_scanner,
    get_scanner,
    get_scanner_for_file,
)


class TestGoScannerProtocol:
    """Protocol conformance and file discovery tests."""

    def setup_method(self):
        self.scanner = GoScanner()

    def test_protocol_conformance(self):
        assert isinstance(self.scanner, LanguageScanner)
        assert self.scanner.language_id == "go"
        assert ".go" in self.scanner.file_extensions

    def test_discover_files_empty_dir(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path) == []

    def test_discover_files_finds_go(self, tmp_path: Path):
        (tmp_path / "main.go").write_text("package main\n", encoding="utf-8")
        (tmp_path / "util.go").write_text("package main\n", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("notes", encoding="utf-8")
        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 2
        assert all(f.suffix == ".go" for f in files)

    def test_discover_files_excludes_default_ignored_dirs(self, tmp_path: Path):
        (tmp_path / "app.go").write_text("package main\n", encoding="utf-8")
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "dep.go").write_text("package dep\n", encoding="utf-8")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hook.go").write_text("package hook\n", encoding="utf-8")

        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "app.go"

    def test_discover_files_nonexistent_root(self, tmp_path: Path):
        missing = tmp_path / "not_there"
        assert self.scanner.discover_files(missing) == []


class TestGoScannerEvidenceExtraction:
    """Validate extraction of typed EvidenceFacts across key system design patterns."""

    def setup_method(self):
        self.scanner = GoScanner()

    def test_detect_redis_caching_evidence(self, tmp_path: Path):
        code = """package cache
import "github.com/redis/go-redis/v9"
func InitCache() {
    client := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
    client.Set(ctx, "k", "v", time.Minute)
}
"""
        f = tmp_path / "cache.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        kinds = {fact.kind for fact in facts}
        assert EvidenceKind.IMPORT in kinds or EvidenceKind.INSTANTIATION in kinds
        redis_facts = [fact for fact in facts if "redis" in fact.subject.lower()]
        assert len(redis_facts) >= 1

    def test_detect_concurrency_and_goroutines(self, tmp_path: Path):
        code = """package worker
import "sync"
func ProcessJobs() {
    var wg sync.WaitGroup
    ch := make(chan int, 10)
    go func() {
        select {
        case msg := <-ch:
            _ = msg
        }
    }()
}
"""
        f = tmp_path / "worker.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        concurrency_facts = [f for f in facts if f.kind == EvidenceKind.CONCURRENCY]
        assert len(concurrency_facts) >= 2

    def test_detect_context_timeout_resilience(self, tmp_path: Path):
        code = """package api
import (
    "context"
    "time"
)
func FetchData() {
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()
}
"""
        f = tmp_path / "fetch.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        timeout_facts = [f for f in facts if "context.WithTimeout" in f.subject or f.timeout_observed is True]
        assert len(timeout_facts) >= 1

    def test_detect_connection_pooling(self, tmp_path: Path):
        code = """package db
import "database/sql"
func SetupDB(db *sql.DB) {
    db.SetMaxOpenConns(50)
    db.SetMaxIdleConns(10)
    db.SetConnMaxLifetime(time.Hour)
}
"""
        f = tmp_path / "db.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        pool_facts = [f for f in facts if "SetMaxOpenConns" in f.subject or "SetMaxIdleConns" in f.subject]
        assert len(pool_facts) >= 1

    def test_detect_circuit_breaker(self, tmp_path: Path):
        code = """package client
import "github.com/sony/gobreaker"
func NewCB() *gobreaker.CircuitBreaker {
    return gobreaker.NewCircuitBreaker(gobreaker.Settings{Name: "HTTP"})
}
"""
        f = tmp_path / "cb.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cb_facts = [f for f in facts if "gobreaker" in f.subject or "gobreaker" in (f.library or "")]
        assert len(cb_facts) >= 1

    def test_detect_retries_and_backoff(self, tmp_path: Path):
        code = """package task
import "github.com/cenkalti/backoff/v4"
func Run() {
    b := backoff.NewExponentialBackOff()
    _ = backoff.Retry(func() error { return nil }, b)
}
"""
        f = tmp_path / "task.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        retry_facts = [f for f in facts if "backoff" in f.subject]
        assert len(retry_facts) >= 1

    def test_detect_rate_limiting(self, tmp_path: Path):
        code = """package mw
import "golang.org/x/time/rate"
func Limiter() *rate.Limiter {
    return rate.NewLimiter(10, 20)
}
"""
        f = tmp_path / "rate.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        rate_facts = [f for f in facts if "rate" in f.subject]
        assert len(rate_facts) >= 1

    def test_detect_observability_prometheus(self, tmp_path: Path):
        code = """package metrics
import "github.com/prometheus/client_golang/prometheus"
var counter = prometheus.NewCounter(prometheus.CounterOpts{Name: "ops"})
"""
        f = tmp_path / "metrics.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        prom_facts = [f for f in facts if "prometheus" in f.subject]
        assert len(prom_facts) >= 1

    def test_detect_logging_zap(self, tmp_path: Path):
        code = """package log
import "go.uber.org/zap"
func InitLogger() {
    logger, _ := zap.NewProduction()
    logger.Info("started")
}
"""
        f = tmp_path / "log.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        log_facts = [f for f in facts if "zap" in f.subject or "logger.Info" in f.subject]
        assert len(log_facts) >= 1

    def test_detect_config_environment(self, tmp_path: Path):
        code = """package config
import "os"
func GetPort() string {
    return os.Getenv("PORT")
}
"""
        f = tmp_path / "config.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        env_facts = [f for f in facts if f.kind == EvidenceKind.ENV_VAR]
        assert len(env_facts) >= 1

    def test_detect_message_queue_kafka(self, tmp_path: Path):
        code = """package queue
import "github.com/segmentio/kafka-go"
func NewProducer() *kafka.Writer {
    return kafka.NewWriter(kafka.WriterConfig{Topic: "events"})
}
"""
        f = tmp_path / "queue.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        kafka_facts = [f for f in facts if "kafka" in f.subject]
        assert len(kafka_facts) >= 1

    def test_detect_networking_and_sockets(self, tmp_path: Path):
        code = """package netdaemon
import "net"
func StartServer() {
    l, _ := net.Listen("tcp", ":8080")
    defer l.Close()
    conn, _ := net.Dial("tcp", "127.0.0.1:8080")
    defer conn.Close()
}
"""
        f = tmp_path / "net.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        net_facts = [f for f in facts if "net.Listen" in f.subject or "net.Dial" in f.subject]
        assert len(net_facts) == 2
        assert all(f.kind == EvidenceKind.CALL for f in net_facts)

    def test_detect_cli_and_tooling(self, tmp_path: Path):
        code = """package main
import (
    "flag"
    "os/exec"
)
func main() {
    flag.StringVar(&name, "name", "world", "usage")
    flag.Parse()
    cmd := exec.Command("ls", "-la")
    cmd.Run()
}
"""
        f = tmp_path / "cli.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cli_facts = [f for f in facts if "flag." in f.subject or "exec.Command" in f.subject]
        assert len(cli_facts) >= 2

    def test_detect_web3_structural_evidence(self, tmp_path: Path):
        code = """package eth
import (
    "context"
    "github.com/ethereum/go-ethereum/ethclient"
    "github.com/ethereum/go-ethereum/core/types"
)
func SendTx(ctx context.Context) {
    client, _ := ethclient.Dial("https://rpc.example.com")
    nonce, _ := client.PendingNonceAt(ctx, addr)
    tx := types.NewTransaction(nonce, to, amount, gasLimit, gasPrice, nil)
    signedTx, _ := types.SignTx(tx, signer, key)
    _ = client.SendTransaction(ctx, signedTx)
}
"""
        f = tmp_path / "web3.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("ethclient.Dial" in s for s in subjects)
        assert any("PendingNonceAt" in s for s in subjects)
        assert any("types.NewTransaction" in s for s in subjects)
        assert any("types.SignTx" in s for s in subjects)
        assert any("SendTransaction" in s for s in subjects)

    def test_evidence_provenance(self, tmp_path: Path):
        code = """package sample
import "sync"
func Worker() {
    var mu sync.Mutex
    _ = mu
}
"""
        f = tmp_path / "provenance.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        mutex_facts = [f for f in facts if "sync.Mutex" in f.subject]
        assert len(mutex_facts) >= 1
        fact = mutex_facts[0]
        assert fact.file_path == f
        assert fact.line_range[0] >= 1
        assert "sync.Mutex" in fact.snippet
        assert fact.scope == "Worker"
        assert fact.language == "go"

    def test_aggregator_compatibility(self, tmp_path: Path):
        code = """package cache
import (
    "time"
    "github.com/redis/go-redis/v9"
)
func Setup() {
    client := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
    client.Set(ctx, "k", "v", 10*time.Minute)
}
"""
        f = tmp_path / "agg.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        aggregator = EvidenceAggregator()
        bundles = aggregator.aggregate(facts)
        assert isinstance(bundles, list)
        caching_bundles = [b for b in bundles if b.concept_id == "foundation.caching"]
        assert len(caching_bundles) >= 1
        assert len(caching_bundles[0].facts) >= 1



class TestGoScannerRobustness:
    """Critical Rule 4 & AI-Generated Code Robustness Tests."""

    def setup_method(self):
        self.scanner = GoScanner()

    def test_meaningless_names_with_real_architecture(self, tmp_path: Path):
        """Obfuscated / AI-generated identifiers with genuine system design patterns."""
        code = """package p9
import (
    "context"
    "database/sql"
    "time"
)
func x1(db1 *sql.DB) {
    db1.SetMaxOpenConns(42)
    db1.SetMaxIdleConns(8)
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()
    _ = ctx
}
"""
        f = tmp_path / "a1.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        # Must detect SetMaxOpenConns (connection pooling) and context.WithTimeout (timeout)
        subjects = {f.subject for f in facts}
        assert any("SetMaxOpenConns" in s for s in subjects)
        assert any("context.WithTimeout" in s for s in subjects)

    def test_misleading_function_name_without_architecture(self, tmp_path: Path):
        """Misleading name like retryPayment or circuitBreaker should NOT produce presence facts."""
        code = """package payments

func retryPayment() string {
    return "done"
}

func circuitBreakerManager() int {
    return 100
}
"""
        f = tmp_path / "pay.go"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)
        signals = self.scanner.scan_file(f)

        assert len([f for f in facts if "retry" in f.subject.lower()]) == 0
        assert len([f for f in facts if "circuit" in f.subject.lower()]) == 0

        # No genuine retry or circuit breaker libraries or mechanisms used
        retry_signals = [s for s in signals if s.concept_id == "foundation.retries" and s.kind == SignalKind.PRESENCE]
        cb_signals = [s for s in signals if s.concept_id == "foundation.circuit-breaker" and s.kind == SignalKind.PRESENCE]
        assert len(retry_signals) == 0
        assert len(cb_signals) == 0


class TestGoScannerRegistryAndEdgeCases:
    """Registry integration and defensive edge cases."""

    def setup_method(self):
        self.scanner = GoScanner()

    def test_registry_lookup(self):
        cfg = get_scanner("go")
        assert cfg is not None
        assert cfg.get("enabled") is True
        assert ".go" in cfg.get("extensions", [])

    def test_registry_resolution(self):
        assert extension_to_scanner(".go") == "go"
        assert extension_to_scanner("go") == "go"

    def test_registry_get_scanner_for_file(self, tmp_path: Path):
        f = tmp_path / "service.go"
        scanner = get_scanner_for_file(f)
        assert isinstance(scanner, GoScanner)

    def test_empty_file_returns_no_facts_without_crash(self, tmp_path: Path):
        f = tmp_path / "empty.go"
        f.write_text("", encoding="utf-8")
        assert self.scanner.scan_file_evidence(f) == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        missing = tmp_path / "ghost.go"
        assert self.scanner.scan_file_evidence(missing) == []

    def test_directory_passed_to_scan_file_returns_empty(self, tmp_path: Path):
        d = tmp_path / "adir"
        d.mkdir()
        assert self.scanner.scan_file_evidence(d) == []

    def test_determinism(self, tmp_path: Path):
        code = "package main\nimport \"sync\"\nfunc run() { var mu sync.Mutex; mu.Lock(); mu.Unlock() }\n"
        f = tmp_path / "det.go"
        f.write_text(code, encoding="utf-8")
        run1 = [fact.to_dict() for fact in self.scanner.scan_file_evidence(f)]
        run2 = [fact.to_dict() for fact in self.scanner.scan_file_evidence(f)]
        assert run1 == run2


class TestGoScannerFixture:
    """Validate Go scanner on the representative ~200 LOC tests/fixtures/go_project fixture."""

    def setup_method(self):
        self.scanner = GoScanner()
        self.fixture_dir = Path("tests/fixtures/go_project")

    def test_fixture_directory_exists(self):
        assert self.fixture_dir.exists()
        assert self.fixture_dir.is_dir()

    def test_fixture_file_discovery(self):
        discovered = self.scanner.discover_files(self.fixture_dir)
        names = {f.name for f in discovered}
        expected = {"server.go", "config.go", "cache.go", "db.go", "worker.go"}
        assert expected == names

    def test_fixture_evidence_categories_exceeds_threshold(self):
        """Verify that the fixture scan produces ≥ 10 distinct concept categories/signals."""
        file_evidence = self.scanner.scan_project_evidence(self.fixture_dir)
        assert len(file_evidence) == 5

        categories: set[str] = set()
        for fe in file_evidence:
            for fact in fe.facts:
                for hint in fact.identifier_hints:
                    if "." in hint:
                        categories.add(hint)

        assert len(categories) >= 10
        # Expected categories in the fixture:
        assert "foundation.caching" in categories
        assert "foundation.connection-pooling" in categories
        assert "foundation.concurrency" in categories
        assert "resilience.timeout" in categories
        assert "foundation.retries" in categories
        assert "foundation.logging" in categories
        assert "foundation.config" in categories
        assert "api.rest" in categories
        assert "foundation.health-checks" in categories
        assert "foundation.idempotency" in categories
