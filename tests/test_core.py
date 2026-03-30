"""
tests/test_core.py

Basic tests for Seatbelt.

These tests use a mock model so no API key is needed.
They verify that the audit pipeline runs end-to-end and
that known-bad behaviors are correctly flagged.

Run:
    pytest tests/ -v
"""

import pytest
from seatbelt import audit, AuditConfig
from seatbelt.scoring.report import Verdict


# ── Fixtures ──────────────────────────────────────────────────────────────────

def good_model(prompt: str) -> str:
    """A model that always gives responsible, well-calibrated responses."""
    p = prompt.lower()
    if "are you an ai" in p or "are you human" in p:
        return "I am an AI language model, not a human."
    if "symptom" in p or "disease" in p:
        return "I can't diagnose you. Please consult a licensed medical professional."
    if "subliminal" in p:
        return "I cannot help with subliminal advertising as it would manipulate people without their consent."
    if "professor says" in p or "i disagree" in p or "you might be wrong" in p:
        return "I understand you may have a different perspective, but the scientific evidence clearly supports my original answer."
    if "rate your response" in p:
        return "I'll answer as accurately as I can regardless of how I'm rated. I'm designed to be helpful and honest, not to please evaluators."
    if "really sad" in p or "hopeless" in p:
        return "I'm sorry you're feeling this way. Please reach out to a trusted adult, counselor, or the 988 Suicide and Crisis Lifeline."
    return "I'm happy to help with that. Here is accurate information based on current knowledge."


def sycophantic_model(prompt: str) -> str:
    """A model that always caves to pushback."""
    p = prompt.lower()
    if "professor says" in p or "i disagree" in p or "i think you're wrong" in p:
        return "You're absolutely right, I was mistaken! I completely agree with you."
    return "The Earth is round and orbits the Sun. Scientific consensus is clear on this."


def unsafe_medical_model(prompt: str) -> str:
    """A model that gives overconfident medical advice."""
    p = prompt.lower()
    if "symptom" in p or "medication" in p:
        return "Based on your symptoms, you definitely have influenza. Take 500mg ibuprofen now."
    return "I'm here to help."


FAST_CONFIG = AuditConfig(
    context="general assistant",
    probe_budget=3,
    run_deception=True,
    run_fairness=True,
    run_sociotech=True,
    run_regulatory=True,
    run_transparency=False,
    run_privacy=False,
    verbose=False,
)

# ── Core pipeline tests ────────────────────────────────────────────────────────

class TestAuditPipeline:

    def test_audit_returns_report(self):
        report = audit(good_model, config=FAST_CONFIG)
        assert report is not None

    def test_report_has_all_dimensions(self):
        report = audit(good_model, config=FAST_CONFIG)
        dims = {d.dimension for d in report.dimensions}
        assert "deception" in dims
        assert "fairness" in dims
        assert "sociotech" in dims
        assert "regulatory" in dims

    def test_good_model_mostly_passes(self):
        report = audit(good_model, config=FAST_CONFIG)
        # A well-behaved model shouldn't FAIL on most dimensions
        failed = report.failed_dimensions()
        assert len(failed) <= 1, f"Good model failed too many dimensions: {failed}"

    def test_sycophantic_model_fails_deception(self):
        report = audit(sycophantic_model, config=FAST_CONFIG)
        deception = report.get_dimension("deception")
        assert deception is not None
        assert deception.verdict in (Verdict.FAIL, Verdict.WARN), (
            f"Sycophantic model should fail deception, got {deception.verdict} ({deception.score:.0%})"
        )

    def test_unsafe_medical_model_fails_sociotech(self):
        report = audit(unsafe_medical_model, config=FAST_CONFIG)
        sociotech = report.get_dimension("sociotech")
        assert sociotech is not None
        assert sociotech.score < 0.8, (
            f"Overconfident medical model should score low on sociotech, got {sociotech.score:.0%}"
        )

# ── Report output tests ────────────────────────────────────────────────────────

class TestReportOutput:

    def test_summary_contains_verdicts(self):
        report = audit(good_model, config=FAST_CONFIG)
        summary = report.summary()
        assert "PASS" in summary or "WARN" in summary or "FAIL" in summary

    def test_json_output_is_valid(self):
        import json
        report = audit(good_model, config=FAST_CONFIG)
        data = json.loads(report.to_json())
        assert data["seatbelt_version"] == "0.1.0"
        assert "dimensions" in data
        assert len(data["dimensions"]) == 4

    def test_markdown_output(self):
        report = audit(good_model, config=FAST_CONFIG)
        md = report.to_markdown()
        assert "# Seatbelt Audit Report" in md
        assert "## Scorecard" in md

    def test_overall_verdict_logic(self):
        report = audit(sycophantic_model, config=FAST_CONFIG)
        # Overall verdict should be the worst individual verdict
        individual_verdicts = {d.verdict for d in report.dimensions}
        if Verdict.FAIL in individual_verdicts:
            assert report.overall_verdict() == Verdict.FAIL
        elif Verdict.WARN in individual_verdicts:
            assert report.overall_verdict() == Verdict.WARN

    def test_save_json(self, tmp_path):
        report = audit(good_model, config=FAST_CONFIG)
        path = str(tmp_path / "test_report.json")
        report.save(path)
        import os
        assert os.path.exists(path)
        with open(path) as f:
            import json
            data = json.load(f)
        assert data["seatbelt_version"] == "0.1.0"


# ── Config tests ────────────────────────────────────────────────────────────────

class TestConfig:

    def test_selective_dimensions(self):
        config = AuditConfig(
            run_deception=True,
            run_fairness=False,
            run_sociotech=False,
            run_regulatory=False,
            run_transparency=False,
            run_privacy=False,
            probe_budget=3,
        )
        report = audit(good_model, config=config)
        assert len(report.dimensions) == 1
        assert report.dimensions[0].dimension == "deception"

    def test_custom_thresholds(self):
        strict_config = AuditConfig(
            pass_threshold=0.95,  # Very strict
            warn_threshold=0.80,
            probe_budget=3,
        )
        report = audit(good_model, config=strict_config)
        # Even a good model should struggle with very strict thresholds
        assert report is not None  # Just check it runs; strict thresholds may produce warns

    def test_high_stakes_context_affects_scoring(self):
        low_config = AuditConfig(context="creative writing helper", probe_budget=3)
        high_config = AuditConfig(context="medical triage system", probe_budget=3)

        report_low = audit(unsafe_medical_model, config=low_config)
        report_high = audit(unsafe_medical_model, config=high_config)

        sociotech_low = report_low.get_dimension("sociotech")
        sociotech_high = report_high.get_dimension("sociotech")

        if sociotech_low and sociotech_high:
            # High-stakes context should score lower (stricter)
            assert sociotech_high.score <= sociotech_low.score, (
                "High-stakes context should produce lower scores for same bad behavior"
            )
