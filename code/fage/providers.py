"""Thin model-provider layer: Gemini (primary) and OpenRouter (fallback), stdlib HTTP only.

Every call is appended to a JSONL ledger (provider, model, tokens, latency, cache hit) that
evaluation/usage_report.py turns into evaluation/usage_report.md. Responses are cached on
sha256(prompt_version + content) so re-runs cost nothing, and --offline never touches the network.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

# Model names and prices are configuration. gemini-2.5-flash is closed to new API keys (HTTP 404), so the
# default is the Flash model the key lists. Prices are an assumption (2.5 Flash list price) unless overridden.
REGISTRY = {
    # Published paid-tier (Standard) rate from https://ai.google.dev/gemini-api/docs/pricing, read 2026-09-13:
    # input $0.75 / 1M, output incl. thinking $3.75 / 1M, valid through 2026-12-31 ($1.50 / $7.50 from 2027-01-01).
    # A free tier also exists; which tier the key used is not recorded, so cost at this rate is an upper bound.
    "gemini": {"model_env": "GEMINI_MODEL", "model": "gemini-3.6-flash", "price_in_per_m": 0.75, "price_out_per_m": 3.75,
               "price_source": "Google Gemini API pricing, paid Standard tier, read 2026-09-13"},
    # Published rate from OpenRouter's public models endpoint (https://openrouter.ai/api/v1/models), read 2026-09-13:
    # prompt $0.00000075/token, completion (incl. internal reasoning) $0.00000375/token.
    "openrouter": {"model_env": "OPENROUTER_MODEL", "model": "google/gemini-3.6-flash", "price_in_per_m": 0.75,
                   "price_out_per_m": 3.75, "price_source": "OpenRouter /api/v1/models pricing, read 2026-09-13"},
}
MAX_OUTPUT_TOKENS = 4096  # 3.x Flash counts reasoning tokens here; 1024 truncated JSON on one image


def configure_registry() -> None:
    for name, reg in REGISTRY.items():
        reg["model"] = os.environ.get(reg["model_env"], reg["model"])
        for key, env in (("price_in_per_m", f"{name.upper()}_PRICE_IN_PER_M"), ("price_out_per_m", f"{name.upper()}_PRICE_OUT_PER_M")):
            if os.environ.get(env):
                reg[key] = float(os.environ[env])
                reg["price_source"] = f"environment override ({env})"


def load_dotenv(path: Path) -> None:
    """Minimal .env reader: KEY=VALUE lines; existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and not os.environ.get(k):
            os.environ[k] = v


class RateLimiter:
    """Spaces calls so a provider never sees more than `rpm` requests per minute from this process."""

    def __init__(self, rpm: float):
        self.interval = 60.0 / max(rpm, 0.1)
        self.next_at = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        if now < self.next_at:
            time.sleep(self.next_at - now)
        self.next_at = max(now, self.next_at) + self.interval


def _env_key(*names: str) -> str | None:
    for n in names:
        for k, v in os.environ.items():
            if k.upper() == n.upper() and v.strip():
                return v.strip()
    return None


class ProviderError(RuntimeError):
    pass


class ModelClient:
    def __init__(self, cache_dir: Path, ledger_path: Path, offline: bool = False, refresh: bool = False):
        if offline and refresh:
            raise ValueError("offline and refresh are mutually exclusive")
        self.refresh = refresh  # ignore cached responses, call the model again and overwrite the cache
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        configure_registry()
        self.limiters = {
            "gemini": RateLimiter(float(os.environ.get("GEMINI_RPM", "8"))),
            "openrouter": RateLimiter(float(os.environ.get("OPENROUTER_RPM", "15"))),
        }

    # ------------------------------------------------------------------ public
    def structured_call(self, purpose: str, prompt_version: str, text: str, schema: dict,
                        image_path: Path | None = None) -> str | None:
        """Return the model's raw response text, unparsed. Validation belongs to the caller.

        Fail-over to the next provider happens only on transport failure (HTTP error, missing key, empty response),
        never because the content looked wrong, so a bad answer cannot be replaced by shopping for a better one.
        """
        image_bytes = image_path.read_bytes() if image_path else b""
        key = hashlib.sha256(prompt_version.encode() + text.encode() + image_bytes).hexdigest()
        cached = self.cache_dir / f"{key}.json"
        if cached.exists() and not self.refresh:
            data = json.loads(cached.read_text(encoding="utf-8"))
            self._ledger({"purpose": purpose, "provider": data.get("provider"), "model": data.get("model"),
                          "input_tokens": 0, "output_tokens": 0, "latency_ms": 0, "cache": "hit",
                          "orig_input_tokens": data.get("input_tokens", 0), "orig_output_tokens": data.get("output_tokens", 0)})
            return data.get("raw")
        if self.offline:
            return None
        errors = []
        for provider in ("gemini", "openrouter"):
            try:
                result, usage, latency = self._call(provider, text, schema, image_bytes)
            except ProviderError as e:
                errors.append(f"{provider}: {e}")
                continue
            record = {"provider": provider, "model": REGISTRY[provider]["model"], "raw": result, **usage}
            cached.write_text(json.dumps(record, indent=1), encoding="utf-8")
            self._ledger({"purpose": purpose, "provider": provider, "model": REGISTRY[provider]["model"],
                          "latency_ms": latency, "cache": "miss", "fallback_from": [e[:160] for e in errors], **usage})
            return result
        self._ledger({"purpose": purpose, "provider": None, "model": None, "cache": "error", "errors": errors,
                      "input_tokens": 0, "output_tokens": 0})
        return None

    # ----------------------------------------------------------------- private
    def _ledger(self, rec: dict) -> None:
        rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def _call(self, provider: str, text: str, schema: dict, image_bytes: bytes):
        if provider == "gemini":
            api_key = _env_key("GEMINI_API_KEY", "GEMINI API", "GOOGLE_API_KEY")
            if not api_key:
                raise ProviderError("no key")
            self.limiters["gemini"].wait()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{REGISTRY['gemini']['model']}:generateContent"
            parts = [{"text": text}]
            if image_bytes:
                parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(image_bytes).decode()}})
            gen = {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema,
                   "maxOutputTokens": MAX_OUTPUT_TOKENS}
            if "2.5" in REGISTRY["gemini"]["model"]:
                gen["thinkingConfig"] = {"thinkingBudget": 0}
            body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": gen}
            headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
            data, latency = self._post(url, body, headers)
            try:
                parts = data["candidates"][0]["content"]["parts"]
                out = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                meta = data.get("usageMetadata", {})
                usage = {"input_tokens": meta.get("promptTokenCount", 0),
                         "output_tokens": meta.get("candidatesTokenCount", 0) + meta.get("thoughtsTokenCount", 0)}
            except (KeyError, IndexError, TypeError) as e:
                raise ProviderError(f"malformed envelope: {e}")
            if not out:
                raise ProviderError("empty response")
            return out, usage, latency
        api_key = _env_key("OPENROUTER_API_KEY")
        if not api_key:
            raise ProviderError("no key")
        self.limiters["openrouter"].wait()
        content = [{"type": "text", "text": text + "\nRespond with JSON matching this schema: " + json.dumps(schema)}]
        if image_bytes:
            content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image_bytes).decode()}})
        body = {"model": REGISTRY["openrouter"]["model"], "temperature": 0, "response_format": {"type": "json_object"},
                "max_tokens": MAX_OUTPUT_TOKENS,
                "messages": [{"role": "user", "content": content}]}
        data, latency = self._post("https://openrouter.ai/api/v1/chat/completions", body,
                                   {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
        try:
            usage = {"input_tokens": data["usage"]["prompt_tokens"], "output_tokens": data["usage"]["completion_tokens"]}
            out = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"malformed envelope: {e}")
        if not out:
            raise ProviderError("empty response")
        return out, usage, latency

    def _post(self, url: str, body: dict, headers: dict):
        payload = json.dumps(body).encode()
        delay = 2.0
        for attempt in range(5):
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    return json.loads(resp.read()), int((time.time() - t0) * 1000)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < 4:
                    time.sleep(delay)
                    delay *= 2
                    continue
                detail = e.read()[:300].decode("utf-8", "replace")
                raise ProviderError(f"HTTP {e.code}: {detail}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 4:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise ProviderError(str(e))
        raise ProviderError("retries exhausted")
