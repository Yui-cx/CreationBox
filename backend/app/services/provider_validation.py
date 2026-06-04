import httpx
from app.services.provider_types import ProviderConfig, ProviderError


async def validate_provider_config(config: ProviderConfig, timeout_seconds: int) -> None:
    if not config.api_key:
        raise ProviderError("AI_PROVIDER_NOT_CONFIGURED", "AI provider key is not configured.")
    payload = {
        "model": config.model,
        "stream": False,
        "messages": [
            {"role": "system", "content": "你是 CreationBox 的模型连通性检查助手。"},
            {"role": "user", "content": "请只回复 ok。"},
        ],
        "max_tokens": 4,
        **config.extra_body,
    }
    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        **config.extra_headers,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise ProviderError("AI_PROVIDER_TIMEOUT", "模型服务响应超时，请稍后重试。") from exc
    if response.status_code == 429:
        raise ProviderError("AI_PROVIDER_RATE_LIMIT", "模型服务限流，请稍后重试。")
    if response.status_code >= 400:
        raise ProviderError("AI_PROVIDER_ERROR", f"模型服务返回 {response.status_code}。")
