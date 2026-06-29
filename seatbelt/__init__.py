"""
Seatbelt — Responsible AI auditing for LLMs and SLMs.

Usage:
    from seatbelt import audit

    report = audit(
        model_fn=my_llm,
        context="customer support chatbot",
    )
    print(report.summary())
    report.save("audit_report.json")
"""

from seatbelt.core import audit, AuditConfig
from seatbelt.scoring.report import AuditReport
from seatbelt._version import __version__

__all__ = ["audit", "AuditConfig", "AuditReport", "__version__"]
