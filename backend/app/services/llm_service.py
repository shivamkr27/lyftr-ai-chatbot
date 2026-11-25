import time
import logging
from typing import Dict, List, Optional, Tuple

import litellm

logger = logging.getLogger(__name__)


def _usage(response: object) -> Tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage:
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        if isinstance(prompt, int) and isinstance(completion, int):
            return prompt, completion
        if isinstance(usage, dict):
            return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
    return 0, 0


def _cache_hit(response: object) -> bool:
    hidden = getattr(response, "_hidden_params", None)
    if isinstance(hidden, dict) and hidden.get("cache_hit"):
        return True
    hidden = getattr(response, "hidden_params", None)
    if isinstance(hidden, dict) and hidden.get("cache_hit"):
        return True
    return False


def completion(
    model: str,
    messages: List[Dict[str, str]],
    api_keys: List[str],
    key_ids: List[str],
    simulated_failures: Dict[str, int],
    cache_enabled: bool,
) -> Dict[str, object]:
    started = time.perf_counter()
    retry_count = 0

    for key_id, api_key in zip(key_ids, api_keys):
        if key_id in simulated_failures:
            retry_count += 1
            continue

        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "api_key": api_key,
                "temperature": 0.2,
                "timeout": 60,
            }
            if cache_enabled and not simulated_failures:
                kwargs["cache"] = True

            response = litellm.completion(**kwargs)
            elapsed = int((time.perf_counter() - started) * 1000)
            input_tokens, output_tokens = _usage(response)
            if input_tokens == 0:
                input_tokens = litellm.token_counter(model=model, messages=messages)
            if output_tokens == 0:
                text = str(response.choices[0].message.content or "")
                output_tokens = litellm.token_counter(model=model, text=text)

            cache_hit = _cache_hit(response)
            return {
                "reply": str(response.choices[0].message.content or "").strip(),
                "resolution_source": "LLM_CACHE" if cache_hit else "LIVE_INFERENCE",
                "model": model,
                "latency_ms": elapsed,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "key_id": None if cache_hit else key_id,
                "fallback_attempts": 0 if cache_hit else retry_count,
            }
        except Exception as error:
            logger.warning(
                "LLM provider request failed for %s (%s)",
                key_id,
                type(error).__name__,
            )
            retry_count += 1
            continue

    raise ProviderUnavailable()


class ProviderUnavailable(Exception):
    pass
