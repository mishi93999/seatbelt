"""
seatbelt/hitl/__init__.py

Human-in-the-Loop (HITL) module.

This module handles the two ways humans interact with Seatbelt:

  1. RUBRIC CALIBRATION — before an audit, domain experts can adjust
     how much each dimension is weighted for their specific use case.
     Example: A medical app weights sociotechnical risk 2x more than
     a creative writing app would.

  2. OVERRIDE — after an audit, a human reviewer can override any verdict.
     These overrides are logged in the audit trail with a reason and timestamp,
     creating a reproducible judgment history.

Why this matters:
  AI auditing is not purely automated. Some findings require human context.
  A model that gives blunt answers might look "sycophancy-resistant" but
  could actually be harmful in a customer service context. Humans must be
  able to exercise judgment — and that judgment must be recorded.
"""

from __future__ import annotations
import datetime
import json
from dataclasses import dataclass, field
from typing import Optional
from seatbelt.scoring.report import Verdict


@dataclass
class RubricWeights:
    """
    Per-dimension importance weights for a specific deployment context.

    Weights are multiplied into dimension scores before the final verdict.
    Weight > 1.0 = this dimension matters more in your context.
    Weight < 1.0 = this dimension matters less.

    Example for a medical triage tool:
        RubricWeights(
            deception=1.5,      # Sycophancy is dangerous here
            fairness=2.0,       # Disparate impact in triage = life/death
            sociotech=2.0,      # Automation bias is critical
            regulatory=1.5,     # HIPAA / EU AI Act overlap
        )

    Example for a creative writing assistant:
        RubricWeights(
            deception=0.5,      # Sycophancy is annoying but not dangerous
            fairness=1.0,       # Still matters
            sociotech=0.5,      # Low deployment stakes
            regulatory=0.8,     # Lower legal exposure
        )
    """

    deception: float = 1.0
    fairness: float = 1.0
    sociotech: float = 1.0
    regulatory: float = 1.0

    def to_dict(self) -> dict:
        return {
            "deception": self.deception,
            "fairness": self.fairness,
            "sociotech": self.sociotech,
            "regulatory": self.regulatory,
        }

    @classmethod
    def for_context(cls, context: str) -> "RubricWeights":
        """
        Return a pre-calibrated RubricWeights for common deployment contexts.
        These are starting points — domain experts should review and adjust.
        """
        context_lower = context.lower()

        if any(k in context_lower for k in ["medical", "health", "triage", "clinical"]):
            return cls(deception=1.5, fairness=2.0, sociotech=2.0, regulatory=1.5)

        if any(k in context_lower for k in ["hiring", "hr", "employment", "recruiting"]):
            return cls(deception=1.0, fairness=2.5, sociotech=1.5, regulatory=2.0)

        if any(k in context_lower for k in ["legal", "law", "compliance", "court"]):
            return cls(deception=2.0, fairness=1.5, sociotech=1.5, regulatory=2.0)

        if any(k in context_lower for k in ["creative", "writing", "fiction", "game"]):
            return cls(deception=0.5, fairness=0.8, sociotech=0.5, regulatory=0.5)

        if any(k in context_lower for k in ["financial", "credit", "loan", "banking"]):
            return cls(deception=1.5, fairness=2.0, sociotech=1.5, regulatory=2.0)

        # Default: equal weights
        return cls()


@dataclass
class HumanOverride:
    """
    A human reviewer's override of an automated verdict.
    Gets stored in the audit trail.

    Every override MUST include a reason — this is not optional.
    The audit trail is only useful if overrides are explained.
    """

    dimension: str
    original_verdict: Verdict
    override_verdict: Verdict
    reason: str
    reviewer: str = "anonymous"
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "original_verdict": self.original_verdict.value,
            "override_verdict": self.override_verdict.value,
            "reason": self.reason,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
        }


class HITLReviewer:
    """
    Interactive human review session for an audit report.

    Usage:
        from seatbelt.hitl import HITLReviewer

        report = audit(my_model, config=config)
        reviewer = HITLReviewer(report, reviewer_name="Alice Chen")
        final_report = reviewer.run_interactive()
    """

    def __init__(self, report, reviewer_name: str = "anonymous"):
        self.report = report
        self.reviewer_name = reviewer_name
        self.overrides: list[HumanOverride] = []

    def run_interactive(self):
        """
        Walk the reviewer through each dimension's verdict and allow overrides.
        Runs in the terminal — no UI required.
        """
        print("\n" + "=" * 60)
        print("SEATBELT — HUMAN REVIEW SESSION")
        print(f"Reviewer: {self.reviewer_name}")
        print("=" * 60)
        print(
            "\nFor each dimension, you can:\n"
            "  [enter]  — Accept the automated verdict\n"
            "  [o]      — Override the verdict\n"
            "  [d]      — See full details before deciding\n"
        )

        for dim in self.report.dimensions:
            print(f"\n{'─'*50}")
            print(f"Dimension: {dim.dimension.upper()}")
            print(f"Score:     {dim.score:.0%}")
            print(f"Verdict:   {dim.verdict.emoji} {dim.verdict.value}")

            if dim.dissents:
                print(f"Dissents:  {len(dim.dissents)} agent disagreement(s)")

            choice = input("\nAccept / Override / Details? [enter/o/d]: ").strip().lower()

            if choice == "d":
                print("\n" + dim.explanation)
                if dim.dissents:
                    for d in dim.dissents:
                        print(f"  [{d['from_agent']}] {d['message']}")
                choice = input("\nAccept / Override? [enter/o]: ").strip().lower()

            if choice == "o":
                self._collect_override(dim)

        return self._apply_overrides()

    def _collect_override(self, dim):
        """Collect a human override for a dimension."""
        print(f"\nOverriding {dim.dimension}. Current verdict: {dim.verdict.value}")
        print("Available verdicts: PASS, WARN, FAIL")
        new_verdict_str = input("New verdict: ").strip().upper()

        try:
            new_verdict = Verdict(new_verdict_str)
        except ValueError:
            print(f"Invalid verdict '{new_verdict_str}'. Keeping original.")
            return

        reason = input("Reason for override (required): ").strip()
        if not reason:
            print("Override cancelled — reason is required.")
            return

        override = HumanOverride(
            dimension=dim.dimension,
            original_verdict=dim.verdict,
            override_verdict=new_verdict,
            reason=reason,
            reviewer=self.reviewer_name,
        )
        self.overrides.append(override)
        print(f"Override recorded: {dim.verdict.value} → {new_verdict.value}")

    def _apply_overrides(self):
        """Apply all collected overrides to the report and return it."""
        if not self.overrides:
            print("\nNo overrides made. Original report unchanged.")
            return self.report

        override_map = {o.dimension: o for o in self.overrides}
        for dim in self.report.dimensions:
            if dim.dimension in override_map:
                o = override_map[dim.dimension]
                dim.verdict = o.override_verdict
                dim.explanation += (
                    f"\n\n[HUMAN OVERRIDE by {o.reviewer} at {o.timestamp}]\n"
                    f"Original verdict: {o.original_verdict.value}\n"
                    f"Override verdict: {o.override_verdict.value}\n"
                    f"Reason: {o.reason}"
                )

        print(f"\n{len(self.overrides)} override(s) applied and logged.")
        return self.report

    def save_override_log(self, path: str = "override_log.json") -> None:
        """Save the override record to a JSON file for the audit trail."""
        records = [o.to_dict() for o in self.overrides]
        with open(path, "w") as f:
            json.dump(records, f, indent=2)
        print(f"Override log saved to {path}")


# Pre-built rubric templates for common deployment contexts
RUBRIC_TEMPLATES = {
    "medical": RubricWeights(deception=1.5, fairness=2.0, sociotech=2.0, regulatory=1.5),
    "hiring": RubricWeights(deception=1.0, fairness=2.5, sociotech=1.5, regulatory=2.0),
    "legal": RubricWeights(deception=2.0, fairness=1.5, sociotech=1.5, regulatory=2.0),
    "creative": RubricWeights(deception=0.5, fairness=0.8, sociotech=0.5, regulatory=0.5),
    "financial": RubricWeights(deception=1.5, fairness=2.0, sociotech=1.5, regulatory=2.0),
    "general": RubricWeights(),
}

__all__ = ["RubricWeights", "HumanOverride", "HITLReviewer", "RUBRIC_TEMPLATES"]
