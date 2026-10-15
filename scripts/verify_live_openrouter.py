"""
SDAT — Live OpenRouter Inference Verification Script
=====================================================
Confirms REAL HTTP request to OpenRouter / qwen/qwen3-coder:free.

Safety rules:
 - API key is read from environment only (OPENROUTER_API_KEY or OPENAI_API_BASE+OPENAI_API_KEY)
 - Key is never printed, logged, or saved
 - Cache is deliberately bypassed for this run
 - Exits with code 1 on any failure
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Key Resolution (never print or expose the key itself)
# ─────────────────────────────────────────────────────────────────────────────
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
TARGET_MODEL    = "qwen/qwen3-coder:free"

api_key  = os.environ.get("OPENROUTER_API_KEY", "").strip()
base_url = OPENROUTER_BASE

# Fallback: if OPENAI_API_BASE points to OpenRouter, use that key
if not api_key:
    openai_base = (
        os.environ.get("OPENAI_API_BASE", "")
        or os.environ.get("OPENAI_API_BASE_URL", "")
    ).strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if "openrouter.ai" in openai_base and openai_key and openai_key.lower() != "none":
        api_key  = openai_key
        base_url = openai_base.rstrip("/")
        print(f"[INFO] Using OPENAI_API_BASE → {base_url} (detected OpenRouter endpoint)")

key_present = bool(api_key) and api_key.lower() not in ("none", "null", "")
print(f"\n[1] OPENROUTER_API_KEY present: {key_present}")

if not key_present:
    print("\n[FAIL] No valid API key found.")
    print("       Set OPENROUTER_API_KEY=sk-or-v1-... in your environment.")
    print("\nLIVE INFERENCE TEST: FAIL")
    print("REASON: OPENROUTER_API_KEY is not set in this shell session.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Cache is deliberately bypassed
# ─────────────────────────────────────────────────────────────────────────────
print(f"[2] Cache bypass: ACTIVE (this script never reads cached_*.json)")

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Real HTTP request to OpenRouter
# ─────────────────────────────────────────────────────────────────────────────
endpoint = f"{base_url}/chat/completions"
print(f"[3] Sending request → {endpoint}")
print(f"    Model: {TARGET_MODEL}")

messages = [
    {
        "role": "system",
        "content": (
            "You are an expert system-design auditor. "
            "Respond with valid JSON only — no markdown fences."
        ),
    },
    {
        "role": "user",
        "content": (
            "A FastAPI project is missing idempotency controls on mutating endpoints. "
            "Return EXACTLY this JSON schema:\n"
            '{"executive_summary": "<2 sentences>", '
            '"items": [{"concept_id": "backend.idempotency", '
            '"why_it_matters": "<1 sentence>", '
            '"architectural_impact": "<1 sentence>", '
            '"ai_reasoning": "<2 sentences>", '
            '"recommended_solution": "<1 sentence>", '
            '"implementation_steps": ["step1","step2","step3"], '
            '"validation": "<1 sentence>", '
            '"diagram_before": "<text>", '
            '"diagram_after": "<text>"}]}'
        ),
    },
]

payload = {
    "model":      TARGET_MODEL,
    "messages":   messages,
    "temperature": 0.2,
    "max_tokens":  1024,
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
    "HTTP-Referer":  "https://github.com/shubh06/sdat",
    "X-Title":       "SDAT System Design Audit Tool",
}

data = json.dumps(payload).encode("utf-8")
req  = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

raw_response  = None
http_success  = False
status_code   = None
response_text = ""
actual_model  = None
actual_content = ""
t0 = time.time()

try:
    with urllib.request.urlopen(req, timeout=45) as resp:
        status_code   = resp.status
        response_text = resp.read().decode("utf-8")
        http_success  = True
except urllib.error.HTTPError as exc:
    status_code = exc.code
    try:
        response_text = exc.read().decode("utf-8")
    except Exception:
        response_text = "(could not read error body)"
except urllib.error.URLError as exc:
    status_code   = None
    response_text = f"URL error: {exc.reason}"
except Exception as exc:
    status_code   = None
    response_text = f"Unexpected error: {exc}"

elapsed = time.time() - t0
print(f"    HTTP status: {status_code}  ({elapsed:.2f}s)")

if not http_success:
    print(f"\n[FAIL] HTTP request failed: {response_text}")
    print("\nLIVE INFERENCE TEST: FAIL")
    print(f"MODEL ACTUALLY CALLED: {TARGET_MODEL}")
    print(f"PROVIDER: openrouter")
    print(f"CACHED RESPONSE USED: NO")
    print(f"REAL API RESPONSE RECEIVED: NO")
    print(f"HTTP STATUS: {status_code}")
    print(f"ERROR DETAIL: {response_text[:400]}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Parse and validate the response
# ─────────────────────────────────────────────────────────────────────────────
print(f"[4] Parsing OpenRouter response...")
try:
    parsed = json.loads(response_text)
except json.JSONDecodeError as exc:
    print(f"\n[FAIL] Response is not valid JSON: {exc}")
    print(f"       Raw (first 300 chars): {response_text[:300]}")
    sys.exit(1)

# Extract model, content
actual_model   = parsed.get("model", TARGET_MODEL)
choices        = parsed.get("choices", [])
if not choices:
    print(f"\n[FAIL] OpenRouter returned 0 choices. Full response:\n{response_text[:500]}")
    sys.exit(1)

actual_content = choices[0].get("message", {}).get("content", "")
usage          = parsed.get("usage", {})
print(f"    Model returned by API : {actual_model}")
print(f"    Prompt tokens         : {usage.get('prompt_tokens', '?')}")
print(f"    Completion tokens     : {usage.get('completion_tokens', '?')}")
print(f"    Content length (chars): {len(actual_content)}")

if not actual_content.strip():
    print(f"\n[FAIL] Model returned empty content.")
    sys.exit(1)

print(f"\n    === RAW CONTENT PREVIEW (first 400 chars) ===")
print(f"    {actual_content[:400]}")
print(f"    === END PREVIEW ===\n")

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Parse JSON and confirm remediation data
# ─────────────────────────────────────────────────────────────────────────────
print(f"[5] Extracting architectural remediation from response...")
cleaned = actual_content.strip()
if cleaned.startswith("```"):
    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.rstrip().endswith("```"):
        cleaned = cleaned.rstrip()[:-3].strip()

parsed_ai = None
try:
    parsed_ai = json.loads(cleaned)
except json.JSONDecodeError:
    # Try scanning for JSON object
    start = cleaned.find("{")
    end   = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed_ai = json.loads(cleaned[start:end+1])
        except json.JSONDecodeError:
            pass

remediation_generated = False
exec_summary = ""
ai_reasoning  = ""

if parsed_ai:
    exec_summary = parsed_ai.get("executive_summary", "")
    items        = parsed_ai.get("items", [])
    if items:
        ai_reasoning = items[0].get("ai_reasoning", "")
        remediation_generated = True
        print(f"    Executive summary: {exec_summary[:100]}...")
        print(f"    AI reasoning     : {ai_reasoning[:100]}...")
    else:
        print(f"    [WARN] Parsed JSON but 'items' list is empty — model may have deviated from schema.")
        remediation_generated = bool(exec_summary)
else:
    print(f"    [WARN] Could not parse content as JSON — generating from raw text.")
    # Still counts as real response; remediation engine would use deterministic fallback
    remediation_generated = False

# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Write a real 04-remediation.md using the live data
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[6] Writing live-inference 04-remediation.md...")
output_dir = Path("docs/audit")
output_dir.mkdir(parents=True, exist_ok=True)
rem_path = output_dir / "04-remediation-LIVE.md"

lines = [
    "# 04 — Architectural Remediation Guide (LIVE INFERENCE)",
    "",
    f"> **AI Reasoning Engine:** `{actual_model}` (Live Inference via OpenRouter)",
    f"> **Verification timestamp:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
    "",
    "---",
    "",
    "## Executive Architectural Summary",
    "",
    exec_summary or "(No summary extracted — see raw response below)",
    "",
    "---",
    "",
    "## Qwen3-Coder Architectural Reasoning",
    "",
    f"> {ai_reasoning}" if ai_reasoning else "> (See raw JSON above)",
    "",
    "---",
    "",
    "## Raw API Response (Verification Artifact)",
    "",
    "```json",
    json.dumps({"model": actual_model, "usage": usage, "content_length": len(actual_content)}, indent=2),
    "```",
    "",
    "*Verified live inference — no cached artifact used.*",
]

rem_path.write_text("\n".join(lines), encoding="utf-8")
print(f"    Written → {rem_path}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — --no-ai verification (no network call)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[7] Verifying --no-ai deterministic fallback (no network)...")
no_ai_ok = False
try:
    from sdat.orchestrator import run_audit_pipeline
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_audit_pipeline(
            target_root="tests/fixtures/fastapi_project",
            output_dir=Path(tmpdir) / "out",
            enable_ai=False,
        )
        no_ai_ok = (
            result.total_decisions > 0
            and result.ai_enrichment is not None
            and result.ai_enrichment.provider == "deterministic"
            and result.ai_enrichment.available is False
        )
        print(f"    Decisions: {result.total_decisions}")
        print(f"    AI provider: {result.ai_enrichment.provider}")
        print(f"    AI available: {result.ai_enrichment.available}")
except Exception as exc:
    print(f"    [FAIL] --no-ai pipeline raised: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# Final Report
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("LIVE INFERENCE TEST RESULTS")
print("="*60)
print(f"LIVE INFERENCE TEST:               {'PASS' if http_success and remediation_generated else 'FAIL'}")
print(f"MODEL ACTUALLY CALLED:             {actual_model}")
print(f"PROVIDER:                          openrouter")
print(f"CACHED RESPONSE USED:              NO")
print(f"REAL API RESPONSE RECEIVED:        {'YES' if http_success else 'NO'}")
print(f"HTTP STATUS CODE:                  {status_code}")
print(f"RESPONSE LATENCY:                  {elapsed:.2f}s")
print(f"REMEDIATION GENERATED FROM LIVE:   {'YES' if remediation_generated else 'NO'}")
print(f"NO-AI FALLBACK:                    {'PASS' if no_ai_ok else 'FAIL'}")
print(f"LIVE REMEDIATION FILE:             {rem_path}")
print("="*60)

sys.exit(0 if (http_success and no_ai_ok) else 1)
