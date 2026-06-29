# Maintainer scripts

Utilities that are **not** part of the published `seatbelt` package.

## Threshold sensitivity analysis

Paper / validation workflow — sweeps PASS/WARN thresholds on locally stored audit results.

```bash
cp -r local_outputs.example local_outputs   # first time only
python scripts/sensitivity_analysis.py --recompute
```

See [`local_outputs.example/README.md`](../local_outputs.example/README.md).
