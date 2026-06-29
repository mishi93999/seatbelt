# Local outputs (not committed)

Audit runs, validation JSON, and precomputed sensitivity scores stay on your machine.

## Setup

```bash
cp -r local_outputs.example local_outputs
mkdir -p local_outputs/validation local_outputs/colab
```

Then add your files:

| Path | Description |
|------|-------------|
| `local_outputs/validation/seatbelt_validation_results.json` | Full multi-model audit export |
| `local_outputs/sensitivity/adjusted_model_scores.json` | Generated — do not edit by hand |
| `local_outputs/colab/` | Colab / notebook audit exports (`seatbelt_audit.md`, etc.) |

Regenerate sensitivity scores after updating validation JSON or manual overrides:

```bash
python scripts/sensitivity_analysis.py --recompute
```

Override the root directory:

```bash
export SEATBELT_LOCAL_OUTPUTS=/path/to/my/outputs
```

The `local_outputs/` directory is listed in `.gitignore` and must not be pushed to GitHub.
