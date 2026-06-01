from functools import lru_cache
from pathlib import Path
from app.schemas.generation import GenerationRequest, split_reference_links

HUMANIZER_ZH_SYSTEM_PROMPT = """你是一位中文文字编辑，专门识别和去除 AI 生成文本的痕迹，使文字听起来更自然、更像真人写作。

请参考 Humanizer-zh 的处理原则：
1. 删除填充短语、开场白、强调性拐杖词和聊天机器人痕迹。
2. 打破公式结构，避免“不仅……而且……”“这不仅是……而是……”、三段式列举、戏剧化转折和通用乐观结尾。
3. 调整句子节奏，混合长短句；避免每句话长度和结构都相同。
4. 信任读者，直接陈述事实，减少过度解释、过度限定、模糊归因和宣传式语言。
5. 删除听起来像金句、口号、新闻稿或销售文案的表达，保留必要信息和原文语气。
6. 避免高频 AI 词汇和套路表达，例如“此外”“至关重要”“深入探讨”“彰显”“赋能”“持续演进的格局”“充满活力的”“作为……的证明”等。
7. 减少破折号、粗体强调、表情符号、内联标题列表和机械的 Markdown 装饰。
8. 保留原文事实、含义、段落层级、列表、标题、引用和 Markdown 结构；只优化表达，不虚构新事实。

输出要求：
- 只输出优化后的正文。
- 不输出编辑建议、处理前/处理后、编辑洞察、评分表、解释说明或总结。
- 不承诺规避检测，不提“AI 检测”“绕过检测”等结果保证。
"""

HUMANIZER_ZH_OUTPUT_CONSTRAINTS = """以上规则仅作为编辑参考。

最终输出要求：
- 只输出优化后的正文。
- 不要输出编辑建议、处理前/处理后、编辑洞察、评分表、修改总结、解释说明或任何质量评分。
- 不承诺规避检测，不提“AI 检测”“绕过检测”等结果保证。
"""

SKILL_DIR = Path(__file__).resolve().parents[3] / "Skill"
SKILL_PROMPT_FILES = {
    "humanize": "Humanizer-zh-SKILL.md",
    "aigc_reduce": "AIGC-Reduce-zh-SKILL.md",
    "generate": "Article-Generate-zh-SKILL.md",
}


def _strip_skill_frontmatter(content: str) -> str:
    normalized = content.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return normalized.strip()
    end = normalized.find("\n---\n", 4)
    if end == -1:
        return normalized.strip()
    return normalized[end + len("\n---\n"):].strip()


@lru_cache
def load_skill_prompt(file_name: str, fallback_prompt: str) -> str:
    try:
        return _strip_skill_frontmatter((SKILL_DIR / file_name).read_text(encoding="utf-8"))
    except OSError:
        return fallback_prompt.strip()


@lru_cache
def load_humanizer_zh_system_prompt() -> str:
    skill_prompt = load_skill_prompt(SKILL_PROMPT_FILES["humanize"], HUMANIZER_ZH_SYSTEM_PROMPT)
    return f"{skill_prompt}\n\n{HUMANIZER_ZH_OUTPUT_CONSTRAINTS.strip()}"


def build_system_prompt(request: GenerationRequest) -> str:
    if request.tool_type == "humanize":
        return load_humanizer_zh_system_prompt()
    if request.tool_type in SKILL_PROMPT_FILES:
        return load_skill_prompt(SKILL_PROMPT_FILES[request.tool_type], "你是 CreationBox 的公众号内容编辑助手，输出必须安全、自然、可编辑。")
    return "你是 CreationBox 的公众号内容编辑助手，输出必须安全、自然、可编辑。"


def _format_reference_links(input_url: str | None) -> str:
    links = split_reference_links(input_url)
    return "\n".join(f"- {link}" for link in links) if links else "无"


def build_prompt(request: GenerationRequest) -> str:
    config = request.config or {}
    if request.tool_type == "humanize":
        preserve_format = config.get("preserve_format", "true") != "false"
        format_instruction = (
            "格式要求：保留原文 Markdown 结构，包括标题、段落、列表、引用和代码块；只优化表达。\n"
            if preserve_format
            else "格式要求：不需要保留原文 Markdown 结构，可以去掉标题、列表、引用等格式限制，整理成自然顺畅、语义连贯的正文。\n"
        )
        return (
            "请按照 Humanizer-zh 中文编辑规则，优化下面文本的自然表达、节奏和可读性。\n"
            f"模式：{request.mode}\n"
            f"{format_instruction}"
            f"原文：{request.input_text}\n"
            "只输出优化后的正文，不要输出标题、编辑建议、处理前/处理后、编辑洞察或解释说明。\n"
        )
    if request.tool_type == "aigc_reduce":
        preserve_format = config.get("preserve_format", "true") != "false"
        format_instruction = (
            "格式要求：保留原文 Markdown 结构，包括标题、段落、列表、引用和代码块。\n"
            if preserve_format
            else "格式要求：不需要保留原文 Markdown 结构，可以去掉标题、列表、引用等格式限制，整理成自然正文。\n"
        )
        return (
            "请按照 AIGC-Reduce-zh 规则处理下面文本。\n"
            f"{format_instruction}"
            f"原文：{request.input_text}\n"
            "只输出改写后的正文，不要输出解释、建议、评分、检测承诺、处理前/处理后或编辑说明。\n"
        )
    content_type = str(config.get("style") or "运营方法论").strip()
    article_tone = str(config.get("tone") or "专业可信").strip()
    source = (
        f"参考链接（作为参考素材线索，不要求抓取网页正文）：\n{_format_reference_links(request.input_url)}"
        if request.mode == "link"
        else f"主题：{request.topic}\n补充素材：{request.materials or request.input_text or '无'}"
    )
    return (
        "请按照 Article-Generate-zh 规则生成可编辑的公众号草稿。\n"
        f"内容类型：{content_type}\n"
        f"文章语气：{article_tone}\n"
        f"输入：{source}\n"
        "输出 Markdown，包含：文章标题、文章正文、结尾行动建议、编辑洞察。"
    )

