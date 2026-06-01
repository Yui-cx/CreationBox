from datetime import datetime
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


ToolType = Literal["humanize", "aigc_reduce", "generate"]


def split_reference_links(input_url: str | None) -> list[str]:
    return [item.strip() for item in re.split(r"[\n,，;；]+", input_url or "") if item.strip()]


class GenerationRequest(BaseModel):
    tool_type: ToolType
    mode: str = Field(max_length=32)
    input_text: str | None = Field(default=None, max_length=6000)
    input_url: str | None = Field(default=None, max_length=6000)
    topic: str | None = Field(default=None, max_length=500)
    materials: str | None = Field(default=None, max_length=6000)
    config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self):
        if self.tool_type == "humanize":
            if self.mode not in {"quick", "long"}:
                raise ValueError("VALIDATION_ERROR: AI痕迹去除首版仅支持极速模式和长文本模式。")
            text = (self.input_text or "").strip()
            if not text:
                raise ValueError("VALIDATION_ERROR: 请输入需要优化的文本。")
            limit = 600 if self.mode == "quick" else 2500
            if len(text) > limit:
                raise ValueError(f"VALIDATION_ERROR: {self.mode} 模式最多支持 {limit} 字。")
        if self.tool_type == "aigc_reduce":
            if self.mode != "text":
                raise ValueError("VALIDATION_ERROR: 降AIGC率首版仅支持文本输入。")
            text = (self.input_text or "").strip()
            if not text:
                raise ValueError("VALIDATION_ERROR: 请输入需要处理的文本。")
            if len(text) > 1500:
                raise ValueError("VALIDATION_ERROR: 输入文本最多支持 1500 字。")
        if self.tool_type == "generate":
            if self.mode not in {"topic", "link"}:
                raise ValueError("VALIDATION_ERROR: 生成文章仅支持主题生成或参考链接。")
            if self.mode == "topic" and not (self.topic or "").strip():
                raise ValueError("VALIDATION_ERROR: 请填写文章主题。")
            if self.mode == "link" and not split_reference_links(self.input_url):
                raise ValueError("VALIDATION_ERROR: 请填写参考链接。")
        return self


class GenerationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tool_type: str
    mode: str
    status: str
    output_content: str
    created_at: datetime
    completed_at: datetime | None

class GenerationDetail(GenerationListItem):
    input_snapshot: dict
    config_snapshot: dict
    prompt_tokens: int
    completion_tokens: int
    elapsed_ms: int
    error_code: str | None = None
    error_message: str | None = None
