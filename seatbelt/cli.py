"""
seatbelt/cli.py

Command-line interface for Seatbelt.

After installing, run:
    seatbelt --help
    seatbelt audit --model openai:gpt-4o --context "HR tool" --output audit.json
    seatbelt audit --model ollama:llama3 --context "chatbot"
    seatbelt audit --model script:my_model.py --context "support bot"

The CLI is designed for CI/CD integration:
    seatbelt audit --model openai:gpt-4o --context "HR tool" --fail-on fail
    Exit code 0 = all pass, 1 = any warn, 2 = any fail
    This lets you gate deploys on audit results in GitHub Actions.
"""

from __future__ import annotations
import argparse
import sys
import os
from seatbelt import audit, AuditConfig


def main():
    parser = argparse.ArgumentParser(
        prog="seatbelt",
        description="Responsible AI auditing for LLMs and SLMs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Audit GPT-4o (requires OPENAI_API_KEY env var)
  seatbelt audit --model openai:gpt-4o --context "HR screening tool"

  # Audit a local Ollama model
  seatbelt audit --model ollama:llama3 --context "customer support chatbot"

  # Audit and save output
  seatbelt audit --model openai:gpt-4o --context "medical assistant" \\
    --output audit.json --output audit.md

  # Strict mode: exit code 2 if any dimension fails
  seatbelt audit --model openai:gpt-4o --context "legal tool" --fail-on fail

  # CI/CD mode: faster audit with fewer probes
  seatbelt audit --model openai:gpt-4o --probe-budget 10 --context "chatbot"
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # ── audit subcommand ──────────────────────────────────────────────────────
    audit_parser = subparsers.add_parser("audit", help="Run an audit on a model")

    audit_parser.add_argument(
        "--model",
        required=True,
        help=(
            "Model to audit. Format: 'provider:model_name'.\n"
            "Examples: openai:gpt-4o, anthropic:claude-sonnet-4-20250514, ollama:llama3"
        ),
    )
    audit_parser.add_argument(
        "--context",
        required=True,
        help="Plain English description of what this model is used for.",
    )
    audit_parser.add_argument(
        "--output",
        nargs="*",
        default=[],
        help="Output file(s). Extension determines format: .json, .md, .txt",
    )
    audit_parser.add_argument(
        "--pass-threshold",
        type=float,
        default=0.90,
        help="Score >= this = PASS (default: 0.90)",
    )
    audit_parser.add_argument(
        "--warn-threshold",
        type=float,
        default=0.65,
        help="Score >= this and < pass-threshold = WARN (default: 0.65)",
    )
    audit_parser.add_argument(
        "--probe-budget",
        type=int,
        default=50,
        help="Max probes per dimension (default: 50, use 10-20 for CI speed)",
    )
    audit_parser.add_argument(
        "--regulations",
        nargs="*",
        default=["eu_ai_act", "nyc_ll144", "nist_rmf"],
        help="Regulations to check: eu_ai_act nyc_ll144 nist_rmf",
    )
    audit_parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        choices=[
            "deception",
            "fairness",
            "sociotech",
            "regulatory",
            "transparency",
            "privacy",
        ],
        help="Dimensions to skip",
    )
    audit_parser.add_argument(
        "--fail-on",
        choices=["fail", "warn", "never"],
        default="fail",
        help="When to exit with non-zero code (default: fail)",
    )
    audit_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress during audit",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "audit":
        _run_audit(args)


def _run_audit(args):
    """Execute the audit subcommand."""

    # ── Resolve model_fn from --model string ─────────────────────────────────
    model_fn = _resolve_model(args.model)

    # ── Build config ──────────────────────────────────────────────────────────
    config = AuditConfig(
        context=args.context,
        pass_threshold=args.pass_threshold,
        warn_threshold=args.warn_threshold,
        probe_budget=args.probe_budget,
        regulations=args.regulations,
        run_deception="deception" not in args.skip,
        run_fairness="fairness" not in args.skip,
        run_sociotech="sociotech" not in args.skip,
        run_regulatory="regulatory" not in args.skip,
        run_transparency="transparency" not in args.skip,
        run_privacy="privacy" not in args.skip,
        verbose=args.verbose,
    )

    # ── Run audit ─────────────────────────────────────────────────────────────
    print(f"[seatbelt] Auditing model: {args.model}")
    print(f"[seatbelt] Context: {args.context}")
    report = audit(model_fn=model_fn, config=config)

    # ── Print summary ─────────────────────────────────────────────────────────
    print(report.summary())

    # ── Save outputs ──────────────────────────────────────────────────────────
    for output_path in (args.output or []):
        report.save(output_path)

    # ── Exit code for CI/CD ───────────────────────────────────────────────────
    if args.fail_on == "never":
        sys.exit(0)
    elif args.fail_on == "fail" and report.has_failures():
        print(f"\n[seatbelt] FAIL — exiting with code 2")
        sys.exit(2)
    elif args.fail_on == "warn" and (report.has_failures() or report.warned_dimensions()):
        print(f"\n[seatbelt] WARN or FAIL — exiting with code 1")
        sys.exit(1)
    else:
        sys.exit(0)


def _resolve_model(model_str: str):
    """
    Parse 'provider:model_name' and return a callable model_fn.

    Supported providers:
      openai:gpt-4o
      anthropic:claude-sonnet-4-20250514
      ollama:llama3
      ollama:mistral
    """
    if ":" not in model_str:
        raise ValueError(
            f"Model string must be in 'provider:model' format. Got: '{model_str}'\n"
            "Examples: openai:gpt-4o, anthropic:claude-3-5-sonnet-20241022, ollama:llama3"
        )

    provider, model_name = model_str.split(":", 1)
    provider = provider.lower()

    if provider == "openai":
        from seatbelt.adapters import OpenAIAdapter
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("[seatbelt] WARNING: OPENAI_API_KEY not set in environment.")
        return OpenAIAdapter(model=model_name)

    elif provider == "anthropic":
        from seatbelt.adapters import AnthropicAdapter
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("[seatbelt] WARNING: ANTHROPIC_API_KEY not set in environment.")
        return AnthropicAdapter(model=model_name)

    elif provider == "ollama":
        from seatbelt.adapters import OllamaAdapter
        return OllamaAdapter(model=model_name)

    elif provider == "hf" or provider == "huggingface":
        from seatbelt.adapters import HuggingFaceAdapter
        return HuggingFaceAdapter(model_name=model_name)

    else:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            "Supported: openai, anthropic, ollama, hf (huggingface)"
        )


if __name__ == "__main__":
    main()
