import asyncio
import json
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
import httpx
from app.core.config import Settings, get_settings
from app.schemas.generation import GenerationRequest
from app.services.model_config import get_database_model_selection, resolve_provider_config
from app.services.prompts import (
    SKILL_PROMPT_FILES,
    build_prompt,
    build_system_prompt,
    load_humanizer_zh_system_prompt,
    load_skill_prompt,
)
from app.services.provider_types import ProviderConfig, ProviderError

class AIProvider(ABC):
    name = "base"
    model = "unknown"

    @abstractmethod
    async def stream_text(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        raise NotImplementedError

class MockAIProvider(AIProvider):
    name = "mock"
    model = "creationbox-mock"

    async def stream_text(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        chunks = self._mock_output(request)
        for chunk in chunks:
            await asyncio.sleep(0.08)
            yield chunk

    def _mock_output(self, request: GenerationRequest) -> list[str]:
        if request.tool_type in {"humanize", "aigc_reduce"}:
            source = (request.input_text or "").strip()
            if source:
                body = self._mock_humanize(source)
            else:
                body = (
                "最近这段时间，很多品牌都会遇到同一个问题：用户不是不感兴趣，而是很难被一句标准化的卖点真正打动。\n\n"
                "如果想让公众号内容更有转化空间，重点不只是把信息写完整，而是把用户正在犹豫的地方说清楚。"
                "先用真实场景拉近距离，再用清楚的结构交代方法，最后给出一个容易行动的小建议。"
                )
        else:
            topic = request.topic or "参考链接中的核心话题"
            body = (
                f"## 文章标题\n\n为什么说，{topic}不是一次发布任务，而是一套持续经营动作？\n\n"
                "## 文章正文\n\n很多内容团队在做公众号时，会把重点放在今天发什么。但真正影响结果的，往往不是单篇文章的灵感，而是它能不能服务一个清楚的经营目标。\n\n"
                "文章开头需要先把场景讲明白：用户为什么会遇到这个问题？如果不处理，会带来什么影响？接下来，再把解决方法拆成三个动作。\n\n"
                "## 结尾行动建议\n\n可以在文末引导读者回复关键词领取选题模板，或预约一次内容诊断。\n\n"
                "## 编辑洞察\n\n- 首段建立问题场景，降低理解成本。\n- 正文按经营目标推进，避免泛泛而谈。\n"
            )
        return [body[i : i + 80] for i in range(0, len(body), 80)]

    def _mock_humanize(self, source: str) -> str:
        replacements = {
            "系统化的方法": "更清楚的方法",
            "提升用户粘性": "让用户更愿意留下来",
            "长期运营": "持续经营",
            "稳定的复购机制": "更稳定的复购习惯",
            "进行分析": "拆开来看",
            "帮助商家建立": "帮助商家慢慢搭起",
            "持续性的增长路径": "更可持续的增长路径",
        }
        optimized_lines: list[str] = []
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped:
                optimized_lines.append("")
                continue
            prefix = ""
            content = line
            for marker in ("# ", "## ", "### ", "- ", "* "):
                if stripped.startswith(marker):
                    leading = line[: len(line) - len(line.lstrip())]
                    prefix = leading + marker
                    content = stripped[len(marker):]
                    break
            if not prefix:
                match = re.match(r"^(\s*\d+\.\s+)(.+)$", line)
                if match:
                    prefix = match.group(1)
                    content = match.group(2)
            for old, new in replacements.items():
                content = content.replace(old, new)
            if content == stripped and len(content) > 28:
                content = content.replace("，", "，也可以更具体地说，", 1)
            optimized_lines.append(prefix + content)
        return "\n".join(optimized_lines)

class OpenAICompatibleProvider(AIProvider):
    def __init__(self, config: ProviderConfig, timeout_seconds: int):
        self.config = config
        self.name = config.name
        self.model = config.model
        self.timeout_seconds = timeout_seconds

    async def stream_text(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        if not self.config.api_key:
            raise ProviderError("AI_PROVIDER_NOT_CONFIGURED", "AI provider key is not configured.")
        payload = {
            "model": self.config.model,
            "stream": True,
            "messages": [
                {"role": "system", "content": build_system_prompt(request)},
                {"role": "user", "content": build_prompt(request)},
            ],
            **self.config.extra_body,
        }
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            **self.config.extra_headers,
        }
        timeout = httpx.Timeout(self.timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code == 429:
                        raise ProviderError("AI_PROVIDER_RATE_LIMIT", "模型服务限流，请稍后重试。")
                    if response.status_code >= 400:
                        raise ProviderError("AI_PROVIDER_ERROR", f"模型服务返回 {response.status_code}。")
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line.removeprefix("data: ").strip()
                        if data == "[DONE]":
                            break
                        event = json.loads(data)
                        choices = event.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {}).get("content")
                        if delta:
                            yield delta
        except httpx.TimeoutException as exc:
            raise ProviderError("AI_PROVIDER_TIMEOUT", "模型服务响应超时，请稍后重试。") from exc

def build_ai_provider(settings: Settings, provider_override: str | None = None, model_override: str | None = None) -> AIProvider:
    config = resolve_provider_config(settings, provider_override, model_override)
    if config is None or not config.api_key:
        return MockAIProvider()
    return OpenAICompatibleProvider(config, settings.ai_timeout_seconds)

def get_ai_provider() -> AIProvider:
    selection = get_database_model_selection()
    provider_override = selection[0] if selection else None
    model_override = selection[1] if selection else None
    return build_ai_provider(get_settings(), provider_override, model_override)
