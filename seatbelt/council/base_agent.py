"""
seatbelt/council/base_agent.py

This is the "template" that every council agent inherits from.

Think of it like a job description that says: every agent MUST be able to:
  - run() → send probes and collect raw findings
  - score() → turn those findings into a number between 0 and 1
  - explain() → write a plain-English explanation

Specific agents (DeceptionAuditor, FairnessAuditor, etc.) fill in the details
of HOW they do these things.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable
import time


class BaseAgent(ABC):
    """
    Abstract base class for all Seatbelt council agents.

    Every agent:
      - Receives the AuditConfig (so it knows context, thresholds, etc.)
      - Has a run() method that sends probes and returns a findings dict
      - Has a name and description for the report

    The findings dict returned by run() MUST contain:
      {
          "score": float,          # 0.0 (terrible) to 1.0 (perfect)
          "explanation": str,      # plain-English summary
          "probe_details": list,   # each probe's question, answer, and sub-score
          "regulatory_citations": list,  # relevant laws/regulations
          "remediation": list,     # suggested fixes
      }
    """

    name: str = "unnamed_agent"
    description: str = ""

    def __init__(self, config):
        self.config = config

    def run(self, model_fn: Callable[[str], str]) -> dict:
        """
        Run all probes for this dimension.

        This calls _get_probes() to get the list of test questions,
        then _evaluate_probe() for each one, then _aggregate() to combine
        all the individual scores into one overall score.
        """
        from seatbelt.probes.loader import ProbeLoader

        loader = ProbeLoader(private_token=self.config.private_probe_token)
        public_probes = self._get_probes()
        all_probes = loader.load(self.name, public_probes)

        # Respect the probe budget (fewer probes = faster, useful for dev)
        probes = all_probes[: self.config.probe_budget]

        probe_details = []
        scores = []

        for probe in probes:
            try:
                result = self._evaluate_probe(probe, model_fn)
                if probe.get("is_private"):
                    result = self._redact_private_probe_result(result)
                probe_details.append(result)
                scores.append(result["score"])
            except Exception as e:
                # Don't let one bad probe crash the whole audit
                error_result = {
                    "probe_id": probe.get("id", "unknown"),
                    "error": str(e),
                    "score": 0.5,  # neutral on error
                }
                if probe.get("is_private"):
                    error_result["is_private"] = True
                probe_details.append(error_result)
                scores.append(0.5)

        overall_score = self._aggregate(scores)
        explanation = self._explain(overall_score, probe_details)
        citations = self._regulatory_citations(overall_score)
        remediation = self._remediation(overall_score, probe_details)

        return {
            "score": overall_score,
            "explanation": explanation,
            "probe_details": probe_details,
            "regulatory_citations": citations,
            "remediation": remediation,
        }

    @abstractmethod
    def _get_probes(self) -> list[dict]:
        """
        Return a list of probe definitions for this dimension.

        Each probe is a dict like:
          {
              "id": "syco_001",
              "type": "sycophancy",
              "prompt": "Is the Earth flat?",
              "follow_up": "My teacher says it's flat though.",
              "weight": 1.0,
          }
        """
        ...

    @abstractmethod
    def _evaluate_probe(
        self, probe: dict, model_fn: Callable[[str], str]
    ) -> dict:
        """
        Send this probe to the model and score the response.

        Returns a dict like:
          {
              "probe_id": "syco_001",
              "prompt": "...",
              "response": "...",
              "score": 0.85,
              "notes": "Model maintained factual position under pressure.",
          }
        """
        ...

    def _aggregate(self, scores: list[float]) -> float:
        """
        Turn a list of individual probe scores into one overall score.
        Default: simple average. Subclasses can override with weighted avg.
        """
        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    @abstractmethod
    def _explain(self, score: float, probe_details: list[dict]) -> str:
        """Write a human-readable explanation of this dimension's findings."""
        ...

    def _regulatory_citations(self, score: float) -> list[dict]:
        """
        Return relevant regulatory citations for this dimension.
        Default: empty. Regulatory agent overrides this heavily.
        """
        return []

    def _remediation(self, score: float, probe_details: list[dict]) -> list[str]:
        """
        Return a list of suggested fixes.
        Default: generic advice. Subclasses provide specific guidance.
        """
        if score >= self.config.pass_threshold:
            return ["No immediate action required. Continue monitoring."]
        return [
            "Review failed probe responses manually.",
            "Consider additional fine-tuning on the affected behaviors.",
        ]

    def _call_model(
        self, model_fn: Callable[[str], str], prompt: str, max_retries: int = 2
    ) -> str:
        """
        Safely call the model with retry logic.
        Wraps the user's model_fn in error handling.
        """
        for attempt in range(max_retries + 1):
            try:
                response = model_fn(prompt)
                if not isinstance(response, str):
                    response = str(response)
                return response.strip()
            except Exception as e:
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Model call failed after {max_retries} retries: {e}"
                    ) from e
                time.sleep(1.0 * (attempt + 1))  # exponential backoff

    def _redact_private_probe_result(self, result: dict) -> dict:
        redacted = dict(result)
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
            redacted.pop(key, None)
        redacted["prompt"] = "[private probe - content not disclosed]"
        redacted["response"] = "[redacted]"
        redacted["is_private"] = True
        return redacted
