"""Tests for C/C++ scanner (Phase 4C) — protocol, evidence extraction, robustness, fixture."""

from __future__ import annotations

from pathlib import Path

from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import EvidenceKind, SignalKind
from sdat.scanners.base import LanguageScanner
from sdat.scanners.c_cpp_scanner import CCppScanner
from sdat.scanners.registry import (
    extension_to_scanner,
    get_scanner,
    get_scanner_for_file,
)


class TestCCppScannerProtocol:
    """Protocol conformance and file discovery tests."""

    def setup_method(self):
        self.scanner = CCppScanner()

    def test_protocol_conformance(self):
        assert isinstance(self.scanner, LanguageScanner)
        assert self.scanner.language_id == "c_cpp"
        for ext in (".c", ".h", ".cpp", ".hpp"):
            assert ext in self.scanner.file_extensions

    def test_discover_files_empty_dir(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path) == []

    def test_discover_files_finds_all_c_cpp_extensions(self, tmp_path: Path):
        (tmp_path / "main.c").write_text("int main() { return 0; }", encoding="utf-8")
        (tmp_path / "header.h").write_text("#pragma once", encoding="utf-8")
        (tmp_path / "app.cpp").write_text("int main() { return 0; }", encoding="utf-8")
        (tmp_path / "types.hpp").write_text("#pragma once", encoding="utf-8")
        (tmp_path / "tool.cc").write_text("void f() {}", encoding="utf-8")
        (tmp_path / "engine.cxx").write_text("void g() {}", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("readme", encoding="utf-8")

        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 6
        names = {f.name for f in files}
        assert names == {"main.c", "header.h", "app.cpp", "types.hpp", "tool.cc", "engine.cxx"}

    def test_discover_files_excludes_default_ignored_dirs(self, tmp_path: Path):
        (tmp_path / "main.c").write_text("int main() { return 0; }", encoding="utf-8")
        build = tmp_path / "build"
        build.mkdir()
        (build / "out.c").write_text("int x = 1;", encoding="utf-8")
        cmake = tmp_path / "CMakeFiles"
        cmake.mkdir()
        (cmake / "check.c").write_text("int y = 2;", encoding="utf-8")

        files = self.scanner.discover_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "main.c"

    def test_discover_files_nonexistent_root(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path / "ghost") == []


class TestCCppScannerEvidenceExtraction:
    """Validate extraction of typed EvidenceFacts across C/C++ systems patterns."""

    def setup_method(self):
        self.scanner = CCppScanner()

    def test_detect_socket_networking(self, tmp_path: Path):
        code = """#include <sys/socket.h>
int setup_server() {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    bind(fd, NULL, 0);
    listen(fd, 10);
    return fd;
}
"""
        f = tmp_path / "net.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        socket_facts = [f for f in facts if "socket" in f.subject or "bind" in f.subject or "listen" in f.subject]
        assert len(socket_facts) >= 2

    def test_detect_epoll_event_loop(self, tmp_path: Path):
        code = """#include <sys/epoll.h>
void loop(int sfd) {
    int epfd = epoll_create1(0);
    epoll_ctl(epfd, EPOLL_CTL_ADD, sfd, NULL);
    epoll_wait(epfd, NULL, 10, 100);
}
"""
        f = tmp_path / "loop.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        epoll_facts = [f for f in facts if "epoll" in f.subject]
        assert len(epoll_facts) >= 2

    def test_detect_pthread_concurrency(self, tmp_path: Path):
        code = """#include <pthread.h>
pthread_mutex_t lock;
void* worker(void* arg) {
    pthread_mutex_lock(&lock);
    pthread_mutex_unlock(&lock);
    return NULL;
}
void start() {
    pthread_t t;
    pthread_create(&t, NULL, worker, NULL);
    pthread_join(t, NULL);
}
"""
        f = tmp_path / "threads.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        concurrency_facts = [f for f in facts if f.kind == EvidenceKind.CONCURRENCY]
        assert len(concurrency_facts) >= 3

    def test_detect_cpp11_concurrency(self, tmp_path: Path):
        code = """#include <thread>
#include <mutex>
std::mutex mtx;
void work() {
    std::lock_guard<std::mutex> lock(mtx);
}
void run() {
    std::thread t(work);
    t.join();
}
"""
        f = tmp_path / "cpp_thread.cpp"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cpp_concurrency = [f for f in facts if f.kind == EvidenceKind.CONCURRENCY or "std::thread" in f.subject]
        assert len(cpp_concurrency) >= 2

    def test_detect_shared_memory_and_ipc(self, tmp_path: Path):
        code = """#include <sys/mman.h>
#include <fcntl.h>
#include <semaphore.h>
void setup_ipc() {
    int fd = shm_open("/shm_test", O_CREAT | O_RDWR, 0666);
    void *ptr = mmap(NULL, 1024, PROT_READ, MAP_SHARED, fd, 0);
    sem_t sem;
    sem_init(&sem, 1, 1);
}
"""
        f = tmp_path / "ipc.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        ipc_facts = [f for f in facts if "shm_open" in f.subject or "mmap" in f.subject or "sem_init" in f.subject]
        assert len(ipc_facts) >= 2

    def test_detect_fork_process_creation(self, tmp_path: Path):
        code = """#include <unistd.h>
void spawn_proc() {
    pid_t pid = fork();
    if (pid == 0) {
        char *args[] = {"/bin/ls", NULL};
        execve(args[0], args, NULL);
    }
}
"""
        f = tmp_path / "proc.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        proc_facts = [f for f in facts if "fork" in f.subject or "execve" in f.subject]
        assert len(proc_facts) >= 1

    def test_detect_socket_timeout_option(self, tmp_path: Path):
        code = """#include <sys/socket.h>
void set_timeout(int fd) {
    struct timeval tv = { .tv_sec = 5 };
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
}
"""
        f = tmp_path / "timeout.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        timeout_facts = [f for f in facts if "SO_RCVTIMEO" in f.subject or f.timeout_observed is True]
        assert len(timeout_facts) >= 1

    def test_detect_embedded_freertos_and_kernel(self, tmp_path: Path):
        code = """#include <FreeRTOS.h>
#include <task.h>
void app_main() {
    xTaskCreate(NULL, "task1", 2048, NULL, 5, NULL);
}
"""
        f = tmp_path / "embedded.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        rtos_facts = [f for f in facts if "xTaskCreate" in f.subject or "<FreeRTOS.h>" in f.snippet]
        assert len(rtos_facts) >= 1

    def test_detect_syslog_logging(self, tmp_path: Path):
        code = """#include <syslog.h>
void log_msg() {
    openlog("test", LOG_PID, LOG_USER);
    syslog(LOG_INFO, "server ready");
    closelog();
}
"""
        f = tmp_path / "log.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        log_facts = [f for f in facts if "syslog" in f.subject]
        assert len(log_facts) >= 1

    def test_detect_unsafe_buffer_weakness(self, tmp_path: Path):
        code = """#include <string.h>
void copy_data(char *dst, const char *src) {
    strcpy(dst, src);
}
"""
        f = tmp_path / "unsafe.c"
        f.write_text(code, encoding="utf-8")
        signals = self.scanner.scan_file(f)

        weaknesses = [s for s in signals if s.kind == SignalKind.WEAKNESS]
        assert any(w.concept_id == "security.buffer-overflow" for w in weaknesses)

    def test_detect_cli_tooling(self, tmp_path: Path):
        code = """#include <getopt.h>
int main(int argc, char **argv) {
    int opt = getopt_long(argc, argv, "h", 0, 0);
    return 0;
}
"""
        f = tmp_path / "cli.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        cli_facts = [f for f in facts if "getopt" in f.subject]
        assert len(cli_facts) >= 1

    def test_detect_graphics_and_multimedia(self, tmp_path: Path):
        code = """#include <GL/gl.h>
#include <GLFW/glfw3.h>
void render() {
    GLFWwindow* window = glfwCreateWindow(640, 480, "Demo", NULL, NULL);
}
"""
        f = tmp_path / "gfx.cpp"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("GLFW" in s or "glfwCreateWindow" in s for s in subjects)

    def test_detect_cryptography_and_ssl(self, tmp_path: Path):
        code = """#include <openssl/ssl.h>
void secure_connect(SSL *ssl) {
    SSL_connect(ssl);
}
"""
        f = tmp_path / "crypto.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("SSL_connect" in s or "openssl" in s for s in subjects)

    def test_evidence_provenance(self, tmp_path: Path):
        code = """#include <sys/socket.h>
void init_socket() {
    int s = socket(AF_INET, SOCK_STREAM, 0);
}
"""
        f = tmp_path / "prov.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        sock_facts = [f for f in facts if "socket" in f.subject]
        assert len(sock_facts) >= 1
        fact = sock_facts[0]
        assert fact.file_path == f
        assert fact.line_range[0] >= 1
        assert "socket" in fact.snippet
        assert fact.scope == "init_socket"
        assert fact.language == "c_cpp"

    def test_aggregator_compatibility(self, tmp_path: Path):
        code = """#include <stdlib.h>
char* get_cfg() {
    return getenv("DATABASE_URL");
}
"""
        f = tmp_path / "agg.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        aggregator = EvidenceAggregator()
        bundles = aggregator.aggregate(facts)
        assert isinstance(bundles, list)
        cfg_bundles = [b for b in bundles if b.concept_id == "foundation.config"]
        assert len(cfg_bundles) >= 1


class TestCCppScannerRobustness:
    """Validate meaningless and misleading names."""

    def setup_method(self):
        self.scanner = CCppScanner()

    def test_meaningless_names_with_real_architecture(self, tmp_path: Path):
        code = """#include <pthread.h>
void* fn_z0(void* p) { return p; }
void proc_x9() {
    pthread_t t1;
    pthread_create(&t1, NULL, fn_z0, NULL);
    pthread_join(t1, NULL);
}
"""
        f = tmp_path / "sub.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)

        subjects = {f.subject for f in facts}
        assert any("pthread_create" in s for s in subjects)

    def test_misleading_names_without_architecture(self, tmp_path: Path):
        code = """int retryPayment(int x) {
    return x + 1;
}
int circuitBreakerHandler(void) {
    return 0;
}
"""
        f = tmp_path / "misleading.c"
        f.write_text(code, encoding="utf-8")
        facts = self.scanner.scan_file_evidence(f)
        signals = self.scanner.scan_file(f)

        assert len([f for f in facts if "backoff" in f.subject.lower()]) == 0
        assert len([s for s in signals if s.concept_id == "foundation.retries" and s.kind == SignalKind.PRESENCE]) == 0


class TestCCppScannerRegistryAndEdgeCases:
    """Registry integration and defensive edge cases."""

    def setup_method(self):
        self.scanner = CCppScanner()

    def test_registry_lookup(self):
        cfg = get_scanner("c_cpp")
        assert cfg is not None
        assert cfg.get("enabled") is True
        assert ".c" in cfg.get("extensions", [])
        assert ".cpp" in cfg.get("extensions", [])

    def test_registry_extension_resolution(self):
        for ext in (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp"):
            assert extension_to_scanner(ext) == "c_cpp"

    def test_registry_get_scanner_for_file(self, tmp_path: Path):
        f = tmp_path / "test.cpp"
        scanner = get_scanner_for_file(f)
        assert isinstance(scanner, CCppScanner)

    def test_empty_file_returns_empty(self, tmp_path: Path):
        f = tmp_path / "empty.c"
        f.write_text("", encoding="utf-8")
        assert self.scanner.scan_file_evidence(f) == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        assert self.scanner.scan_file_evidence(tmp_path / "missing.c") == []

    def test_determinism(self, tmp_path: Path):
        code = "int run() { return socket(0, 0, 0); }\n"
        f = tmp_path / "det.c"
        f.write_text(code, encoding="utf-8")
        r1 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        r2 = [f.to_dict() for f in self.scanner.scan_file_evidence(f)]
        assert r1 == r2


class TestCCppScannerFixture:
    """Validate C/C++ scanner on tests/fixtures/c_cpp_project/."""

    def setup_method(self):
        self.scanner = CCppScanner()
        self.fixture_dir = Path("tests/fixtures/c_cpp_project")

    def test_fixture_directory_exists(self):
        assert self.fixture_dir.exists()
        assert self.fixture_dir.is_dir()

    def test_fixture_file_discovery(self):
        discovered = self.scanner.discover_files(self.fixture_dir)
        names = {f.name for f in discovered}
        expected = {"main.c", "config.h", "thread_pool.h", "thread_pool.c", "ipc_shm.c"}
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

        assert len(categories) >= 6
        assert "networking.socket" in categories
        assert "foundation.concurrency" in categories
        assert "architecture.ipc" in categories
        assert "resilience.timeout" in categories
        assert "foundation.logging" in categories
        assert "foundation.config" in categories
        assert "foundation.memory" in categories
