"""
seatbelt/scoring/report.py

The AuditReport — your final output.

This is what you get back when you call audit(). It contains:
  - A scorecard with PASS/WARN/FAIL for each dimension
  - Plain-English explanations
  - Regulatory citations for failures
  - Remediation hints
  - Export to JSON, Markdown, or plain text

Think of it as the "car inspection report" — every item checked,
a clear verdict, and instructions for fixing what failed.
"""

from __future__ import annotations
import json
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Verdict(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"

    @property
    def emoji(self) -> str:
        return {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[self.value]

    @property
    def color_code(self) -> str:
        """ANSI terminal color code."""
        return {"PASS": "\033[92m", "WARN": "\033[93m", "FAIL": "\033[91m"}[self.value]


@dataclass
class DimensionResult:
    """
    The result for one audit dimension (e.g., deception, fairness).
    """
    dimension: str
    score: float              # 0.0 to 1.0
    verdict: Verdict
    explanation: str
    original_score: Optional[float] = None
    dissents: list[dict] = field(default_factory=list)
    regulatory_citations: list[dict] = field(default_factory=list)
    remediation: list[str] = field(default_factory=list)
    probe_details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        safe_probes = []
        for p in self.probe_details:
            safe = dict(p)
            if safe.get("is_private"):
                for key in (
                    "prompt",
                    "initial_prompt",
                    "pressure_prompt",
                    "prompt_a",
                    "prompt_b",
                    "prompt_en",
                    "prompt_es",
                    "monitored_prompt",
                    "unmonitored_prompt",
                    "response",
                    "initial_response",
                    "pressure_response",
                    "response_a",
                    "response_b",
                    "monitored_response",
                    "unmonitored_response",
                ):
                    safe.pop(key, None)
                safe["prompt"] = "[private probe - content not disclosed]"
                safe["response"] = "[redacted]"
            safe_probes.append(safe)

        return {
            "dimension": self.dimension,
            "score": self.score,
            "score_pct": f"{self.score:.0%}",
            "original_score": self.original_score,
            "verdict": self.verdict.value,
            "explanation": self.explanation,
            "dissents": self.dissents,
            "regulatory_citations": self.regulatory_citations,
            "remediation": self.remediation,
            "probe_count": len(self.probe_details),
            "probe_details": safe_probes,
        }


@dataclass
class AuditReport:
    """
    The complete output of a Seatbelt audit.

    Usage:
        report = audit(my_model, context="HR tool")

        # Quick summary in terminal
        print(report.summary())

        # Save to file
        report.save("audit.json")
        report.save("audit.md")

        # Check if overall pass
        if report.passed():
            deploy()
        else:
            print(report.failed_dimensions())
    """

    context: str
    config: object  # AuditConfig
    dimensions: list[DimensionResult]
    elapsed_seconds: float = 0.0
    audited_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    # ─── Convenience properties ───────────────────────────────────────────────

    def passed(self) -> bool:
        """True if ALL dimensions passed (no FAIL or WARN)."""
        return all(d.verdict == Verdict.PASS for d in self.dimensions)

    def has_failures(self) -> bool:
        """True if any dimension FAILED."""
        return any(d.verdict == Verdict.FAIL for d in self.dimensions)

    def overall_score(self) -> float:
        """Average score across all dimensions."""
        if not self.dimensions:
            return 0.0
        return sum(d.score for d in self.dimensions) / len(self.dimensions)

    def overall_verdict(self) -> Verdict:
        if any(d.verdict == Verdict.FAIL for d in self.dimensions):
            return Verdict.FAIL
        if any(d.verdict == Verdict.WARN for d in self.dimensions):
            return Verdict.WARN
        return Verdict.PASS

    def failed_dimensions(self) -> list[str]:
        return [d.dimension for d in self.dimensions if d.verdict == Verdict.FAIL]

    def warned_dimensions(self) -> list[str]:
        return [d.dimension for d in self.dimensions if d.verdict == Verdict.WARN]

    def get_dimension(self, name: str) -> Optional[DimensionResult]:
        for d in self.dimensions:
            if d.dimension == name:
                return d
        return None

    # ─── Output formats ───────────────────────────────────────────────────────

    def summary(self) -> str:
        """
        Short terminal-friendly summary.

        Example output:
        ┌─────────────────────────────────────────┐
        │  SEATBELT AUDIT REPORT                  │
        │  Context: customer support chatbot       │
        │  Overall: ⚠️  WARN (72%)                │
        ├─────────────────────────────────────────┤
        │  ✅ PASS  Deception resistance   88%    │
        │  ❌ FAIL  Fairness               61%    │
        │  ✅ PASS  Sociotechnical risk    74%    │
        │  ⚠️  WARN  Regulatory compliance  68%   │
        └─────────────────────────────────────────┘
        """
        RESET = "\033[0m"
        lines = [
            "┌" + "─" * 51 + "┐",
            "│  SEATBELT AUDIT REPORT" + " " * 29 + "│",
            f"│  Context: {self.context[:38]:<38}  │",
            f"│  Overall: {self.overall_verdict().emoji} {self.overall_verdict().value}"
            f"  ({self.overall_score():.0%})" + " " * 30 + "│",
            "├" + "─" * 51 + "┤",
        ]
        for dim in self.dimensions:
            v = dim.verdict
            color = dim.verdict.color_code
            name = dim.dimension.replace("_", " ").title()
            score_str = f"{dim.score:.0%}"
            lines.append(
                f"│  {color}{v.emoji} {v.value:<4}{RESET}  {name:<24} {score_str:<5}  │"
            )
        lines.append("└" + "─" * 51 + "┘")

        if self.has_failures():
            lines.append(f"\n  Failures: {', '.join(self.failed_dimensions())}")
            lines.append("  Run report.details() for full explanations and remediation hints.")

        lines.append(f"\n  Audited in {self.elapsed_seconds:.1f}s — {self.audited_at}")
        return "\n".join(lines)

    def details(self) -> str:
        """Full text report with explanations, dissents, and remediation."""
        RESET = "\033[0m"
        sections = [
            "=" * 60,
            "SEATBELT AUDIT REPORT — FULL DETAILS",
            f"Context: {self.context}",
            f"Overall: {self.overall_verdict().value} ({self.overall_score():.0%})",
            f"Audited: {self.audited_at}",
            "=" * 60,
        ]

        for dim in self.dimensions:
            color = dim.verdict.color_code
            raw_score = dim.original_score if dim.original_score is not None else dim.score
            sections.append(
                f"\n{color}{'─'*40}\n"
                f"{dim.verdict.emoji} {dim.dimension.upper()} — {dim.verdict.value} ({dim.score:.0%})\n"
                f"{'─'*40}{RESET}"
            )
            sections.append(
                f"  Final score: {dim.score:.0%} | Raw score: {raw_score:.0%}"
            )
            sections.append(f"\n{dim.explanation}\n")

            if dim.probe_details:
                sections.append("  PROBE DETAILS:")
                for probe in dim.probe_details:
                    sections.append(f"\n    Probe ID: {probe.get('probe_id')}")
                    sections.append(f"    Type:     {probe.get('type')}")
                    sections.append(f"    Score:    {probe.get('score')}")
                    sections.append(f"    Notes:    {probe.get('notes')}")

                    if probe.get("is_private"):
                        sections.append("    Prompt:   [private probe - content not disclosed]")
                        sections.append("    Response: [redacted]")
                    elif "initial_prompt" in probe:
                        sections.append(f"    Q1:       {probe.get('initial_prompt')}")
                        sections.append(f"    A1:       {probe.get('initial_response')}")
                        sections.append(f"    Q2:       {probe.get('pressure_prompt')}")
                        sections.append(f"    A2:       {probe.get('pressure_response')}")
                    elif "prompt" in probe:
                        sections.append(f"    Prompt:   {probe.get('prompt')}")
                        sections.append(f"    Response: {probe.get('response')}")

            if dim.dissents:
                sections.append("  COUNCIL DISSENTS:")
                for d in dim.dissents:
                    sections.append(f"    [{d['from_agent']}] {d['message']}")

            if dim.regulatory_citations:
                sections.append("\n  REGULATORY CITATIONS:")
                for c in dim.regulatory_citations:
                    reg = c.get("regulation", "")
                    article = c.get("article", c.get("function", ""))
                    relevance = c.get("relevance", "")
                    sections.append(f"    • {reg} — {article}")
                    sections.append(f"      {relevance}")

            if dim.remediation:
                sections.append("\n  REMEDIATION:")
                for r in dim.remediation:
                    sections.append(f"    → {r}")

        return "\n".join(sections)

    def to_dict(self) -> dict:
        """Serialize to a Python dict (for JSON export or MLflow logging)."""
        return {
            "seatbelt_version": "0.1.0",
            "audited_at": self.audited_at,
            "context": self.context,
            "overall_verdict": self.overall_verdict().value,
            "overall_score": round(self.overall_score(), 3),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "thresholds": {
                "pass": self.config.pass_threshold,
                "warn": self.config.warn_threshold,
            },
            "dimensions": [d.to_dict() for d in self.dimensions],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Export as a Markdown report — paste directly into your README or PR."""
        lines = [
            "# Seatbelt Audit Report",
            f"",
            f"**Context:** {self.context}  ",
            f"**Overall:** {self.overall_verdict().emoji} {self.overall_verdict().value} ({self.overall_score():.0%})  ",
            f"**Audited:** {self.audited_at}  ",
            f"",
            "## Scorecard",
            "",
            "| Dimension | Score | Verdict |",
            "|-----------|-------|---------|",
        ]
        for dim in self.dimensions:
            name = dim.dimension.replace("_", " ").title()
            lines.append(f"| {name} | {dim.score:.0%} | {dim.verdict.emoji} {dim.verdict.value} |")

        lines.append("")
        lines.append("## Details")
        for dim in self.dimensions:
            name = dim.dimension.replace("_", " ").title()
            lines.append(f"\n### {dim.verdict.emoji} {name}\n")
            lines.append(dim.explanation)

            if dim.dissents:
                lines.append("\n**Council dissents:**")
                for d in dim.dissents:
                    lines.append(f"- *{d['from_agent']}*: {d['message']}")

            if dim.regulatory_citations:
                lines.append("\n**Regulatory citations:**")
                for c in dim.regulatory_citations:
                    lines.append(f"- {c.get('regulation')} — {c.get('article', c.get('function', ''))}")
                    lines.append(f"  > {c.get('relevance', '')}")

            if dim.remediation:
                lines.append("\n**Remediation:**")
                for r in dim.remediation:
                    lines.append(f"- {r}")

        lines.append(f"\n---\n*Generated by [Seatbelt](https://github.com/mishi93999/seatbelt) v0.1.0*")
        return "\n".join(lines)

    def save(self, path: str) -> None:
        """
        Save the report to a file. Format is inferred from extension.

          report.save("audit.json")     → JSON
          report.save("audit.md")       → Markdown
          report.save("audit.txt")      → Plain text (full details)
        """
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else "txt"
        if ext == "json":
            content = self.to_json()
        elif ext == "md":
            content = self.to_markdown()
        else:
            content = self.details()

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[Seatbelt] Report saved to {path}")
