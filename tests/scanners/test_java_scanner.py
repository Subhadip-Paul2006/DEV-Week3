"""Tests for Java/Kotlin scanner (Phase 4E) — protocol, evidence extraction, robustness, fixture."""

from __future__ import annotations

from pathlib import Path

from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import EvidenceKind, SignalKind
from sdat.scanners.base import LanguageScanner
from sdat.scanners.java_scanner import JavaScanner
from sdat.scanners.registry import (
    extension_to_scanner,
    get_scanner,
    get_scanner_for_file,
)


class TestJavaScannerProtocol:
    """Protocol conformance and file discovery tests."""

    def setup_method(self):
        self.scanner = JavaScanner()

    def test_protocol_conformance(self):
        assert isinstance(self.scanner, LanguageScanner)
        assert self.scanner.language_id == "java"
        assert ".java" in self.scanner.file_extensions
        assert ".kt" in self.scanner.file_extensions

    def test_discover_files_empty_dir(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path) == []

    def test_discover_files_finds_java_and_kt(self, tmp_path: Path):
        (tmp_path / "App.java").write_text("class App {}", encoding="utf-8")
        (tmp_path / "Worker.kt").write_text("class Worker", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("notes", encoding="utf-8")
        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"App.java", "Worker.kt"}

    def test_discover_files_excludes_gradle_and_target(self, tmp_path: Path):
        (tmp_path / "App.java").write_text("class App {}", encoding="utf-8")
        gradle_dir = tmp_path / ".gradle"
        gradle_dir.mkdir()
        (gradle_dir / "Cache.java").write_text("class Cache {}", encoding="utf-8")
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "Build.kt").write_text("class Build", encoding="utf-8")

        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "App.java"

    def test_discover_files_nonexistent_root(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path / "ghost") == []


class TestJavaScannerEvidenceExtraction:
    """Validate extraction of typed EvidenceFacts across Java/Kotlin patterns."""

    def setup_method(self):
        self.scanner = JavaScanner()

    def test_detect_spring_rest_controller(self, tmp_path: Path):
        code = """package com.example;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api")
public class ApiController {
    @GetMapping("/users")
    public String getUsers() { return "[]"; }
}
"""
        f = tmp_path / "ApiController.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        rest_facts = [f for f in facts if "@RestController" in f.subject or "@GetMapping" in f.subject]
        assert len(rest_facts) >= 2

    def test_detect_resilience4j_circuit_breaker(self, tmp_path: Path):
        code = """package com.example;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
public class Client {
    @CircuitBreaker(name = "backendA", fallbackMethod = "fallback")
    public String call() { return "ok"; }
}
"""
        f = tmp_path / "Client.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cb_facts = [f for f in facts if "@CircuitBreaker" in f.subject]
        assert len(cb_facts) >= 1

    def test_detect_spring_retry(self, tmp_path: Path):
        code = """package com.example;
import org.springframework.retry.annotation.Retryable;
public class RetryService {
    @Retryable(maxAttempts = 3)
    public void execute() {}
}
"""
        f = tmp_path / "RetryService.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        retry_facts = [f for f in facts if "@Retryable" in f.subject]
        assert len(retry_facts) >= 1

    def test_detect_hikaricp_connection_pooling(self, tmp_path: Path):
        code = """package com.example;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
public class DB {
    public void setup() {
        HikariConfig cfg = new HikariConfig();
        cfg.setMaximumPoolSize(20);
    }
}
"""
        f = tmp_path / "DB.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        pool_facts = [f for f in facts if "HikariConfig" in f.subject or "maximumPoolSize" in f.subject]
        assert len(pool_facts) >= 1

    def test_detect_spring_caching(self, tmp_path: Path):
        code = """package com.example;
import org.springframework.cache.annotation.Cacheable;
public class CacheService {
    @Cacheable("products")
    public String getProduct(String id) { return id; }
}
"""
        f = tmp_path / "CacheService.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cache_facts = [f for f in facts if "@Cacheable" in f.subject]
        assert len(cache_facts) >= 1

    def test_detect_kafka_listener(self, tmp_path: Path):
        code = """package com.example;
import org.springframework.kafka.annotation.KafkaListener;
public class Consumer {
    @KafkaListener(topics = "events")
    public void listen(String payload) {}
}
"""
        f = tmp_path / "Consumer.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        kafka_facts = [f for f in facts if "@KafkaListener" in f.subject]
        assert len(kafka_facts) >= 1

    def test_detect_kotlin_coroutines(self, tmp_path: Path):
        code = """package com.example
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
class AsyncWorker {
    suspend fun doWork() = withContext(Dispatchers.IO) {
        println("working")
    }
}
"""
        f = tmp_path / "AsyncWorker.kt"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        coroutine_facts = [f for f in facts if "suspend fun" in f.subject or "Dispatchers.IO" in f.subject]
        assert len(coroutine_facts) >= 1

    def test_detect_cli_and_tooling(self, tmp_path: Path):
        code = """package com.example.cli;
import picocli.CommandLine;
import picocli.CommandLine.Command;
@Command(name = "sync", mixinStandardHelpOptions = true)
public class SyncCli implements Runnable {
    public void run() {
        CommandLine.call(new SyncCli());
    }
}
"""
        f = tmp_path / "SyncCli.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cli_facts = [f for f in facts if any("tooling.cli" in h for h in f.identifier_hints)]
        assert len(cli_facts) >= 1

    def test_detect_raw_networking_and_netty(self, tmp_path: Path):
        code = """package com.example.net;
import java.net.ServerSocket;
import io.netty.bootstrap.ServerBootstrap;
public class SocketServer {
    public void listen() throws Exception {
        ServerSocket s = new ServerSocket(8080);
        ServerBootstrap b = new ServerBootstrap();
    }
}
"""
        f = tmp_path / "SocketServer.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("ServerSocket" in s for s in subjects)
        assert any("ServerBootstrap" in s for s in subjects)

    def test_detect_android_client(self, tmp_path: Path):
        code = """package com.example.mobile;
import android.os.Bundle;
import android.app.Activity;
public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {}
}
"""
        f = tmp_path / "MainActivity.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        android_facts = [f for f in facts if any("client.android" in h for h in f.identifier_hints)]
        assert len(android_facts) >= 1

    def test_detect_web3_structural_evidence(self, tmp_path: Path):
        code = """package com.example.web3;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.http.HttpService;
import org.web3j.tx.FastRawTransactionManager;
public class EthService {
    public void init() {
        Web3j web3 = Web3j.build(new HttpService("https://rpc.example.com"));
        FastRawTransactionManager txMgr = new FastRawTransactionManager(web3, null);
    }
}
"""
        f = tmp_path / "EthService.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("Web3j" in s for s in subjects)
        assert any("Web3j.build" in s or "HttpService" in s for s in subjects)
        assert any("FastRawTransactionManager" in s for s in subjects)
        assert any(f.kind == EvidenceKind.IMPORT for f in facts)

    def test_evidence_provenance(self, tmp_path: Path):
        code = """package com.example;
import java.net.ServerSocket;
public class Server {
    public void start() throws Exception {
        ServerSocket s = new ServerSocket(9000);
    }
}
"""
        f = tmp_path / "Prov.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        server_facts = [f for f in facts if "ServerSocket" in f.subject]
        assert len(server_facts) >= 1
        fact = server_facts[0]
        assert fact.file_path == f
        assert fact.line_range[0] >= 1
        assert "ServerSocket" in fact.snippet
        assert fact.scope == "start"
        assert fact.language == "java"

    def test_aggregator_compatibility(self, tmp_path: Path):
        code = """package com.example;
import org.springframework.cache.annotation.Cacheable;
public class UserService {
    @Cacheable("users")
    public String getUser(String id) { return id; }
}
"""
        f = tmp_path / "Agg.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        aggregator = EvidenceAggregator()
        bundles = aggregator.aggregate(facts)
        assert isinstance(bundles, list)
        caching = [b for b in bundles if b.concept_id == "foundation.caching"]
        assert len(caching) >= 1


class TestJavaScannerRobustness:
    """Validate meaningless and misleading names."""

    def setup_method(self):
        self.scanner = JavaScanner()

    def test_meaningless_names_with_real_architecture(self, tmp_path: Path):
        code = """package com.x9;
import com.zaxxer.hikari.HikariConfig;
public class C1 {
    public void fn_z0() {
        HikariConfig c = new HikariConfig();
        c.setMaximumPoolSize(15);
    }
}
"""
        f = tmp_path / "C1.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("HikariConfig" in s or "maximumPoolSize" in s for s in subjects)

    def test_misleading_names_without_architecture(self, tmp_path: Path):
        code = """package com.fake;
public class PaymentService {
    public void retryPayment() {}
    public int circuitBreakerCounter() { return 0; }
}
"""
        f = tmp_path / "Fake.java"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)
        signals = self.scanner.scan_file(f)

        assert len([f for f in facts if "@Retryable" in f.subject]) == 0
        assert len([s for s in signals if s.concept_id == "foundation.retries" and s.kind == SignalKind.PRESENCE]) == 0


class TestJavaScannerRegistryAndEdgeCases:
    """Registry integration and edge cases."""

    def setup_method(self):
        self.scanner = JavaScanner()

    def test_registry_lookup(self):
        cfg = get_scanner("java")
        assert cfg is not None
        assert cfg.get("enabled") is True
        assert ".java" in cfg.get("extensions", [])
        assert ".kt" in cfg.get("extensions", [])

    def test_registry_extension_resolution(self):
        assert extension_to_scanner(".java") == "java"
        assert extension_to_scanner("kt") == "java"

    def test_registry_get_scanner_for_file(self, tmp_path: Path):
        f = tmp_path / "Service.kt"
        scanner = get_scanner_for_file(f)
        assert isinstance(scanner, JavaScanner)

    def test_empty_file_returns_empty(self, tmp_path: Path):
        f = tmp_path / "Empty.java"
        f.write_text("", encoding="utf-8")
        assert self.scanner.scan_file_evidence(f) == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        assert self.scanner.scan_file_evidence(tmp_path / "Ghost.java") == []

    def test_determinism(self, tmp_path: Path):
        code = "class A { @Retryable void f() {} }"
        f = tmp_path / "Det.java"
        f.write_text(code, encoding="utf-8")
        r1 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        r2 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        assert r1 == r2


class TestJavaScannerFixture:
    """Validate Java scanner on tests/fixtures/java_project/."""

    def setup_method(self):
        self.scanner = JavaScanner()
        self.fixture_dir = Path("tests/fixtures/java_project")

    def test_fixture_directory_exists(self):
        assert self.fixture_dir.exists()
        assert self.fixture_dir.is_dir()

    def test_fixture_file_discovery(self):
        discovered = self.scanner.discover_files(self.fixture_dir)
        names = {f.name for f in discovered}
        expected = {"Application.java", "OrderService.java", "OrderRepository.java", "DatabaseConfig.java", "PaymentListener.kt"}
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

        assert len(categories) >= 8
        assert "api.rest" in categories
        assert "foundation.circuit-breaker" in categories
        assert "foundation.retries" in categories
        assert "data.orm" in categories
        assert "foundation.connection-pooling" in categories
        assert "foundation.caching" in categories
        assert "foundation.message-queues" in categories
        assert "foundation.concurrency" in categories
        assert "foundation.logging" in categories
        assert "foundation.health-checks" in categories
