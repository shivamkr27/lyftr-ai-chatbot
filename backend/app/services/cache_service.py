import litellm
from litellm.caching.caching import Cache


def configure_cache(enabled: bool) -> None:
    if not enabled:
        litellm.cache = None
        return
    litellm.cache = Cache(type="local")
