from app.models.entities import Generation


def generation_to_markdown(generation: Generation) -> str:
    title_map = {
        "humanize": "AI痕迹去除",
        "aigc_reduce": "降AIGC率",
        "generate": "生成文章",
    }
    lines = [
        f"# {title_map.get(generation.tool_type, generation.tool_type)}",
        "",
        f"- 工具：{generation.tool_type}",
        f"- 模式：{generation.mode}",
        f"- 状态：{generation.status}",
        "",
        "## 输入快照",
        "",
        "```json",
        str(generation.input_snapshot),
        "```",
        "",
        "## 生成结果",
        "",
        generation.output_content or "",
    ]
    return "\n".join(lines)
