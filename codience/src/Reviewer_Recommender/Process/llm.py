import os
import random
import re
import time
import importlib
from threading import Lock
from google import genai
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq_primary_gemini_fallback").strip().lower()

GEMINI_MODEL_PRIMARY = os.getenv("LLM_MODEL_PRIMARY", "gemini-3.1-flash-lite-preview")
GEMINI_MODEL_FALLBACKS = [m.strip() for m in os.getenv("LLM_MODEL_FALLBACKS", "").split(",") if m.strip()]

GROQ_MODEL_PRIMARY = os.getenv("GROQ_MODEL_PRIMARY", "llama-3.3-70b-versatile")
GROQ_MODEL_FALLBACKS = [m.strip() for m in os.getenv("GROQ_MODEL_FALLBACKS", "").split(",") if m.strip()]

LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_BACKOFF_BASE_SEC = float(os.getenv("LLM_BACKOFF_BASE_SEC", "1.5"))
LLM_BACKOFF_MAX_SEC = float(os.getenv("LLM_BACKOFF_MAX_SEC", "8"))
LLM_MAX_TOTAL_WAIT_SEC = float(os.getenv("LLM_MAX_TOTAL_WAIT_SEC", "20"))
LLM_CIRCUIT_FAIL_THRESHOLD = int(os.getenv("LLM_CIRCUIT_FAIL_THRESHOLD", "4"))
LLM_CIRCUIT_COOLDOWN_SEC = float(os.getenv("LLM_CIRCUIT_COOLDOWN_SEC", "30"))

_clients = {}
_lock = Lock()
_circuit_failures = 0
_circuit_open_until = 0.0


class ProviderConfigurationError(Exception):
    pass


class ProviderUnavailableError(Exception):
    pass


def _parse_model_list(value):
    return [m.strip() for m in value.split(",") if m.strip()]


def _purpose_env_key(purpose):
    suffix = re.sub(r"[^a-zA-Z0-9]+", "_", (purpose or "general")).upper().strip("_")
    if not suffix:
        suffix = "GENERAL"
    return suffix


def _provider_sequence():
    if LLM_PROVIDER in ("groq", "groq_only"):
        return ["groq"]
    if LLM_PROVIDER in ("gemini", "gemini_only"):
        return ["gemini"]
    if LLM_PROVIDER == "gemini_primary_groq_fallback":
        return ["gemini", "groq"]
    if LLM_PROVIDER == "groq_primary_gemini_fallback":
        return ["groq", "gemini"]

    parsed = [p.strip().lower() for p in LLM_PROVIDER.split(",") if p.strip()]
    valid = [p for p in parsed if p in ("groq", "gemini")]
    return valid or ["groq", "gemini"]


def _provider_api_key(provider):
    if provider == "groq":
        return os.getenv("GROQ_API_KEY", "").strip()
    if provider == "gemini":
        return os.getenv("GEMINI_API_KEY", "").strip()
    return ""


def _models_for_provider(purpose, provider, allow_fallback=True):
    suffix = _purpose_env_key(purpose)
    provider_key = f"LLM_MODELS_{provider.upper()}_{suffix}"
    generic_key = f"LLM_MODELS_{suffix}"

    provider_models = _parse_model_list(os.getenv(provider_key, ""))
    if provider_models:
        return list(dict.fromkeys(provider_models))

    generic_models = _parse_model_list(os.getenv(generic_key, ""))
    if generic_models:
        return list(dict.fromkeys(generic_models))

    if provider == "groq":
        models = [GROQ_MODEL_PRIMARY]
        if allow_fallback:
            models.extend(GROQ_MODEL_FALLBACKS)
        return list(dict.fromkeys([m for m in models if m]))

    if provider == "gemini":
        models = [GEMINI_MODEL_PRIMARY]
        if allow_fallback:
            models.extend(GEMINI_MODEL_FALLBACKS)
        return list(dict.fromkeys([m for m in models if m]))

    return []


def _get_provider_client(provider):
    global _clients
    if provider in _clients:
        return _clients[provider]

    api_key = _provider_api_key(provider)
    if not api_key:
        raise ProviderConfigurationError(f"Missing API key for provider={provider}")

    if provider == "gemini":
        _clients[provider] = genai.Client(api_key=api_key)
        return _clients[provider]

    if provider == "groq":
        try:
            groq_module = importlib.import_module("groq")
            Groq = getattr(groq_module, "Groq")
        except Exception as exc:
            raise ProviderUnavailableError(f"Groq SDK unavailable: {exc}")
        _clients[provider] = Groq(api_key=api_key)
        return _clients[provider]

    raise ProviderConfigurationError(f"Unsupported provider={provider}")


def _invoke_model(provider, model_name, prompt):
    client = _get_provider_client(provider)

    if provider == "gemini":
        response = client.models.generate_content(model=model_name, contents=prompt)
        return (response.text or "").strip()

    if provider == "groq":
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        try:
            content = response.choices[0].message.content
            return (content or "").strip()
        except Exception:
            return ""

    raise ProviderConfigurationError(f"Unsupported provider={provider}")


def _is_retryable_error(exc):
    msg = str(exc)
    retry_markers = [
        "429",
        "503",
        "500",
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
        "DEADLINE_EXCEEDED",
        "rate limit",
        "too many requests",
        "internal server error",
        "overloaded",
        "timeout",
        "temporarily unavailable",
    ]
    lowered = msg.lower()
    return any(marker.lower() in lowered for marker in retry_markers)


def _mark_failure_and_maybe_open_circuit():
    global _circuit_failures, _circuit_open_until
    with _lock:
        _circuit_failures += 1
        if _circuit_failures >= LLM_CIRCUIT_FAIL_THRESHOLD:
            _circuit_open_until = time.time() + LLM_CIRCUIT_COOLDOWN_SEC


def _reset_circuit_on_success():
    global _circuit_failures, _circuit_open_until
    with _lock:
        _circuit_failures = 0
        _circuit_open_until = 0.0


def _is_circuit_open():
    return time.time() < _circuit_open_until


def generate_with_resilience(prompt, purpose="general", allow_fallback=True, max_retries=None, model_candidates=None):
    if _is_circuit_open():
        return {
            "ok": False,
            "text": "",
            "reason": "CIRCUIT_OPEN",
            "attempts": 0,
            "model": "",
        }

    retries = LLM_MAX_RETRIES if max_retries is None else max(0, max_retries)
    forced_models = list(dict.fromkeys([m.strip() for m in (model_candidates or []) if str(m).strip()]))
    providers = _provider_sequence()
    start_time = time.time()
    attempts = 0
    last_error = ""

    for attempt_index in range(retries + 1):
        for provider in providers:
            if not _provider_api_key(provider):
                last_error = f"Missing API key for provider={provider}"
                continue

            models = forced_models or _models_for_provider(purpose, provider, allow_fallback=allow_fallback)
            if not models:
                last_error = f"No models configured for provider={provider}, purpose={purpose}"
                continue

            provider_blocked = False
            for model_name in models:
                attempts += 1
                try:
                    text = _invoke_model(provider, model_name, prompt)
                    _reset_circuit_on_success()
                    return {
                        "ok": bool(text),
                        "text": text,
                        "reason": "OK" if text else "EMPTY_RESPONSE",
                        "attempts": attempts,
                        "model": model_name,
                        "provider": provider,
                    }
                except (ProviderConfigurationError, ProviderUnavailableError) as exc:
                    last_error = str(exc)
                    provider_blocked = True
                    continue
                except Exception as exc:
                    last_error = str(exc)
                    if _is_retryable_error(exc):
                        _mark_failure_and_maybe_open_circuit()
                    continue

            if provider_blocked:
                continue

        if attempt_index < retries:
            elapsed = time.time() - start_time
            if elapsed >= LLM_MAX_TOTAL_WAIT_SEC:
                break
            delay = min(LLM_BACKOFF_MAX_SEC, LLM_BACKOFF_BASE_SEC * (2 ** attempt_index))
            delay += random.uniform(0, 0.5)
            remaining_budget = max(0.0, LLM_MAX_TOTAL_WAIT_SEC - elapsed)
            if remaining_budget <= 0:
                break
            time.sleep(min(delay, remaining_budget))

    reason = "RETRY_EXHAUSTED"
    if _is_circuit_open():
        reason = "CIRCUIT_OPEN"
    elif last_error:
        reason = f"RETRY_EXHAUSTED:{last_error}"

    print(f"⚠️ LLM {purpose} failed. reason={reason}, attempts={attempts}")
    return {
        "ok": False,
        "text": "",
        "reason": reason,
        "attempts": attempts,
        "model": "",
        "provider": "",
    }