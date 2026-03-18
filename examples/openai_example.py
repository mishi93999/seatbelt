"""
examples/openai_example.py

Complete example: Audit a GPT-4o model using Seatbelt.

Run:
    pip install seatbelt openai
    export OPENAI_API_KEY=your_key
    python examples/openai_example.py
"""

import os
import openai
from seatbelt import audit, AuditConfig

# ── 1. Define your model_fn ───────────────────────────────────────────────────
# model_fn is how Seatbelt talks to your model.
# It takes one string (the prompt) and returns one string (the response).
# That's it. Seatbelt doesn't care what's inside.

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def my_gpt4o(prompt: str) -> str:
    """Wrap GPT-4o as a simple string-in, string-out function."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,  # deterministic for auditing
    )
    return response.choices[0].message.content


# ── 2. Configure your audit ───────────────────────────────────────────────────
config = AuditConfig(
    # Tell Seatbelt what this model is actually for.
    # This affects risk weighting — "HR screening" is high-stakes,
    # "creative writing helper" is low-stakes.
    context="HR candidate screening tool used in New York City",

    # Stricter thresholds for a high-stakes HR use case
    pass_threshold=0.80,
    warn_threshold=0.65,

    # Which regulations to check against
    regulations=["eu_ai_act", "nyc_ll144", "nist_rmf"],

    # Only run 10 probes per dimension for this quick demo
    probe_budget=10,

    # Print progress to console
    verbose=True,
)

# ── 3. Run the audit ──────────────────────────────────────────────────────────
print("Running Seatbelt audit on GPT-4o...")
report = audit(model_fn=my_gpt4o, config=config)

# ── 4. Look at the results ────────────────────────────────────────────────────

# Quick scorecard — this is what you'd put in your terminal / CI logs
print(report.summary())

# Full details — explanations, dissents, regulatory citations
print(report.details())

# ── 5. Save the report ────────────────────────────────────────────────────────
report.save("gpt4o_hr_audit.json")   # Machine-readable, for CI/CD pipelines
report.save("gpt4o_hr_audit.md")     # Human-readable, for your PR or README

# ── 6. Use the result programmatically ───────────────────────────────────────
if report.has_failures():
    print(f"\n🚨 AUDIT FAILED on: {report.failed_dimensions()}")
    print("Do not deploy. Fix the above issues first.")
    exit(1)
elif report.warned_dimensions():
    print(f"\n⚠️  Warnings on: {report.warned_dimensions()}")
    print("Review warnings before deploying in a high-stakes context.")
else:
    print("\n✅ All dimensions passed. Safe to proceed.")
