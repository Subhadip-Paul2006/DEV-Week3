"""Comprehensive tests for the Phase 2 Python scanner implementation."""

from __future__ import annotations

from pathlib import Path

from sdat.models import Signal, SignalKind
from sdat.scanners.base import LanguageScanner
from sdat.scanners.python_scanner import PythonScanner
from sdat.scanners.registry import (
    extension_to_scanner,
    get_enabled_scanners,
    get_scanner,
    get_scanner_class,
    get_scanner_for_file,
    get_scanner_instance,
)


class TestPythonScannerProtocol:
    """Validate scanner protocol conformance and discovery."""

    def setup_method(self):
        self.scanner = PythonScanner()

    def test_protocol_conformance(self):
        assert isinstance(self.scanner, LanguageScanner)
        assert self.scanner.language_id == "python"
        assert ".py" in self.scanner.file_extensions

    def test_discover_files_empty_dir(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path) == []

    def test_discover_files_finds_py(self, tmp_path: Path):
        (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "utils.py").write_text("y = 2", encoding="utf-8")
        (tmp_path / "readme.md").write_text("# Docs", encoding="utf-8")
        found = self.scanner.discover_files(tmp_path)
        assert len(found) == 2
        assert all(f.suffix == ".py" for f in found)

    def test_discover_files_excludes_default_ignored_dirs(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("x = 1", encoding="utf-8")
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "lib.py").write_text("y = 2", encoding="utf-8")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hook.py").write_text("z = 3", encoding="utf-8")

        found = self.scanner.discover_files(tmp_path)
        assert len(found) == 1
        assert found[0].name == "app.py"

    def test_discover_files_nonexistent_root(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist"
        assert self.scanner.discover_files(missing) == []


class TestPythonScannerDetections:
    """Validate detection of system design concepts in realistic Python code."""

    def setup_method(self):
        self.scanner = PythonScanner()

    def _get_presence(self, signals: list[Signal], concept_id: str) -> list[Signal]:
        return [s for s in signals if s.concept_id == concept_id and s.kind == SignalKind.PRESENCE]

    def _get_weakness(self, signals: list[Signal], concept_id: str) -> list[Signal]:
        return [s for s in signals if s.concept_id == concept_id and s.kind == SignalKind.WEAKNESS]

    def test_fastapi_application_detection(self, tmp_path: Path):
        f = tmp_path / "app.py"
        f.write_text(
            "from fastapi import FastAPI, APIRouter\n"
            "app = FastAPI(title='Service', openapi_url='/api/v1/openapi.json')\n"
            "router = APIRouter()\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        openapi_sigs = self._get_presence(signals, "foundation.openapi")
        client_server_sigs = self._get_presence(signals, "foundation.client-server")
        assert len(openapi_sigs) >= 1
        assert len(client_server_sigs) >= 1
        assert "FastAPI" in openapi_sigs[0].evidence

    def test_http_request_external_service(self, tmp_path: Path):
        f = tmp_path / "client.py"
        f.write_text(
            "import httpx\n"
            "async def fetch_user(user_id: str):\n"
            "    async with httpx.AsyncClient() as client:\n"
            "        return await client.get(f'https://users.service.internal/{user_id}')\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "foundation.client-server")
        assert len(sigs) >= 1
        assert "httpx" in sigs[0].evidence

    def test_retry_logic_detection(self, tmp_path: Path):
        f = tmp_path / "tasks.py"
        f.write_text(
            "from tenacity import retry, stop_after_attempt, wait_exponential\n"
            "@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))\n"
            "def push_notification():\n"
            "    pass\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "resilience.retries")
        assert len(sigs) >= 1
        assert any("tenacity" in s.evidence or "retry" in s.evidence for s in sigs)

    def test_timeout_handling_detection(self, tmp_path: Path):
        f = tmp_path / "network.py"
        f.write_text(
            "import httpx\n"
            "client = httpx.Client(timeout=10.0)\n"
            "def call_gateway():\n"
            "    return client.get('https://gateway.example.com', timeout=5.0)\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "resilience.timeouts")
        assert len(sigs) >= 1
        assert "timeout=" in sigs[0].evidence

    def test_circuit_breaker_detection(self, tmp_path: Path):
        f = tmp_path / "resilience.py"
        f.write_text(
            "import pybreaker\n"
            "db_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)\n"
            "@db_breaker\n"
            "def query_database():\n"
            "    pass\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "resilience.circuit-breaker")
        assert len(sigs) >= 1
        assert any("pybreaker" in s.evidence or "CircuitBreaker" in s.evidence for s in sigs)

    def test_caching_detection(self, tmp_path: Path):
        f = tmp_path / "cache.py"
        f.write_text(
            "import redis\n"
            "from functools import lru_cache\n"
            "redis_client = redis.from_url('redis://localhost:6379/0')\n"
            "@lru_cache(maxsize=128)\n"
            "def get_expensive_computation(x: int) -> int:\n"
            "    return x * 2\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "foundation.caching")
        assert len(sigs) >= 1
        assert any("redis" in s.evidence or "lru_cache" in s.evidence for s in sigs)

    def test_database_orm_detection(self, tmp_path: Path):
        f = tmp_path / "models.py"
        f.write_text(
            "from sqlalchemy import Column, Integer, String\n"
            "from sqlalchemy.orm import declarative_base, Session\n"
            "Base = declarative_base()\n"
            "class User(Base):\n"
            "    __tablename__ = 'users'\n"
            "    id = Column(Integer, primary_key=True)\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "data.orm")
        assert len(sigs) >= 1
        assert "sqlalchemy" in sigs[0].evidence.lower() or "declarative_base" in sigs[0].evidence

    def test_database_migrations_detection(self, tmp_path: Path):
        f = tmp_path / "001_initial.py"
        f.write_text(
            "from alembic import op\n"
            "import sqlalchemy as sa\n"
            "def upgrade() -> None:\n"
            "    op.create_table('accounts', sa.Column('id', sa.Integer))\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "data.migrations")
        assert len(sigs) >= 1
        assert "alembic" in sigs[0].evidence

    def test_connection_pooling_detection(self, tmp_path: Path):
        f = tmp_path / "database.py"
        f.write_text(
            "from sqlalchemy import create_engine\n"
            "engine = create_engine('postgresql://user:pass@localhost/db', pool_size=20, max_overflow=10)\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "performance.connection-pool")
        assert len(sigs) >= 1
        assert any("pool_size" in s.evidence or "create_engine" in s.evidence for s in sigs)

    def test_logging_detection(self, tmp_path: Path):
        f = tmp_path / "logger.py"
        f.write_text(
            "import logging\n"
            "logger = logging.getLogger('my_app')\n"
            "logger.info('System initialized')\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "foundation.logging")
        assert len(sigs) >= 1
        assert "import logging" in sigs[0].evidence

    def test_metrics_detection(self, tmp_path: Path):
        f = tmp_path / "metrics.py"
        f.write_text(
            "from prometheus_client import Counter, Histogram\n"
            "REQUESTS_TOTAL = Counter('requests_total', 'HTTP total requests')\n"
            "LATENCY = Histogram('request_latency_seconds', 'Request latency')\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "observability.metrics")
        assert len(sigs) >= 1
        assert "prometheus" in sigs[0].evidence.lower() or "Counter" in sigs[0].evidence

    def test_distributed_tracing_detection(self, tmp_path: Path):
        f = tmp_path / "telemetry.py"
        f.write_text(
            "from opentelemetry import trace\n"
            "tracer = trace.get_tracer(__name__)\n"
            "with tracer.start_as_current_span('checkout_op'):\n"
            "    pass\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "observability.tracing")
        assert len(sigs) >= 1
        assert "opentelemetry" in sigs[0].evidence or "trace.get_tracer" in sigs[0].evidence

    def test_message_broker_detection(self, tmp_path: Path):
        f = tmp_path / "queue_worker.py"
        f.write_text(
            "import pika\n"
            "params = pika.ConnectionParameters('localhost')\n"
            "connection = pika.BlockingConnection(params)\n"
            "channel = connection.channel()\n"
            "channel.queue_declare(queue='task_queue', durable=True)\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "streaming.message-broker")
        assert len(sigs) >= 1
        assert "pika" in sigs[0].evidence

    def test_websockets_detection(self, tmp_path: Path):
        f = tmp_path / "ws.py"
        f.write_text(
            "from fastapi import WebSocket, WebSocketDisconnect\n"
            "async def websocket_handler(websocket: WebSocket):\n"
            "    await websocket.accept()\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "streaming.websockets")
        assert len(sigs) >= 1
        assert "WebSocket" in sigs[0].evidence

    def test_authentication_detection(self, tmp_path: Path):
        f = tmp_path / "auth.py"
        f.write_text(
            "import jwt\n"
            "def create_token(user_id: int) -> str:\n"
            "    return jwt.encode({'sub': str(user_id)}, 'secret_key', algorithm='HS256')\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "foundation.auth")
        assert len(sigs) >= 1
        assert "jwt" in sigs[0].evidence.lower()

    def test_secrets_and_config_detection(self, tmp_path: Path):
        f = tmp_path / "config.py"
        f.write_text(
            "from dotenv import load_dotenv\n"
            "import os\n"
            "load_dotenv()\n"
            "DATABASE_URL = os.getenv('DATABASE_URL')\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "foundation.config")
        assert len(sigs) >= 1
        assert "dotenv" in sigs[0].evidence or "os.getenv" in sigs[0].evidence

    def test_secrets_manager_presence_detection(self, tmp_path: Path):
        f = tmp_path / "vault.py"
        f.write_text(
            "import hvac\n"
            "client = hvac.Client(url='https://vault.internal:8200')\n"
            "secret = client.secrets.kv.v2.read_secret_version(path='my-secret')\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "security.secrets-management")
        assert len(sigs) >= 1
        assert "hvac" in sigs[0].evidence.lower()

    def test_cors_middleware_detection(self, tmp_path: Path):
        f = tmp_path / "cors.py"
        f.write_text(
            "from fastapi.middleware.cors import CORSMiddleware\n"
            "app.add_middleware(CORSMiddleware, allow_origins=['https://app.example.com'])\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "security.cors")
        assert len(sigs) >= 1
        assert "CORSMiddleware" in sigs[0].evidence

    def test_healthchecks_detection(self, tmp_path: Path):
        f = tmp_path / "routes.py"
        f.write_text(
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/health')\n"
            "def health():\n"
            "    return {'status': 'healthy'}\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        sigs = self._get_presence(signals, "deployment.healthchecks")
        assert len(sigs) >= 1
        assert "/health" in sigs[0].evidence

    def test_misconfiguration_hardcoded_secret(self, tmp_path: Path):
        f = tmp_path / "bad_auth.py"
        f.write_text(
            "API_KEY = 'sk_live_1234567890abcdef123456'\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        weaknesses = self._get_weakness(signals, "security.secrets-management")
        assert len(weaknesses) >= 1
        assert "[WEAKNESS]" in weaknesses[0].evidence

    def test_misconfiguration_bare_except(self, tmp_path: Path):
        f = tmp_path / "bad_error.py"
        f.write_text(
            "try:\n"
            "    do_something()\n"
            "except:\n"
            "    pass\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(f)
        weaknesses = self._get_weakness(signals, "foundation.error-handling")
        assert len(weaknesses) >= 1
        assert "[WEAKNESS]" in weaknesses[0].evidence


class TestScannerRegistryIntegration:
    """Validate scanner registry integration for Python."""

    def test_registry_lookup_returns_python_scanner(self):
        config = get_scanner("python")
        assert config is not None
        assert config.get("enabled") is True
        assert ".py" in config.get("extensions", [])

    def test_registry_get_scanner_class(self):
        cls = get_scanner_class("python")
        assert cls is PythonScanner

    def test_registry_get_scanner_instance(self):
        inst = get_scanner_instance("python")
        assert isinstance(inst, PythonScanner)
        assert isinstance(inst, LanguageScanner)

    def test_registry_extension_mapping(self):
        assert extension_to_scanner(".py") == "python"
        assert extension_to_scanner("py") == "python"
        assert extension_to_scanner(".PY") == "python"
        assert extension_to_scanner(".unknown_ext") is None

    def test_registry_get_scanner_for_file(self, tmp_path: Path):
        py_file = tmp_path / "service.py"
        py_file.write_text("import redis\n", encoding="utf-8")
        scanner = get_scanner_for_file(py_file)
        assert isinstance(scanner, PythonScanner)
        signals = scanner.scan_file(py_file)
        assert any(s.concept_id == "foundation.caching" and s.kind == SignalKind.PRESENCE for s in signals)

    def test_registry_enabled_scanners_list(self):
        enabled = get_enabled_scanners()
        assert any(s.get("module") == "sdat.scanners.python_scanner" for s in enabled)


class TestPythonScannerErrorHandling:
    """Validate robust error handling for edge cases."""

    def setup_method(self):
        self.scanner = PythonScanner()

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        missing_file = tmp_path / "missing.py"
        assert self.scanner.scan_file(missing_file) == []

    def test_directory_path_passed_to_scan_file_returns_empty(self, tmp_path: Path):
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        assert self.scanner.scan_file(sub_dir) == []

    def test_empty_file_returns_signals_without_crashing(self, tmp_path: Path):
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("", encoding="utf-8")
        signals = self.scanner.scan_file(empty_file)
        # Should gracefully return absence signals, no exception
        assert isinstance(signals, list)
        assert all(s.kind == SignalKind.ABSENCE for s in signals)

    def test_invalid_python_syntax_does_not_crash(self, tmp_path: Path):
        syntax_err_file = tmp_path / "invalid.py"
        syntax_err_file.write_text(
            "def broken_syntax(:\n"
            "    import redis\n"
            "    ??? << >> !@#$\n",
            encoding="utf-8",
        )
        signals = self.scanner.scan_file(syntax_err_file)
        # Regex scanner still identifies patterns without choking on syntax errors
        caching_sigs = [s for s in signals if s.concept_id == "foundation.caching" and s.kind == SignalKind.PRESENCE]
        assert len(caching_sigs) >= 1

    def test_scan_project_empty_dir_returns_empty(self, tmp_path: Path):
        empty_dir = tmp_path / "empty_proj"
        empty_dir.mkdir()
        results = self.scanner.scan_project(empty_dir)
        assert results == []


class TestPhase2ExitCondition:
    """Validate the Phase 2 exit condition against representative 500-line FastAPI project."""

    FIXTURE_DIR = Path("tests/fixtures/fastapi_project")

    def test_fastapi_fixture_exists_and_line_count(self):
        assert self.FIXTURE_DIR.exists()
        py_files = list(self.FIXTURE_DIR.glob("*.py"))
        assert len(py_files) >= 5
        total_loc = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in py_files)
        # Verify representative ~500 LOC
        assert 450 <= total_loc <= 650

    def test_fastapi_fixture_exit_condition_at_least_15_concepts(self):
        # 1. Use the official registry path
        scanner = get_scanner_instance("python")
        assert scanner is not None

        # 2. Discover files
        discovered = scanner.discover_files(self.FIXTURE_DIR)
        assert len(discovered) >= 5

        # 3. Extract signals
        signals = scanner.extract_signals(discovered)
        assert len(signals) > 0

        # 4. Check presence signals and unique concept coverage
        presence_signals = [s for s in signals if s.kind == SignalKind.PRESENCE]
        unique_presence_concepts = set(s.concept_id for s in presence_signals)

        # Exit condition: ≥15 concept signals
        assert len(unique_presence_concepts) >= 15
        assert len(presence_signals) >= 15

        # 5. Verify canonical schema fields for every emitted signal
        for sig in signals:
            assert isinstance(sig.concept_id, str) and len(sig.concept_id) > 0
            assert isinstance(sig.kind, SignalKind)
            assert isinstance(sig.file_path, Path)
            assert sig.line_range is None or (
                isinstance(sig.line_range, tuple)
                and len(sig.line_range) == 2
                and sig.line_range[0] <= sig.line_range[1]
            )
            assert isinstance(sig.evidence, str) and len(sig.evidence) > 0
            assert 0.0 <= sig.confidence <= 1.0
            assert isinstance(sig.metadata, dict)

    def test_deterministic_output_across_repeated_runs(self):
        scanner = get_scanner_instance("python")
        discovered = scanner.discover_files(self.FIXTURE_DIR)

        run1 = scanner.extract_signals(discovered)
        run2 = scanner.extract_signals(discovered)

        assert len(run1) == len(run2)
        for s1, s2 in zip(run1, run2):
            assert s1.concept_id == s2.concept_id
            assert s1.kind == s2.kind
            assert s1.file_path == s2.file_path
            assert s1.line_range == s2.line_range
            assert s1.evidence == s2.evidence
            assert s1.confidence == s2.confidence

    def test_scan_project_conforms_to_file_signals(self):
        scanner = PythonScanner()
        file_signals_list = scanner.scan_project(self.FIXTURE_DIR)
        assert len(file_signals_list) == len(list(self.FIXTURE_DIR.glob("*.py")))
        for fs in file_signals_list:
            assert Path(fs.file).exists()
            assert len(fs.signals) > 0

