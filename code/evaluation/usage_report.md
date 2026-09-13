# Token usage and cost: final full-dataset run

Run window: ledger rows at or after `2026-09-13T13:20:03` (11 rows); requests in run: 250.

**What is measured and what is estimated.**
* **Model use:** only the 16 document images whose ledger amount is blank. Messages (215) are parsed by deterministic rules and make no model calls. Of the 16 images, 11 belong to evaluation requests.
* **Tokens are measured.** Input and output token counts are the provider-reported usage for the call that produced each response, recorded in `call_ledger.jsonl`. A cached replay reports the tokens of that original call. On OpenRouter, output tokens include the model's internal reasoning tokens.
* **Cost is an estimate:** measured tokens × the published per-token rate stated in the table. It is not an invoice.
* **Tier caveat:** for direct Gemini calls the rate is Google's paid Standard tier, and Google also offers a free tier for this model. The ledger does not record which tier the key used (its HTTP 429 quota errors are consistent with a quota-limited plan), so the Gemini share of the estimate is an upper bound and may be USD 0. OpenRouter calls are billed at OpenRouter's published rate.

| Provider | Model | Live calls | Cache replays | Errors | Input tokens (measured) | Output tokens (measured) | Rate used (USD / 1M in, out) | Estimated cost (USD) |
|---|---|---:|---:|---:|---:|---:|---|---:|
| gemini | gemini-3.6-flash | 0 | 7 | 0 | 9,152 | 2,119 | 0.75, 3.75 (Google Gemini API pricing, paid Standard tier, read 2026-09-13) | 0.0148 |
| openrouter | google/gemini-3.6-flash | 0 | 4 | 0 | 5,513 | 1,784 | 0.75, 3.75 (OpenRouter /api/v1/models pricing, read 2026-09-13) | 0.0108 |
| **all** | | 0 | 11 | 0 | 14,665 | 3,903 | | 0.0256 |

## Totals

* Model requests behind this output: 11
* Tokens (measured): 14,665 input + 3,903 output = 18,568
* Average tokens per request (over 250 requests): 74.3
* Estimated total cost: USD 0.0256
* Estimated cost per request: USD 0.000103

## Provider incidents across the whole session (full ledger)

Ledger span: 2026-09-13T11:07:51 to 2026-09-13T13:20:04. Each row is one failed attempt as recorded, either a call that failed on every provider (`errors`) or a primary failure before a successful fail-over (`fallback_from`; only recorded from 11:37 onward, so fail-overs between 11:31 and 11:34 appear as OpenRouter successes without a stated Gemini reason).

| Provider | HTTP | Message (truncated) | Attempts | First | Last |
|---|---|---|---:|---|---|
| gemini | 400 | HTTP 400 | 16 | 2026-09-13T11:07:51 | 2026-09-13T11:08:13 |
| openrouter | - | no key | 32 | 2026-09-13T11:07:51 | 2026-09-13T11:12:15 |
| gemini | 400 | API key not valid. Please pass a valid API key. | 16 | 2026-09-13T11:11:48 | 2026-09-13T11:12:15 |
| gemini | 404 | This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/ | 16 | 2026-09-13T11:19:57 | 2026-09-13T11:21:50 |
| openrouter | 402 | HTTP 402: {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 65 | 16 | 2026-09-13T11:19:57 | 2026-09-13T11:21:50 |
| gemini | - | bad response: Unterminated string starting at: line 1 column 69 (char 68) | 1 | 2026-09-13T11:23:24 | 2026-09-13T11:23:24 |
| openrouter | - | bad response: Unterminated string starting at: line 1 column 121 (char 120) | 1 | 2026-09-13T11:23:24 | 2026-09-13T11:23:24 |
| gemini | 429 | You exceeded your current quota, please check your plan and billing details. For more informat | 9 | 2026-09-13T12:23:28 | 2026-09-13T12:29:56 |

**Why Gemini failed mid-run.** Three causes, in order:
1. `API key not valid` (HTTP 400) before a key was configured.
2. `models/gemini-2.5-flash is no longer available to new users` (HTTP 404). The default model was changed to `gemini-3.6-flash`, which the key's models endpoint lists.
3. `You exceeded your current quota` (HTTP 429) on every attempt from 12:23 to 12:30, during the closed-schema (`img-v3`) re-extraction. After bounded retries each call failed over to OpenRouter.

Provenance of the responses behind this output (from the ledger, not assumed): gemini: 7, openrouter: 4. Gemini answered the images it reached before its quota ran out; the rest failed over to OpenRouter.

The two OpenRouter failures were self-inflicted and fixed: HTTP 402 because `max_tokens` defaulted above the account's credit (now capped at 4,096), and one response truncated at the earlier 1,024-token cap.
