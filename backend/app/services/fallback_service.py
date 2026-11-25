from typing import Any, Dict, Iterable, List, Tuple


def parse_failure_header(header: str, key_ids: Iterable[str]) -> Dict[str, int]:
    if not header:
        return {}

    ids = list(key_ids)
    failures: Dict[str, int] = {}
    for item in header.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key_id, status_text = item.split("=", 1)
        key_id = key_id.strip()
        status_text = status_text.strip()
        if status_text not in {"429", "500", "502", "503"}:
            continue
        status = int(status_text)
        if key_id == "*":
            for candidate in ids:
                failures[candidate] = status
        elif key_id in ids:
            failures[key_id] = status
    return failures


def status_code(error: BaseException) -> int | None:
    for name in ("status_code", "http_status"):
        value = getattr(error, name, None)
        if isinstance(value, int):
            return value
    return None


def is_retryable(error: BaseException) -> bool:
    code = status_code(error)
    if code in {429, 500, 502, 503}:
        return True
    message = str(error).lower()
    return "quota" in message or "rate limit" in message or "429" in message or "5" in message[:1]
