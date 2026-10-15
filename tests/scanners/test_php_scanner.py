"""Tests for PHP scanner (Phase 4D) — protocol, evidence extraction, robustness, fixture."""

from __future__ import annotations

from pathlib import Path

from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import EvidenceKind, SignalKind
from sdat.scanners.base import LanguageScanner
from sdat.scanners.php_scanner import PhpScanner
from sdat.scanners.registry import (
    extension_to_scanner,
    get_scanner,
    get_scanner_for_file,
)


class TestPhpScannerProtocol:
    """Protocol conformance and file discovery tests."""

    def setup_method(self):
        self.scanner = PhpScanner()

    def test_protocol_conformance(self):
        assert isinstance(self.scanner, LanguageScanner)
        assert self.scanner.language_id == "php"
        assert ".php" in self.scanner.file_extensions

    def test_discover_files_empty_dir(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path) == []

    def test_discover_files_finds_php(self, tmp_path: Path):
        (tmp_path / "index.php").write_text("<?php echo 'hi';", encoding="utf-8")
        (tmp_path / "routes.php").write_text("<?php return [];", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("notes", encoding="utf-8")
        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 2
        assert all(f.suffix == ".php" for f in files)

    def test_discover_files_excludes_vendor_and_storage(self, tmp_path: Path):
        (tmp_path / "index.php").write_text("<?php echo 'hi';", encoding="utf-8")
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "autoload.php").write_text("<?php", encoding="utf-8")
        storage = tmp_path / "storage"
        storage.mkdir()
        (storage / "framework.php").write_text("<?php", encoding="utf-8")

        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "index.php"

    def test_discover_files_nonexistent_root(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path / "ghost") == []


class TestPhpScannerEvidenceExtraction:
    """Validate extraction of typed EvidenceFacts across PHP patterns."""

    def setup_method(self):
        self.scanner = PhpScanner()

    def test_detect_laravel_routing(self, tmp_path: Path):
        code = """<?php
use Illuminate\\Support\\Facades\\Route;
Route::get('/users', [UserController::class, 'index']);
Route::post('/users', [UserController::class, 'store']);
"""
        f = tmp_path / "web.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        route_facts = [f for f in facts if "Route::" in f.subject]
        assert len(route_facts) >= 2

    def test_detect_eloquent_orm_and_db(self, tmp_path: Path):
        code = """<?php
namespace App\\Models;
use Illuminate\\Database\\Eloquent\\Model;
use Illuminate\\Support\\Facades\\DB;
class User extends Model {
    public static function createWithTx($data) {
        return DB::transaction(function() use ($data) {
            return static::create($data);
        });
    }
}
"""
        f = tmp_path / "User.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        orm_facts = [f for f in facts if "extends Model" in f.snippet or "DB::transaction" in f.subject]
        assert len(orm_facts) >= 1

    def test_detect_caching_remember(self, tmp_path: Path):
        code = """<?php
use Illuminate\\Support\\Facades\\Cache;
function getUser($id) {
    return Cache::remember('user:' . $id, 3600, function() use ($id) {
        return User::find($id);
    });
}
"""
        f = tmp_path / "cache.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cache_facts = [f for f in facts if "Cache::remember" in f.subject]
        assert len(cache_facts) >= 1
        assert any(f.ttl_observed is True for f in cache_facts)

    def test_detect_queue_should_queue(self, tmp_path: Path):
        code = """<?php
namespace App\\Jobs;
use Illuminate\\Contracts\\Queue\\ShouldQueue;
class SendEmailJob implements ShouldQueue {
    public function handle() {
        // send email
    }
}
"""
        f = tmp_path / "job.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        queue_facts = [f for f in facts if "implements ShouldQueue" in f.snippet]
        assert len(queue_facts) >= 1

    def test_detect_rate_limiting(self, tmp_path: Path):
        code = """<?php
use Illuminate\\Support\\Facades\\RateLimiter;
RateLimiter::for('api', function ($request) {
    return Limit::perMinute(60)->by($request->user()?->id ?: $request->ip());
});
"""
        f = tmp_path / "rate.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        rate_facts = [f for f in facts if "RateLimiter::for" in f.subject]
        assert len(rate_facts) >= 1

    def test_detect_logging(self, tmp_path: Path):
        code = """<?php
use Illuminate\\Support\\Facades\\Log;
Log::info("User logged in successfully");
"""
        f = tmp_path / "log.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        log_facts = [f for f in facts if "Log::info" in f.subject]
        assert len(log_facts) >= 1

    def test_detect_env_config(self, tmp_path: Path):
        code = """<?php
$host = env('DB_HOST', 'localhost');
$port = config('database.port');
"""
        f = tmp_path / "config.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        config_facts = [f for f in facts if f.kind == EvidenceKind.CONFIG_KEY]
        assert len(config_facts) >= 2

    def test_detect_cli_console_commands(self, tmp_path: Path):
        code = """<?php
namespace App\\Console\\Commands;
use Symfony\\Component\\Console\\Command\\Command;
class ProcessQueueCommand extends Command {
    protected $signature = 'queue:work';
}
"""
        f = tmp_path / "Command.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cli_facts = [f for f in facts if any("tooling.cli" in h for h in f.identifier_hints)]
        assert len(cli_facts) >= 2

    def test_detect_process_control_workers(self, tmp_path: Path):
        code = """<?php
function spawn_worker() {
    $pid = pcntl_fork();
    if ($pid == 0) {
        proc_open("worker", [], $pipes);
    }
}
"""
        f = tmp_path / "worker.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        worker_facts = [f for f in facts if "pcntl_fork" in f.subject or "proc_open" in f.subject]
        assert len(worker_facts) == 2

    def test_detect_http_client_and_scheduling(self, tmp_path: Path):
        code = """<?php
use GuzzleHttp\\Client;
function sync_services($schedule) {
    $client = new Client();
    $schedule->command('sync:run')->hourly();
}
"""
        f = tmp_path / "sync.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("GuzzleHttp\\Client" in s for s in subjects)
        assert any("$schedule->command" in s for s in subjects)

    def test_evidence_provenance(self, tmp_path: Path):
        code = """<?php
class CacheService {
    public function rememberUser($id) {
        return Cache::remember("user:{$id}", 3600, function() {});
    }
}
"""
        f = tmp_path / "prov.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cache_facts = [f for f in facts if "Cache::remember" in f.subject]
        assert len(cache_facts) >= 1
        fact = cache_facts[0]
        assert fact.file_path == f
        assert fact.line_range[0] >= 1
        assert "Cache::remember" in fact.snippet
        assert fact.scope == "rememberUser"
        assert fact.language == "php"

    def test_aggregator_compatibility(self, tmp_path: Path):
        code = """<?php
use Illuminate\\Support\\Facades\\Cache;
function cache_data() {
    Cache::remember('key', 300, function() { return 1; });
}
"""
        f = tmp_path / "agg.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        aggregator = EvidenceAggregator()
        bundles = aggregator.aggregate(facts)
        assert isinstance(bundles, list)
        caching = [b for b in bundles if b.concept_id == "foundation.caching"]
        assert len(caching) >= 1


class TestPhpScannerRobustness:
    """Validate meaningless and misleading names."""

    def setup_method(self):
        self.scanner = PhpScanner()

    def test_meaningless_names_with_real_architecture(self, tmp_path: Path):
        code = """<?php
use Illuminate\\Support\\Facades\\Cache;
function fn_x1($k, $v) {
    return Cache::remember($k, 60, function() use ($v) {
        return $v;
    });
}
"""
        f = tmp_path / "x1.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        assert any("Cache::remember" in f.subject for f in facts)

    def test_misleading_names_without_architecture(self, tmp_path: Path):
        code = """<?php
function retryPayment() {
    return true;
}
function circuitBreakerService() {
    return 1;
}
"""
        f = tmp_path / "misleading.php"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)
        signals = self.scanner.scan_file(f)

        assert len([f for f in facts if "retry" in f.subject.lower()]) == 0
        assert len([s for s in signals if s.concept_id == "foundation.retries" and s.kind == SignalKind.PRESENCE]) == 0


class TestPhpScannerRegistryAndEdgeCases:
    """Registry integration and edge cases."""

    def setup_method(self):
        self.scanner = PhpScanner()

    def test_registry_lookup(self):
        cfg = get_scanner("php")
        assert cfg is not None
        assert cfg.get("enabled") is True
        assert ".php" in cfg.get("extensions", [])

    def test_registry_extension_resolution(self):
        assert extension_to_scanner(".php") == "php"
        assert extension_to_scanner("php") == "php"

    def test_registry_get_scanner_for_file(self, tmp_path: Path):
        f = tmp_path / "app.php"
        scanner = get_scanner_for_file(f)
        assert isinstance(scanner, PhpScanner)

    def test_empty_file_returns_empty(self, tmp_path: Path):
        f = tmp_path / "empty.php"
        f.write_text("", encoding="utf-8")
        assert self.scanner.scan_file_evidence(f) == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        assert self.scanner.scan_file_evidence(tmp_path / "ghost.php") == []

    def test_determinism(self, tmp_path: Path):
        code = "<?php Log::info('det');"
        f = tmp_path / "det.php"
        f.write_text(code, encoding="utf-8")
        r1 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        r2 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        assert r1 == r2


class TestPhpScannerFixture:
    """Validate PHP scanner on tests/fixtures/php_project/."""

    def setup_method(self):
        self.scanner = PhpScanner()
        self.fixture_dir = Path("tests/fixtures/php_project")

    def test_fixture_directory_exists(self):
        assert self.fixture_dir.exists()
        assert self.fixture_dir.is_dir()

    def test_fixture_file_discovery(self):
        discovered = self.scanner.discover_files(self.fixture_dir)
        names = {f.name for f in discovered}
        expected = {"api.php", "OrderController.php", "Order.php", "ProcessPayment.php", "database.php"}
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

        assert len(categories) >= 7
        assert "api.rest" in categories
        assert "data.orm" in categories
        assert "foundation.caching" in categories
        assert "foundation.message-queues" in categories
        assert "foundation.rate-limiting" in categories
        assert "foundation.logging" in categories
        assert "foundation.config" in categories
        assert "foundation.health-checks" in categories
