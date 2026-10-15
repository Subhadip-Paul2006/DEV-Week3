"""System Design Explanation Engine (Gemma 4 / AI Enhancement).

Implements NIRĪKṢĀ prompt architecture:
- What is wrong?
- Why is it wrong?
- What impact can it have?
- How should it be fixed?
- And how can we verify the fix?

Operates strictly on grounded deterministic decisions and evidence facts.
Fails open: if AI is disabled or fails, returns standard fallback text.
"""

from __future__ import annotations

from typing import Sequence

from sdat.ai.config import AIConfig
from sdat.ai.gateway import AIGateway
from sdat.ai.grounding import GroundedContext
from sdat.models import Decision
from sdat.telemetry.tracker import AuditTelemetry


class SystemDesignExplainer:
    """Generates explainable architectural reasoning for SDAT audit decisions."""

    def __init__(
        self,
        config: AIConfig | None = None,
        telemetry: AuditTelemetry | None = None,
    ) -> None:
        self.gateway = AIGateway(config=config, telemetry=telemetry)

    def explain_finding(self, decision: Decision, target_root: str = ".") -> str:
        """Generate a Gemma 4 explanation for a single decision."""
        if not self.gateway.config.is_available:
            return self._fallback_explanation(decision)

        system_prompt = (
            "You are NIRĪKṢĀ (तन्त्रविन्यास-निरीक्षा), an expert system-design architecture auditor. "
            "You explain architectural findings clearly, grounding your reasoning strictly in the "
            "provided evidence. Never hallucinate findings or invent missing code."
        )

        prompt = (
            f"Analyze the following verified architectural finding in target root '{target_root}':\n\n"
            f"- Concept ID: {decision.concept_id}\n"
            f"- Concept Name: {decision.concept_name}\n"
            f"- Status: {decision.status.value}\n"
            f"- Priority: {decision.priority.value}\n"
            f"- Confidence: {decision.confidence}\n"
            f"- Evidence: {[f'{e.file}:{e.line} -> {e.snippet}' for e in decision.evidence]}\n"
            f"- Misconfiguration: {decision.misconfiguration}\n"
            f"- Gaps: {decision.gaps}\n"
            f"- Recommendation: {decision.recommendation}\n\n"
            "Provide a concise architectural explanation structured as:\n"
            "1. **What is wrong / status**\n"
            "2. **Why it matters**\n"
            "3. **Potential impact / risks**\n"
            "4. **Remediation steps**\n"
            "5. **Verification method**\n"
        )

        fallback = self._fallback_explanation(decision)
        return self.gateway.complete(prompt, system_prompt=system_prompt, fallback=fallback)

    def generate_executive_summary(self, decisions: Sequence[Decision], target_root: str = ".") -> str:
        """Generate an AI executive summary for the audit report."""
        if not self.gateway.config.is_available:
            return self._fallback_summary(decisions)

        context = GroundedContext.build(decisions, target_root=target_root, character_budget=8000)

        system_prompt = (
            "You are NIRĪKṢĀ (तन्त्रविन्यास-निरीक्षा), an expert system-design architecture auditor. "
            "Write a professional, objective executive summary of the audit findings, highlighting key strengths, "
            "critical risks, and top priority remediation areas. Ground your summary strictly in the provided data."
        )

        prompt = (
            f"Here is the grounded context of the audit run:\n\n{context.format_for_prompt()}\n\n"
            "Write a 3-paragraph executive summary suitable for engineering leadership."
        )

        fallback = self._fallback_summary(decisions)
        return self.gateway.complete(prompt, system_prompt=system_prompt, fallback=fallback)

    @staticmethod
    def _fallback_explanation(decision: Decision) -> str:
        parts = [f"**Concept:** {decision.concept_name} (`{decision.concept_id}`)"]
        parts.append(f"- **Status:** {decision.status.value.title()} (Confidence: {decision.confidence:.0f}%)")
        if decision.recommendation:
            parts.append(f"- **Recommendation:** {decision.recommendation}")
        if decision.gaps:
            parts.append(f"- **Gaps:** {', '.join(decision.gaps)}")
        return "\n".join(parts)

    @staticmethod
    def _fallback_summary(decisions: Sequence[Decision]) -> str:
        total = len(decisions)
        imp = sum(1 for d in decisions if d.status.value == "implemented")
        mis = sum(1 for d in decisions if d.status.value == "missing")
        msc = sum(1 for d in decisions if d.status.value == "misconfigured")
        return (
            f"System Design Audit evaluated {total} architectural concepts: "
            f"{imp} implemented, {mis} missing, and {msc} misconfigured. "
            "Review individual report files for detailed evidence and remediation guidance."
        )
