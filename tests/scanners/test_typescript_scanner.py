"""Comprehensive tests for the Phase 3 TypeScript / Node.js scanner implementation."""

from __future__ import annotations

from pathlib import Path

from sdat.models import Signal, SignalKind
from sdat.scanners.base import LanguageScanner
from sdat.scanners.registry import (
    extension_to_scanner,
    get_enabled_scanners,
    get_scanner,
    get_scanner_class,
    get_scanner_for_file,
    get_scanner_instance,
)
from sdat.scanners.typescript_scanner import TypeScriptScanner


class TestTypeScriptScannerProtocol:
    """Validate scanner protocol conformance and file discovery."""

    def setup_method(self):
        self.scanner = TypeScriptScanner()

    def test_protocol_conformance(self):
        assert isinstance(self.scanner, LanguageScanner)
        assert self.scanner.language_id == "typescript"
        for ext in (".ts", ".tsx", ".js", ".jsx"):
            assert ext in self.scanner.file_extensions

    def test_discover_files_empty_dir(self, tmp_path: Path):
        assert self.scanner.discover_files(tmp_path) == []

    def test_discover_files_finds_all_supported_extensions(self, tmp_path: Path):
        (tmp_path / "server.ts").write_text("const x: number = 1;", encoding="utf-8")
        (tmp_path / "App.tsx").write_text("export const App = () => null;", encoding="utf-8")
        (tmp_path / "legacy.js").write_text("var y = 2;", encoding="utf-8")
        (tmp_path / "Button.jsx").write_text("export function Button() { return null; }", encoding="utf-8")
        (tmp_path / "notes.md").write_text("# Notes", encoding="utf-8")
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        (tmp_path / "script.py").write_text("x = 1", encoding="utf-8")

        found = self.scanner.discover_files(tmp_path)
        assert len(found) == 4
        names = {f.name for f in found}
        assert names == {"server.ts", "App.tsx", "legacy.js", "Button.jsx"}

    def test_discover_files_excludes_default_ignored_dirs(self, tmp_path: Path):
        (tmp_path / "index.ts").write_text("console.log('hi');", encoding="utf-8")

        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "pkg.js").write_text("module.exports = {};", encoding="utf-8")

        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "bundle.js").write_text("var a=1;", encoding="utf-8")

        next_dir = tmp_path / ".next"
        next_dir.mkdir()
        (next_dir / "server.js").write_text("console.log();", encoding="utf-8")

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "out.js").write_text("console.log();", encoding="utf-8")

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hook.js").write_text("process.exit(0);", encoding="utf-8")

        found = self.scanner.discover_files(tmp_path)
        assert len(found) == 1
        assert found[0].name == "index.ts"

    def test_discover_files_nonexistent_root(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist"
        assert self.scanner.discover_files(missing) == []

    def test_discover_files_file_passed_as_root(self, tmp_path: Path):
        single_file = tmp_path / "single.ts"
        single_file.write_text("const x = 1;", encoding="utf-8")
        assert self.scanner.discover_files(single_file) == []


class TestTypeScriptScannerDetections:
    """Validate detection of system design concepts in TypeScript/JavaScript code."""

    def setup_method(self):
        self.scanner = TypeScriptScanner()

    def _scan_snippet(self, tmp_path: Path, filename: str, code: str) -> list[Signal]:
        f = tmp_path / filename
        f.write_text(code, encoding="utf-8")
        return self.scanner.scan_file(f)

    def _get_presence_concepts(self, signals: list[Signal]) -> set[str]:
        return {s.concept_id for s in signals if s.kind == SignalKind.PRESENCE}

    def test_detect_express_client_server(self, tmp_path: Path):
        code = """
        import express from 'express';
        const app = express();
        app.get('/users', (req, res) => res.json([]));
        """
        sigs = self._scan_snippet(tmp_path, "server.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.client-server" in concepts

    def test_detect_fastify(self, tmp_path: Path):
        code = """
        import Fastify from 'fastify';
        const fastify = Fastify({ logger: true });
        fastify.get('/ping', async (request, reply) => 'pong');
        """
        sigs = self._scan_snippet(tmp_path, "app.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.client-server" in concepts

    def test_detect_nestjs(self, tmp_path: Path):
        code = """
        import { Controller, Get } from '@nestjs/common';
        @Controller('items')
        export class ItemsController {
          @Get()
          findAll() { return []; }
        }
        """
        sigs = self._scan_snippet(tmp_path, "items.controller.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.client-server" in concepts

    def test_detect_external_http_client_axios(self, tmp_path: Path):
        code = """
        import axios from 'axios';
        const client = axios.create({ baseURL: 'https://api.service.internal' });
        const res = await client.post('/data', { id: 123 });
        """
        sigs = self._scan_snippet(tmp_path, "client.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.client-server" in concepts

    def test_detect_caching_redis_ioredis(self, tmp_path: Path):
        code = """
        import Redis from 'ioredis';
        const redis = new Redis(process.env.REDIS_URL);
        await redis.set('cache:key', JSON.stringify(data), 'EX', 3600);
        """
        sigs = self._scan_snippet(tmp_path, "cache.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.caching" in concepts

    def test_detect_caching_react_query(self, tmp_path: Path):
        code = """
        import { useQuery } from '@tanstack/react-query';
        export function useUser(id: string) {
          return useQuery({ queryKey: ['user', id], queryFn: () => fetchUser(id) });
        }
        """
        sigs = self._scan_snippet(tmp_path, "useUser.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.caching" in concepts

    def test_detect_caching_nextjs_revalidate(self, tmp_path: Path):
        code = """
        import { revalidatePath, revalidateTag } from 'next/cache';
        export async function updateAction() {
          revalidatePath('/dashboard');
        }
        """
        sigs = self._scan_snippet(tmp_path, "actions.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.caching" in concepts

    def test_detect_database_prisma(self, tmp_path: Path):
        code = """
        import { PrismaClient } from '@prisma/client';
        export const prisma = new PrismaClient();
        const users = await prisma.user.findMany();
        """
        sigs = self._scan_snippet(tmp_path, "db.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "data.orm" in concepts

    def test_detect_database_typeorm(self, tmp_path: Path):
        code = """
        import { Entity, PrimaryGeneratedColumn, Column } from 'typeorm';
        @Entity()
        export class User {
          @PrimaryGeneratedColumn()
          id: number;
        }
        """
        sigs = self._scan_snippet(tmp_path, "User.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "data.orm" in concepts

    def test_detect_database_mongoose(self, tmp_path: Path):
        code = """
        import mongoose, { Schema } from 'mongoose';
        const userSchema = new Schema({ name: String });
        export const UserModel = mongoose.model('User', userSchema);
        """
        sigs = self._scan_snippet(tmp_path, "user.model.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "data.orm" in concepts

    def test_detect_connection_pooling(self, tmp_path: Path):
        code = """
        import { Pool } from 'pg';
        const pool = new Pool({
          max: 20,
          idleTimeoutMillis: 30000,
          connectionTimeoutMillis: 2000,
        });
        """
        sigs = self._scan_snippet(tmp_path, "pool.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "performance.connection-pool" in concepts

    def test_detect_logging_winston(self, tmp_path: Path):
        code = """
        import winston from 'winston';
        const logger = winston.createLogger({
          level: 'info',
          transports: [new winston.transports.Console()],
        });
        """
        sigs = self._scan_snippet(tmp_path, "logger.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.logging" in concepts

    def test_detect_logging_pino(self, tmp_path: Path):
        code = """
        import pino from 'pino';
        export const logger = pino({ level: 'debug' });
        """
        sigs = self._scan_snippet(tmp_path, "pinoLogger.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.logging" in concepts

    def test_detect_observability_metrics(self, tmp_path: Path):
        code = """
        import { Counter, Registry } from 'prom-client';
        const counter = new Counter({ name: 'http_requests_total', help: 'total requests' });
        """
        sigs = self._scan_snippet(tmp_path, "metrics.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "observability.metrics" in concepts

    def test_detect_observability_tracing(self, tmp_path: Path):
        code = """
        import { trace } from '@opentelemetry/api';
        const tracer = trace.getTracer('payment-service');
        const span = tracer.startSpan('process-charge');
        """
        sigs = self._scan_snippet(tmp_path, "tracer.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "observability.tracing" in concepts

    def test_detect_circuit_breaker(self, tmp_path: Path):
        code = """
        import CircuitBreaker from 'opossum';
        const breaker = new CircuitBreaker(externalCall, { timeout: 3000, errorThresholdPercentage: 50 });
        breaker.fallback(() => ({ fallback: true }));
        """
        sigs = self._scan_snippet(tmp_path, "breaker.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "resilience.circuit-breaker" in concepts

    def test_detect_retry_pattern(self, tmp_path: Path):
        code = """
        import retry from 'async-retry';
        await retry(async (bail) => {
          return await sendReq();
        }, { retries: 5 });
        """
        sigs = self._scan_snippet(tmp_path, "retry.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "resilience.retries" in concepts

    def test_detect_timeouts(self, tmp_path: Path):
        code = """
        const client = axios.create({ timeout: 5000 });
        const signal = AbortSignal.timeout(3000);
        """
        sigs = self._scan_snippet(tmp_path, "timeouts.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "resilience.timeouts" in concepts

    def test_detect_validation_zod(self, tmp_path: Path):
        code = """
        import { z } from 'zod';
        const userSchema = z.object({
          id: z.string().uuid(),
          email: z.string().email(),
        });
        """
        sigs = self._scan_snippet(tmp_path, "schema.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.validation" in concepts

    def test_detect_validation_class_validator(self, tmp_path: Path):
        code = """
        import { IsString, IsEmail, IsNotEmpty } from 'class-validator';
        export class CreateUserDto {
          @IsString()
          @IsNotEmpty()
          name: string;
        }
        """
        sigs = self._scan_snippet(tmp_path, "dto.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.validation" in concepts

    def test_detect_auth_jwt(self, tmp_path: Path):
        code = """
        import jwt from 'jsonwebtoken';
        const token = jwt.sign({ sub: userId }, secret, { expiresIn: '1h' });
        const decoded = jwt.verify(token, secret);
        """
        sigs = self._scan_snippet(tmp_path, "auth.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.auth" in concepts

    def test_detect_auth_bcrypt(self, tmp_path: Path):
        code = """
        import bcrypt from 'bcrypt';
        const hash = await bcrypt.hash(password, 12);
        const match = await bcrypt.compare(password, hash);
        """
        sigs = self._scan_snippet(tmp_path, "passwords.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.auth" in concepts

    def test_detect_authorization_casl(self, tmp_path: Path):
        code = """
        import { AbilityBuilder, createMongoAbility } from '@casl/ability';
        const { can, cannot, build } = new AbilityBuilder(createMongoAbility);
        can('read', 'Article');
        """
        sigs = self._scan_snippet(tmp_path, "ability.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.authorization" in concepts

    def test_detect_cors(self, tmp_path: Path):
        code = """
        import cors from 'cors';
        app.use(cors({ origin: 'https://trusted.example.com', credentials: true }));
        """
        sigs = self._scan_snippet(tmp_path, "cors.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "security.cors" in concepts

    def test_detect_security_headers_helmet(self, tmp_path: Path):
        code = """
        import helmet from 'helmet';
        app.use(helmet());
        """
        sigs = self._scan_snippet(tmp_path, "security.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "security.headers" in concepts

    def test_detect_rate_limiting(self, tmp_path: Path):
        code = """
        import rateLimit from 'express-rate-limit';
        const limiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 100 });
        app.use('/api', limiter);
        """
        sigs = self._scan_snippet(tmp_path, "limiter.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.rate-limiting" in concepts

    def test_detect_config_dotenv(self, tmp_path: Path):
        code = """
        import dotenv from 'dotenv';
        dotenv.config();
        export const PORT = process.env.PORT || 3000;
        """
        sigs = self._scan_snippet(tmp_path, "config.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.config" in concepts

    def test_detect_message_broker_bullmq(self, tmp_path: Path):
        code = """
        import { Queue, Worker } from 'bullmq';
        export const emailsQueue = new Queue('emails');
        const worker = new Worker('emails', async (job) => {
          await sendEmail(job.data);
        });
        """
        sigs = self._scan_snippet(tmp_path, "worker.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "streaming.message-broker" in concepts

    def test_detect_websockets_ws(self, tmp_path: Path):
        code = """
        import { WebSocketServer } from 'ws';
        const wss = new WebSocketServer({ port: 8080 });
        wss.on('connection', (ws) => ws.send('welcome'));
        """
        sigs = self._scan_snippet(tmp_path, "wsServer.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "streaming.websockets" in concepts

    def test_detect_healthchecks(self, tmp_path: Path):
        code = """
        app.get('/health', (req, res) => res.json({ status: 'healthy' }));
        app.get('/ready', (req, res) => res.status(200).send('ready'));
        """
        sigs = self._scan_snippet(tmp_path, "health.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "deployment.healthchecks" in concepts

    def test_detect_react_heuristic(self, tmp_path: Path):
        code = """
        import React, { useState, useEffect } from 'react';
        export const Counter: React.FC = () => {
          const [count, setCount] = useState(0);
          return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
        };
        """
        sigs = self._scan_snippet(tmp_path, "Counter.tsx", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.client-server" in concepts
        # Verify metadata identifies react framework
        presence_sigs = [s for s in sigs if s.kind == SignalKind.PRESENCE]
        assert any(s.metadata.get("framework") == "react" for s in presence_sigs)

    def test_detect_nextjs_heuristic(self, tmp_path: Path):
        code = """
        import { NextRequest, NextResponse } from 'next/server';
        export async function GET(request: NextRequest) {
          return NextResponse.json({ ok: true });
        }
        """
        sigs = self._scan_snippet(tmp_path, "route.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "foundation.client-server" in concepts
        presence_sigs = [s for s in sigs if s.kind == SignalKind.PRESENCE]
        assert any(s.metadata.get("framework") == "nextjs" for s in presence_sigs)

    def test_detect_graphql(self, tmp_path: Path):
        code = """
        import { ApolloServer } from '@apollo/server';
        const server = new ApolloServer({ typeDefs, resolvers });
        """
        sigs = self._scan_snippet(tmp_path, "graphql.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "integration.graphql" in concepts

    def test_detect_pagination(self, tmp_path: Path):
        code = """
        const page = parseInt(req.query.page || '1');
        const limit = parseInt(req.query.limit || '20');
        const offset = (page - 1) * limit;
        """
        sigs = self._scan_snippet(tmp_path, "list.ts", code)
        concepts = self._get_presence_concepts(sigs)
        assert "performance.pagination" in concepts

    def test_detect_accessibility(self, tmp_path: Path):
        code = """
        export function Modal() {
          return <div role="dialog" aria-label="Settings Dialog" aria-hidden="false"></div>;
        }
        """
        sigs = self._scan_snippet(tmp_path, "Modal.tsx", code)
        concepts = self._get_presence_concepts(sigs)
        assert "ux.accessibility" in concepts


class TestTypeScriptScannerMisconfigurations:
    """Validate detection of architectural misconfigurations / smells."""

    def setup_method(self):
        self.scanner = TypeScriptScanner()

    def test_detect_empty_catch_block(self, tmp_path: Path):
        code = """
        try {
          doRiskyOperation();
        } catch (err) {}
        """
        f = tmp_path / "bad_error.ts"
        f.write_text(code, encoding="utf-8")
        sigs = self.scanner.scan_file(f)
        weaknesses = [s for s in sigs if s.kind == SignalKind.WEAKNESS]
        assert any(s.concept_id == "foundation.error-handling" for s in weaknesses)

    def test_detect_wildcard_cors(self, tmp_path: Path):
        code = """
        app.use(cors({ origin: "*" }));
        """
        f = tmp_path / "bad_cors.ts"
        f.write_text(code, encoding="utf-8")
        sigs = self.scanner.scan_file(f)
        weaknesses = [s for s in sigs if s.kind == SignalKind.WEAKNESS]
        assert any(s.concept_id == "security.cors" for s in weaknesses)

    def test_detect_hardcoded_secret(self, tmp_path: Path):
        code = """
        const apiKey = "sk_live_99887766554433221100";
        """
        f = tmp_path / "bad_secret.ts"
        f.write_text(code, encoding="utf-8")
        sigs = self.scanner.scan_file(f)
        weaknesses = [s for s in sigs if s.kind == SignalKind.WEAKNESS]
        assert any(s.concept_id == "security.secrets-management" for s in weaknesses)


class TestTypeScriptScannerEdgeCases:
    """Validate edge cases, negative examples, and defensive handling."""

    def setup_method(self):
        self.scanner = TypeScriptScanner()

    def test_plain_typescript_no_concepts(self, tmp_path: Path):
        code = """
        export function add(a: number, b: number): number {
          return a + b;
        }
        export function multiply(a: number, b: number): number {
          return a * b;
        }
        """
        f = tmp_path / "math.ts"
        f.write_text(code, encoding="utf-8")
        sigs = self.scanner.scan_file(f)
        presence = [s for s in sigs if s.kind == SignalKind.PRESENCE]
        assert len(presence) == 0

    def test_plain_javascript_no_concepts(self, tmp_path: Path):
        code = """
        function calculateArea(width, height) {
          return width * height;
        }
        module.exports = { calculateArea };
        """
        f = tmp_path / "geometry.js"
        f.write_text(code, encoding="utf-8")
        sigs = self.scanner.scan_file(f)
        presence = [s for s in sigs if s.kind == SignalKind.PRESENCE]
        assert len(presence) == 0

    def test_empty_file_returns_absence_signals_without_crashing(self, tmp_path: Path):
        f = tmp_path / "empty.ts"
        f.write_text("", encoding="utf-8")
        sigs = self.scanner.scan_file(f)
        assert len(sigs) > 0
        assert all(s.kind == SignalKind.ABSENCE for s in sigs)

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.ts"
        sigs = self.scanner.scan_file(missing)
        assert sigs == []

    def test_directory_passed_to_scan_file_returns_empty(self, tmp_path: Path):
        folder = tmp_path / "somedir"
        folder.mkdir()
        sigs = self.scanner.scan_file(folder)
        assert sigs == []

    def test_extract_signals_multiple_files(self, tmp_path: Path):
        f1 = tmp_path / "f1.ts"
        f1.write_text("import winston from 'winston';", encoding="utf-8")
        f2 = tmp_path / "f2.ts"
        f2.write_text("import Redis from 'ioredis';", encoding="utf-8")

        all_signals = self.scanner.extract_signals([f1, f2])
        presence_concepts = {s.concept_id for s in all_signals if s.kind == SignalKind.PRESENCE}
        assert "foundation.logging" in presence_concepts
        assert "foundation.caching" in presence_concepts

    def test_scan_project_returns_file_signals(self, tmp_path: Path):
        (tmp_path / "a.ts").write_text("import express from 'express';", encoding="utf-8")
        (tmp_path / "b.js").write_text("import Redis from 'ioredis';", encoding="utf-8")

        file_signals = self.scanner.scan_project(tmp_path)
        assert len(file_signals) == 2
        files = {Path(fs.file).name for fs in file_signals}
        assert files == {"a.ts", "b.js"}


class TestTypeScriptScannerRegistry:
    """Validate scanner registry integration for typescript."""

    def test_registry_lookup(self):
        config = get_scanner("typescript")
        assert config is not None
        assert config.get("enabled") is True
        assert ".ts" in config.get("extensions", [])
        assert ".tsx" in config.get("extensions", [])
        assert ".js" in config.get("extensions", [])
        assert ".jsx" in config.get("extensions", [])

    def test_registry_get_scanner_class(self):
        cls = get_scanner_class("typescript")
        assert cls is TypeScriptScanner

    def test_registry_get_scanner_instance(self):
        inst = get_scanner_instance("typescript")
        assert isinstance(inst, TypeScriptScanner)

    def test_registry_extension_resolution(self):
        assert extension_to_scanner(".ts") == "typescript"
        assert extension_to_scanner("ts") == "typescript"
        assert extension_to_scanner(".tsx") == "typescript"
        assert extension_to_scanner(".js") == "typescript"
        assert extension_to_scanner(".jsx") == "typescript"

    def test_registry_get_scanner_for_file(self, tmp_path: Path):
        ts_file = tmp_path / "index.ts"
        tsx_file = tmp_path / "App.tsx"
        js_file = tmp_path / "server.js"
        jsx_file = tmp_path / "Component.jsx"

        for f in (ts_file, tsx_file, js_file, jsx_file):
            scanner = get_scanner_for_file(f)
            assert isinstance(scanner, TypeScriptScanner)

    def test_registry_enabled_scanners_includes_typescript(self):
        enabled = get_enabled_scanners()
        modules = [s.get("module") for s in enabled]
        assert "sdat.scanners.typescript_scanner" in modules


class TestTypeScriptScannerFixture:
    """Validate the scanner against the realistic node_ts_project fixture."""

    def setup_method(self):
        self.scanner = TypeScriptScanner()
        self.fixture_dir = Path("tests/fixtures/node_ts_project")

    def test_fixture_directory_exists(self):
        assert self.fixture_dir.exists()
        assert self.fixture_dir.is_dir()

    def test_fixture_file_discovery(self):
        discovered = self.scanner.discover_files(self.fixture_dir)
        # Should discover 9 source files (.ts and .tsx)
        assert len(discovered) == 9
        names = {f.name for f in discovered}
        expected = {
            "server.ts",
            "config.ts",
            "telemetry.ts",
            "redis.ts",
            "prisma.ts",
            "payment.service.ts",
            "queue.ts",
            "api.ts",
            "Dashboard.tsx",
        }
        assert expected == names

    def test_fixture_exceeds_15_unique_concepts(self):
        file_signals = self.scanner.scan_project(self.fixture_dir)
        assert len(file_signals) == 9

        presence_concepts: set[str] = set()
        for fs in file_signals:
            for sig in fs.signals:
                if sig.kind == SignalKind.PRESENCE:
                    presence_concepts.add(sig.concept_id)

        # Requirement: at least 15 meaningful concept signals
        assert len(presence_concepts) >= 15
        # The realistic fixture detects 24 distinct concepts
        assert len(presence_concepts) >= 20

    def test_fixture_signal_quality(self):
        file_signals = self.scanner.scan_project(self.fixture_dir)
        for fs in file_signals:
            for sig in fs.signals:
                assert sig.concept_id.startswith(("foundation.", "data.", "security.", "observability.", "resilience.", "deployment.", "performance.", "streaming.", "ux.", "integration.", "ml."))
                assert sig.file_path is not None
                assert len(sig.evidence) > 0
                assert sig.confidence > 0.0
                assert sig.line_range[0] >= 1
                assert sig.line_range[1] >= sig.line_range[0]
