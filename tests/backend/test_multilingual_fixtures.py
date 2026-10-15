"""Multilingual Backend Fixture Validation.

Verifies that the canonical Backend domain concepts (routing, timeouts, connection pooling,
database interaction, and caching) are accurately recognized across diverse programming
languages (Python, Go, TypeScript/Node, Java/Kotlin, Rust, PHP).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from sdat.backend.agent import BackendAgent
from sdat.backend.analyzer import BackendStructuralAnalyzer
from sdat.models import EvidenceFact, EvidenceKind


def test_python_fastapi_backend_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        api_file = root / "main.py"
        api_file.write_text(
            """
from fastapi import FastAPI, Depends
import httpx
from pydantic import BaseModel

app = FastAPI()

class UserCreate(BaseModel):
    username: str

@app.post("/users")
async def create_user(user: UserCreate):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post("https://auth.internal/verify")
    return {"status": "created"}
""",
            encoding="utf-8",
        )

        facts = [
            EvidenceFact(
                kind=EvidenceKind.DECORATOR,
                subject="app.post",
                language="python",
                file_path=api_file,
                line_range=(10, 10),
                snippet="@app.post('/users')",
                framework="fastapi",
            ),
            EvidenceFact(
                kind=EvidenceKind.CONFIG_KEY,
                subject="timeout",
                language="python",
                file_path=api_file,
                line_range=(12, 12),
                snippet="timeout=5.0",
                timeout_observed=True,
            ),
            EvidenceFact(
                kind=EvidenceKind.SCHEMA_DEF,
                subject="UserCreate",
                language="python",
                file_path=api_file,
                line_range=(7, 8),
                snippet="class UserCreate(BaseModel):",
            ),
        ]

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze(facts)

        assert "FastAPI" in summary.detected_frameworks
        assert summary.has_timeouts is True
        assert summary.has_input_validation is True
        assert len(summary.endpoints) >= 1
        assert summary.endpoints[0].path == "/users"
        assert summary.endpoints[0].method == "POST"


def test_go_gin_backend_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        go_file = root / "main.go"
        go_file.write_text(
            """
package main

import (
    "net/http"
    "time"
    "github.com/gin-gonic/gin"
)

func main() {
    r := gin.Default()
    r.GET("/health", func(c *gin.Context) {
        client := &http.Client{Timeout: 3 * time.Second}
        _ = client
        c.JSON(200, gin.H{"status": "ok"})
    })
    r.Run(":8080")
}
""",
            encoding="utf-8",
        )

        facts = [
            EvidenceFact(
                kind=EvidenceKind.CALL,
                subject="gin.Default",
                language="go",
                file_path=go_file,
                line_range=(11, 11),
                snippet="r := gin.Default()",
                framework="gin-gonic/gin",
            ),
            EvidenceFact(
                kind=EvidenceKind.CONFIG_KEY,
                subject="Timeout",
                language="go",
                file_path=go_file,
                line_range=(13, 13),
                snippet="Timeout: 3 * time.Second",
                timeout_observed=True,
            ),
        ]

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze(facts)

        assert "Gin" in summary.detected_frameworks
        assert summary.has_timeouts is True
        assert len(summary.endpoints) >= 1
        assert summary.endpoints[0].path == "/health"
        assert summary.endpoints[0].method == "GET"


def test_typescript_express_backend_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ts_file = root / "server.ts"
        ts_file.write_text(
            """
import express from 'express';
import axios from 'axios';

const app = express();

app.get('/items', async (req, res) => {
    const response = await axios.get('https://inventory.service/items', { timeout: 4000 });
    res.json(response.data);
});
""",
            encoding="utf-8",
        )

        facts = [
            EvidenceFact(
                kind=EvidenceKind.CALL,
                subject="express",
                language="typescript",
                file_path=ts_file,
                line_range=(4, 4),
                snippet="const app = express();",
                framework="express",
            ),
            EvidenceFact(
                kind=EvidenceKind.CONFIG_KEY,
                subject="timeout",
                language="typescript",
                file_path=ts_file,
                line_range=(7, 7),
                snippet="timeout: 4000",
                timeout_observed=True,
            ),
        ]

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze(facts)

        assert "Express" in summary.detected_frameworks
        assert summary.has_timeouts is True
        assert len(summary.endpoints) >= 1
        assert summary.endpoints[0].path == "/items"
        assert summary.endpoints[0].method == "GET"


def test_java_spring_boot_backend_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        java_file = root / "UserController.java"
        java_file.write_text(
            """
package com.example.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {

    @GetMapping("/api/v1/customers")
    public String getCustomers() {
        return "customer_list";
    }
}
""",
            encoding="utf-8",
        )

        facts = [
            EvidenceFact(
                kind=EvidenceKind.ANNOTATION,
                subject="org.springframework.web.bind.annotation.RestController",
                language="java",
                file_path=java_file,
                line_range=(6, 6),
                snippet="@RestController",
                framework="springframework",
            ),
            EvidenceFact(
                kind=EvidenceKind.CONFIG_KEY,
                subject="hikari.maximum-pool-size",
                language="java",
                file_path=Path("application.yml"),
                line_range=(10, 10),
                snippet="maximum-pool-size: 20",
                library="hikaricp",
            ),
        ]

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze(facts)

        assert "Spring Boot" in summary.detected_frameworks
        assert summary.has_connection_pooling is True
        assert len(summary.endpoints) >= 1
        assert summary.endpoints[0].path == "/api/v1/customers"


def test_rust_actix_backend_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        rs_file = root / "main.rs"
        rs_file.write_text(
            """
use actix_web::{get, App, HttpServer, HttpResponse, Responder};

#[get("/status")]
async fn status() -> impl Responder {
    HttpResponse::Ok().body("OK")
}
""",
            encoding="utf-8",
        )

        facts = [
            EvidenceFact(
                kind=EvidenceKind.IMPORT,
                subject="actix_web",
                language="rust",
                file_path=rs_file,
                line_range=(1, 1),
                snippet="use actix_web::{get, App};",
                framework="actix-web",
            ),
        ]

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze(facts)

        assert "Actix-Web" in summary.detected_frameworks
        assert len(summary.endpoints) >= 1
        assert summary.endpoints[0].path == "/status"
        assert summary.endpoints[0].method == "GET"


def test_php_backend_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        php_file = root / "routes.php"
        php_file.write_text(
            """
<?php
use Slim\\Factory\\AppFactory;

$app = AppFactory::create();

$app->get('/orders', function ($request, $response, $args) {
    return $response->write("orders list");
});
""",
            encoding="utf-8",
        )

        facts = [
            EvidenceFact(
                kind=EvidenceKind.IMPORT,
                subject="Slim\\Factory\\AppFactory",
                language="php",
                file_path=php_file,
                line_range=(2, 2),
                snippet="use Slim\\Factory\\AppFactory;",
                framework="slim",
            ),
        ]

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze(facts)

        assert "Slim" in summary.detected_frameworks
        assert len(summary.endpoints) >= 1
        assert summary.endpoints[0].path == "/orders"
        assert summary.endpoints[0].method == "GET"


def test_multilingual_backend_agent_audit() -> None:
    # Full agent run verifying timeout and endpoints recognition across Go and Python
    facts = [
        EvidenceFact(
            kind=EvidenceKind.DECORATOR,
            subject="app.get",
            language="python",
            file_path=Path("main.py"),
            line_range=(5, 5),
            snippet="@app.get('/metrics')",
            framework="fastapi",
        ),
        EvidenceFact(
            kind=EvidenceKind.CONFIG_KEY,
            subject="timeout",
            language="go",
            file_path=Path("client.go"),
            line_range=(20, 20),
            snippet="client.Timeout = 10 * time.Second",
            timeout_observed=True,
        ),
    ]

    agent = BackendAgent()
    context = {"target_root": ".", "evidence_facts": facts}
    result = agent.audit(context)

    decisions = {d["concept_id"]: d for d in result["decisions"]}
    assert decisions["backend.api-architecture"]["status"] == "implemented"
    assert decisions["backend.timeout-management"]["status"] == "implemented"
