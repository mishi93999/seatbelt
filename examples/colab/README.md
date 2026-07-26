# Colab examples

## Open LLM audit demo

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yk3Sw7wAUVbBXzVJU5_DHprIPUYTiWIf?usp=sharing)

Run a Seatbelt audit against a hosted open model (default: Groq `llama-3.3-70b-versatile`) and export a markdown report for your GitHub profile or project README.

**Open the hosted demo:** [Colab notebook](https://colab.research.google.com/drive/1yk3Sw7wAUVbBXzVJU5_DHprIPUYTiWIf?usp=sharing)

The same notebook lives in this repo at [`open_llm_audit.ipynb`](./open_llm_audit.ipynb) if you prefer to run it locally or open it from GitHub.

**What you need**

- Free [Groq API key](https://console.groq.com/keys) (store as Colab secret `GROQ_API_KEY`, or paste when prompted)
- ~5–15 minutes on Colab free tier (demo uses `probe_budget=15`)

**What the notebook does**

1. `pip install seatbelt huggingface_hub groq`
2. Build a `model_fn(prompt) -> str` wrapper around Groq
3. Run `audit(model_fn=..., config=AuditConfig(...))`
4. Print probe-level results, then save:

**Outputs** (download from Colab, or `local_outputs/colab/` on a local run — **never commit these**)

- `seatbelt_audit.md` — paste into an About page or docs
- `seatbelt_audit.json` — full structured report
- `seatbelt_about_snippet.json` — compact scores for badges/tables

**Profile README snippet**

Use values from your run’s `seatbelt_about_snippet.json`:

```markdown
## Responsible AI audit

Audited with [Seatbelt](https://github.com/o-rai/seatbelt) · [Open the Colab demo](https://colab.research.google.com/drive/1yk3Sw7wAUVbBXzVJU5_DHprIPUYTiWIf?usp=sharing)

| Model | Overall |
|-------|---------|
| `your-model-id` | PASS / WARN / FAIL (your %) |
```

See [`local_outputs.example/README.md`](../../local_outputs.example/README.md) for where local audit artifacts live in this repo.
