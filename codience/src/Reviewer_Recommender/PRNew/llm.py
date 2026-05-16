"""
Multi-model LLM router with purpose-based dispatch and rate limiting.

Supported providers (all using OpenAI-compatible API):
  - Groq: High throughput, fast inference
  - Gemini: Large context, good for structured JSON (via Google GenAI)
  - Mistral: 1B tokens/month free, high quota (OpenAI-compatible)
  - Cerebras: Ultra-fast, 30 requests/min (OpenAI-compatible)

Purpose routing:
  pr_file_summary      → Mistral, Cerebras, Groq
  pr_skill_extraction  → Mistral, Groq, Gemini
  candidate_scoring    → Mistral, Groq, Gemini
  history_summary      → Mistral (high volume), Cerebras, Groq
  general              → Mistral, Groq, Gemini
"""

import os
import random
import re
import time
from threading import Lock
from dotenv import load_dotenv

# Import rate limiter
from .llm_rate_limiter import rate_limiter

# Use only openai package for all providers
from openai import OpenAI

load_dotenv()

# ── Provider / model defaults ──────────────────────────────────────────────────

# Groq models (via OpenAI-compatible API)
GROQ_MODELS = {
    "heavy":  os.getenv("GROQ_HEAVY_MODEL",  "llama-3.3-70b-versatile"),
    "light":  os.getenv("GROQ_LIGHT_MODEL",  "llama-3.1-8b-instant"),
    "mid":    os.getenv("GROQ_MID_MODEL",    "llama-3.1-70b-versatile"),
}

# Mistral AI models (via OpenAI-compatible API)
MISTRAL_MODELS = {
    "heavy":   os.getenv("MISTRAL_HEAVY_MODEL",   "mistral-large-latest"),
    "medium":  os.getenv("MISTRAL_MEDIUM_MODEL",  "mistral-small-latest"),
    "light":   os.getenv("MISTRAL_LIGHT_MODEL",   "open-mistral-7b"),
    "code":    os.getenv("MISTRAL_CODE_MODEL",    "codestral-latest"),
}

# Cerebras models (via OpenAI-compatible API)
CEREBRAS_MODELS = {
    "heavy":   os.getenv("CEREBRAS_HEAVY_MODEL",   "qwen3-235b"),
    "medium":  os.getenv("CEREBRAS_MEDIUM_MODEL",  "llama3.1-8b"),
    "light":   os.getenv("CEREBRAS_LIGHT_MODEL",   "gpt-oss-120b"),
}

# Gemini uses native SDK (not OpenAI-compatible)
GEMINI_MODELS = {
    "flash":      os.getenv("GEMINI_FLASH_MODEL",      "gemini-2.5-flash"),  # Changed
    "flash_lite": os.getenv("GEMINI_FLASH_LITE_MODEL", "gemini-3.1-flash-lite"),  # Changed
    "pro":        os.getenv("GEMINI_PRO_MODEL",        "gemini-1.5-pro"),
}
# Provider configurations for OpenAI-compatible clients
PROVIDER_CONFIGS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
    },
}

# Purpose → ordered list of (provider, model_key) to try
PURPOSE_ROUTING: dict[str, list[tuple[str, str]]] = {
    "pr_file_summary":     [("mistral", "light"), ("cerebras", "light"), ("cerebras", "medium")],
    "pr_skill_extraction": [("mistral", "heavy"), ("cerebras", "heavy"), ("gemini", "pro"), ("mistral", "heavy")],
    "candidate_scoring":   [("mistral", "heavy"), ("gemini", "pro"), ("cerebras", "heavy"), ("cerebras", "medium")],
    "history_summary":     [("mistral", "medium"), ("gemini", "pro"), ("cerebras", "heavy"), ("mistral", "heavy")],
    "general":             [("mistral", "heavy"), ("gemini", "pro"), ("cerebras", "heavy"), ("cerebras", "heavy")],
}

# ── Retry / circuit-breaker config ─────────────────────────────────────────────

LLM_MAX_RETRIES           = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_BACKOFF_BASE_SEC      = float(os.getenv("LLM_BACKOFF_BASE_SEC", "2.0"))
LLM_BACKOFF_MAX_SEC       = float(os.getenv("LLM_BACKOFF_MAX_SEC", "30.0"))
LLM_MAX_TOTAL_WAIT_SEC    = float(os.getenv("LLM_MAX_TOTAL_WAIT_SEC", "60.0"))
LLM_CIRCUIT_FAIL_THRESHOLD = int(os.getenv("LLM_CIRCUIT_FAIL_THRESHOLD", "10"))
LLM_CIRCUIT_COOLDOWN_SEC  = float(os.getenv("LLM_CIRCUIT_COOLDOWN_SEC", "60.0"))

# ── Module-level state ─────────────────────────────────────────────────────────

_clients: dict[str, object] = {}
_lock = Lock()
_circuit_failures = 0
_circuit_open_until = 0.0
_gemini_client = None


class ProviderConfigurationError(Exception):
    pass


class ProviderUnavailableError(Exception):
    pass


# ── Circuit breaker ────────────────────────────────────────────────────────────

def _is_circuit_open() -> bool:
    return time.time() < _circuit_open_until


def _mark_failure():
    global _circuit_failures, _circuit_open_until
    with _lock:
        _circuit_failures += 1
        if _circuit_failures >= LLM_CIRCUIT_FAIL_THRESHOLD:
            _circuit_open_until = time.time() + LLM_CIRCUIT_COOLDOWN_SEC
            print(f"🔌 Circuit OPEN for {LLM_CIRCUIT_COOLDOWN_SEC}s")


def _reset_circuit():
    global _circuit_failures, _circuit_open_until
    with _lock:
        _circuit_failures = 0
        _circuit_open_until = 0.0


def _is_retryable(exc: Exception) -> bool:
    markers = ["429", "503", "500", "RESOURCE_EXHAUSTED", "UNAVAILABLE",
               "rate limit", "too many requests", "overloaded", "timeout"]
    msg = str(exc).lower()
    return any(m.lower() in msg for m in markers)


# ── Client cache ───────────────────────────────────────────────────────────────

def _get_client(provider: str):
    """Get or create client for provider"""
    if provider in _clients:
        return _clients[provider]

    # Handle Gemini separately (uses native SDK)
    if provider == "gemini":
        return _get_gemini_client()

    # For OpenAI-compatible providers
    if provider not in PROVIDER_CONFIGS:
        raise ProviderConfigurationError(f"Unsupported provider={provider}")

    config = PROVIDER_CONFIGS[provider]
    api_key = os.getenv(config["api_key_env"])
    
    if not api_key:
        raise ProviderConfigurationError(f"Missing {config['api_key_env']} for provider={provider}")

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=config["base_url"],
            timeout=60.0,
            max_retries=0,  # We handle retries ourselves
        )
        _clients[provider] = client
        return client
    except Exception as exc:
        raise ProviderUnavailableError(f"{provider} client unavailable: {exc}")


def _get_gemini_client():
    """Get Gemini client (native SDK)"""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ProviderConfigurationError("Missing GEMINI_API_KEY")

    try:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except Exception as exc:
        raise ProviderUnavailableError(f"Gemini SDK unavailable: {exc}")


# ── Model invocation ───────────────────────────────────────────────────────────

def _resolve_model_name(provider: str, model_key: str) -> str:
    if provider == "groq":
        return GROQ_MODELS.get(model_key, model_key)
    if provider == "mistral":
        return MISTRAL_MODELS.get(model_key, model_key)
    if provider == "cerebras":
        return CEREBRAS_MODELS.get(model_key, model_key)
    if provider == "gemini":
        return GEMINI_MODELS.get(model_key, model_key)
    return model_key


def _invoke_openai_compatible(provider: str, model_name: str, prompt: str) -> str:
    """Invoke OpenAI-compatible providers (Groq, Mistral, Cerebras)"""
    client = _get_client(provider)
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=4096,
    )
    return (response.choices[0].message.content or "").strip()


def _invoke_gemini(model_name: str, prompt: str) -> str:
    """Invoke Gemini using native SDK"""
    client = _get_gemini_client()
    response = client.models.generate_content(model=model_name, contents=prompt)
    return (response.text or "").strip()


def _invoke(provider: str, model_name: str, prompt: str, purpose: str) -> str:
    """Invoke model with rate limiting"""
    
    # Apply rate limiting before making the call
    if not rate_limiter.acquire(provider, purpose):
        raise Exception(f"Rate limit exceeded for {provider} (purpose: {purpose})")
    
    if provider == "gemini":
        return _invoke_gemini(model_name, prompt)
    else:
        return _invoke_openai_compatible(provider, model_name, prompt)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_with_resilience(
    prompt: str,
    purpose: str = "general",
    max_retries: int | None = None,
) -> dict:
    """
    Routes the prompt to the appropriate model(s) based on `purpose`,
    retries on transient errors, and returns a result dict.
    """
    if _is_circuit_open():
        return {"ok": False, "text": "", "reason": "CIRCUIT_OPEN", "attempts": 0, "model": "", "provider": ""}

    retries   = LLM_MAX_RETRIES if max_retries is None else max(0, max_retries)
    route     = PURPOSE_ROUTING.get(purpose, PURPOSE_ROUTING["general"])
    start     = time.time()
    attempts  = 0
    last_err  = ""

    for attempt_idx in range(retries + 1):
        for provider, model_key in route:
            # Check API key for OpenAI-compatible providers
            if provider in PROVIDER_CONFIGS:
                api_key_env = PROVIDER_CONFIGS[provider]["api_key_env"]
                if not os.getenv(api_key_env):
                    last_err = f"No API key for {provider} (missing {api_key_env})"
                    continue
            elif provider == "gemini":
                if not os.getenv("GEMINI_API_KEY"):
                    last_err = "No API key for gemini (missing GEMINI_API_KEY)"
                    continue

            model_name = _resolve_model_name(provider, model_key)
            attempts += 1

            try:
                text = _invoke(provider, model_name, prompt, purpose)
                _reset_circuit()
                return {
                    "ok": bool(text),
                    "text": text,
                    "reason": "OK" if text else "EMPTY_RESPONSE",
                    "attempts": attempts,
                    "model": model_name,
                    "provider": provider,
                }
            except (ProviderConfigurationError, ProviderUnavailableError) as exc:
                last_err = str(exc)
                print(f"⚠️ Provider {provider} unavailable: {exc}")
                continue
            except Exception as exc:
                last_err = str(exc)
                if _is_retryable(exc):
                    _mark_failure()
                    print(f"⚠️ Retryable error on {provider}/{model_key}: {exc}")
                continue

        # Back-off between full route sweeps
        if attempt_idx < retries:
            elapsed = time.time() - start
            if elapsed >= LLM_MAX_TOTAL_WAIT_SEC:
                break
            delay = min(LLM_BACKOFF_MAX_SEC, LLM_BACKOFF_BASE_SEC * (2 ** attempt_idx))
            delay += random.uniform(0, 0.5)
            budget = max(0.0, LLM_MAX_TOTAL_WAIT_SEC - elapsed)
            time.sleep(min(delay, budget))

    reason = "CIRCUIT_OPEN" if _is_circuit_open() else f"RETRY_EXHAUSTED:{last_err}"
    print(f"⚠️  LLM [{purpose}] failed after {attempts} attempts. reason={reason}")
    return {"ok": False, "text": "", "reason": reason, "attempts": attempts, "model": "", "provider": ""}


def get_rate_limiter_stats():
    """Get rate limiter statistics"""
    return rate_limiter.get_stats()


def print_rate_limiter_stats():
    """Print rate limiter statistics"""
    rate_limiter.print_stats()