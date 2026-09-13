# Fage — Buy or Wait? financial decision agent

For every request in `dataset/requests.csv`, Fage rebuilds the user's cash position, projects a daily
balance for the forecast window, generates every eligible payment plan, simulates each one against the
minimum balance, ranks the safe ones, and writes `output.csv`.

The decision path is deterministic Python (`Decimal` throughout). A vision model is used for one job:
reading the 16 document images whose ledger rows have a blank amount. Messages are parsed by a
deterministic English/Indonesian pattern table. Models never produce decisions — only validated
`Amendment` records.

## Setup

Python 3.11+ (tested on 3.12). No third-party packages are required (stdlib `urllib` for HTTP).

```bash
cp .env.example .env      # then fill GEMINI_API_KEY (and optionally OPENROUTER_API_KEY)
```

`.env` lives at the repository root and is git-ignored. Environment variables that are already set win.

## Run

```bash
python code/main.py                 # full run -> output.csv at repo root (uses cache, calls model only on cache miss)
python code/main.py --offline       # zero network calls; cached image extractions only
python code/main.py --refresh       # ignore the image cache, re-extract all 16 images live, overwrite the cache
python code/main.py --samples       # run the 25 public samples -> code/evaluation/sample_output.csv
python code/evaluation/score.py     # per-field scorecard + confusion matrices + per-request diffs on the samples
python code/evaluation/investigations/sweep.py   # calibration sweep over ambiguous forecast parameters (samples only)
python code/evaluation/usage_report.py   # regenerate evaluation/usage_report.md from the call ledger
```

The run prints validator results; exit code is non-zero if the output violates the contract.

## Layout

```
code/
  main.py                 CLI entry point
  fage/
    loader.py             CSV -> typed records (label columns of samples are never loaded here)
    forecast.py           series detection, projection, amendments, daily balance
    evidence.py           message pattern table, image extraction + validation -> Amendment
    planner.py            candidates, safety simulation, ranking, spending changes, Decision
    narrator.py           explanation templates (no model call)
    validator.py          independent output-contract checks
    providers.py          Gemini / OpenRouter client, .env loader, rate limiter, cache, call ledger
  evaluation/
    score.py extract_images.py usage_report.py test_evidence_boundary.py
    investigations/       indexed hypothesis tests (INDEX.md): sweep, residual analyses, debug tools
    calibration.md        how ambiguous parameters were chosen
    usage_report.md       token usage and cost of the final run
    rejected_amendments.json  evidence the validation layer refused
  cache/                  model responses keyed by sha256(prompt_version + content)
SCHEMA.md SECURITY.md
```

## Shipped image cache (extracted intermediate data)

`code/cache/` holds the raw model responses for the 16 document images whose ledger amount is blank. Each file is keyed
by `sha256(prompt_version + prompt + image bytes)` and contains the provider, model, measured token counts and the
**raw response text**.

**What the cache is not.** It is not a store of answers:
* It holds no request ids, decisions, safe amounts or labels. It only records what a model read off an image.
* Every read goes back through `evidence.validate_image_response`, so a cached response is re-validated on every run.

**Why it ships.** Reviewers can reproduce `output.csv` with `--offline` and no API key.

**How to regenerate it.** `python code/main.py --refresh` ignores the cache, re-extracts every image live and
overwrites the cache. Changing the prompt (`IMAGE_PROMPT_VERSION`) changes the key, so stale entries are never used.

## Calibration record

The 25 public samples were used only to choose between readings the specification leaves open. The record of those
choices, including every rejected hypothesis:
* `code/evaluation/calibration.md`: each parameter or rule, the samples that decided it, sweep tables, and the rejected
  hypotheses.
* `code/evaluation/residuals.md`: why `amount_safe_to_pay` is close but rarely exact, and what the error is (and isn't).
* `code/evaluation/investigations/INDEX.md`: every investigation script, the hypothesis it tested, and the verdict.

## Provider behaviour

* Gemini Flash via Google AI Studio primary (`gemini-3.6-flash`; `gemini-2.5-flash` returns HTTP 404 for new
  keys), OpenRouter (`google/gemini-3.6-flash`) fallback. Override with `GEMINI_MODEL` / `OPENROUTER_MODEL`.
* Temperature 0, output capped at 4,096 tokens. The model is asked for exactly `{"amount", "currency"}`; the raw
  response text is validated by our code (closed keys, JSON number, ≤2 decimals, positive, capped, currency equals the
  bound event's) and rejected outright on any violation. See `SECURITY.md`.
* Messages never go to a model: a deterministic rule table parses them and rejects anything it does not recognise.
* Client-side rate limit per provider (`GEMINI_RPM`, `OPENROUTER_RPM` in `.env`), exponential backoff on
  429/5xx, then fail-over to the next provider. Fail-over is for transport failures only, never for content.
* `python code/evaluation/test_evidence_boundary.py` runs the adversarial boundary tests.
* Every call is appended to `evaluation/call_ledger.jsonl` (provider, model, tokens, latency, cache hit/miss).
