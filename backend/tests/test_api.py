import os

os.environ["AI_PROVIDER"] = "mock"

import pytest
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.api.images import _prepare_inpaint_mask
from app.models.entities import Generation, ModelCallLog, User
from app.services import lama_inpaint
from app.services import ai_provider
from app.services.ai_provider import MockAIProvider, OpenAICompatibleProvider, build_ai_provider, build_prompt, build_system_prompt, resolve_provider_config
from app.services.markdown import generation_to_markdown
from app.schemas.generation import GenerationRequest


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_me(client: TestClient):
    register_response = client.post("/api/auth/register", json={"username": "tester_me", "password": "password123"})
    assert register_response.status_code == 403
    assert register_response.json()["detail"] == "REGISTRATION_DISABLED"

    headers = auth_headers(client)
    response = client.get("/api/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "admin"
    assert body["is_admin"] is True
    assert body["quota_total"] == -1
    assert body["quota_remaining"] == -1


def test_admin_can_create_regular_user_and_regular_user_cannot_access_admin(client: TestClient):
    admin_headers = auth_headers(client)
    create_response = client.post(
        "/api/admin/users",
        json={"username": "regular_user", "password": "pw", "daily_quota_total": 1},
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["username"] == "regular_user"
    assert created["is_admin"] is False
    assert created["quota_total"] == 1

    login_response = client.post("/api/auth/login", json={"username": "regular_user", "password": "pw"})
    assert login_response.status_code == 200
    user_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    me = client.get("/api/me", headers=user_headers)
    assert me.status_code == 200
    assert me.json()["is_admin"] is False
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403


def test_regular_user_quota_is_limited_and_admin_is_unlimited(client: TestClient):
    admin_headers = auth_headers(client)
    client.post(
        "/api/admin/users",
        json={"username": "quota_user", "password": "pw", "daily_quota_total": 1},
        headers=admin_headers,
    )
    login_response = client.post("/api/auth/login", json={"username": "quota_user", "password": "pw"})
    user_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    payload = {
        "tool_type": "humanize",
        "mode": "quick",
        "input_text": "这是一个需要优化的公众号段落。",
        "config": {},
    }
    with client.stream("POST", "/api/generations/stream", json=payload, headers=user_headers) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert '"quota_remaining": 0' in body
    second = client.post("/api/generations/stream", json=payload, headers=user_headers)
    assert second.status_code == 402

    with client.stream("POST", "/api/generations/stream", json=payload, headers=admin_headers) as response:
        assert response.status_code == 200
        admin_body = "".join(response.iter_text())
    assert '"quota_remaining": -1' in admin_body


def test_admin_user_list_stats_and_quota_update(client: TestClient):
    admin_headers = auth_headers(client)
    create_response = client.post(
        "/api/admin/users",
        json={"username": "stats_user", "password": "pw", "daily_quota_total": 3},
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]
    quota_response = client.patch(
        f"/api/admin/users/{user_id}/quota",
        json={"total_quota": 7, "used_quota": 2},
        headers=admin_headers,
    )
    assert quota_response.status_code == 200
    assert quota_response.json()["quota_remaining"] == 5

    users = client.get("/api/admin/users", headers=admin_headers)
    assert users.status_code == 200
    item = next(user for user in users.json() if user["username"] == "stats_user")
    assert item["quota_total"] == 7
    assert item["quota_used"] == 2
    assert item["generation_count"] == 0


def test_cannot_remove_last_active_admin(client: TestClient):
    admin_headers = auth_headers(client)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").one()
        admin_id = admin.id
    finally:
        db.close()

    demote = client.patch(f"/api/admin/users/{admin_id}", json={"is_admin": False}, headers=admin_headers)
    assert demote.status_code == 400
    assert demote.json()["detail"] == "LAST_ADMIN_REQUIRED"
    deactivate = client.patch(f"/api/admin/users/{admin_id}", json={"status": "inactive"}, headers=admin_headers)
    assert deactivate.status_code == 400
    assert deactivate.json()["detail"] == "LAST_ADMIN_REQUIRED"


def test_model_management_whitelist_and_missing_key_validation(client: TestClient):
    admin_headers = auth_headers(client)
    config = client.get("/api/admin/model-config", headers=admin_headers)
    assert config.status_code == 200
    assert {option["provider"] for option in config.json()["options"]} == {"deepseek", "openrouter"}

    update = client.put(
        "/api/admin/model-config",
        json={"provider": "openrouter", "model": "openai/gpt-5.4-mini"},
        headers=admin_headers,
    )
    assert update.status_code == 200
    assert update.json()["provider"] == "openrouter"
    assert update.json()["model"] == "openai/gpt-5.4-mini"

    invalid = client.put(
        "/api/admin/model-config",
        json={"provider": "openrouter", "model": "not-allowed"},
        headers=admin_headers,
    )
    assert invalid.status_code == 422
    validate = client.post("/api/admin/model-config/validate", json={}, headers=admin_headers)
    assert validate.status_code == 400
    assert validate.json()["detail"] == "AI_PROVIDER_NOT_CONFIGURED"


def test_stream_generation_and_history(client: TestClient):
    headers = auth_headers(client)
    payload = {
        "tool_type": "humanize",
        "mode": "quick",
        "input_text": "这是一个需要优化的公众号段落，它表达完整但句式比较标准化。",
        "config": {}
    }
    with client.stream("POST", "/api/generations/stream", json=payload, headers=headers) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: metadata" in body
    assert "event: delta" in body
    assert "event: done" in body

    history = client.get("/api/generations", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) >= 1


def test_aigc_reduce_stream_generation_and_history(client: TestClient):
    headers = auth_headers(client)
    payload = {
        "tool_type": "aigc_reduce",
        "mode": "text",
        "input_text": "随着数字化技术的不断发展，企业管理模式正在发生深刻变化。",
        "config": {"preserve_format": "true"},
    }
    with client.stream("POST", "/api/generations/stream", json=payload, headers=headers) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: metadata" in body
    assert "event: delta" in body
    assert "event: done" in body

    history = client.get("/api/generations", headers=headers)
    assert history.status_code == 200
    assert any(item["tool_type"] == "aigc_reduce" for item in history.json())


def test_aigc_reduce_validation_rejects_empty_and_over_limit():
    empty = GenerationRequest.model_validate({"tool_type": "aigc_reduce", "mode": "text", "input_text": "正文"})
    assert empty.tool_type == "aigc_reduce"
    max_length = GenerationRequest.model_validate({"tool_type": "aigc_reduce", "mode": "text", "input_text": "字" * 8000})
    assert len(max_length.input_text or "") == 8000
    with pytest.raises(ValueError):
        GenerationRequest.model_validate({"tool_type": "aigc_reduce", "mode": "text", "input_text": ""})
    with pytest.raises(ValueError):
        GenerationRequest.model_validate({"tool_type": "aigc_reduce", "mode": "text", "input_text": "字" * 8001})


def test_history_is_limited_to_ten_and_excludes_removed_tool(client: TestClient):
    headers = auth_headers(client)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").one()
        for index in range(12):
            db.add(
                Generation(
                    user_id=user.id,
                    tool_type="humanize" if index % 3 == 0 else ("aigc_reduce" if index % 3 == 1 else "generate"),
                    mode="quick" if index % 2 == 0 else "topic",
                    input_snapshot={},
                    config_snapshot={},
                    output_content=f"可见记录 {index}",
                    status="succeeded",
                )
            )
        db.add(
            Generation(
                user_id=user.id,
                tool_type="imitate",
                mode="text",
                input_snapshot={},
                config_snapshot={},
                output_content="旧仿写记录",
                status="succeeded",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/generations?limit=20", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 10
    assert all(item["tool_type"] != "imitate" for item in body)
    assert any(item["tool_type"] == "aigc_reduce" for item in body)


def test_delete_generation_removes_item_with_call_logs(client: TestClient):
    headers = auth_headers(client)
    payload = {
        "tool_type": "generate",
        "mode": "topic",
        "topic": "删除测试",
        "config": {},
    }
    with client.stream("POST", "/api/generations/stream", json=payload, headers=headers) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    generation_id = body.split('"generation_id": "')[1].split('"')[0]

    db = SessionLocal()
    try:
        assert db.get(Generation, generation_id) is not None
        assert db.query(ModelCallLog).filter(ModelCallLog.generation_id == generation_id).count() == 1
    finally:
        db.close()

    delete_response = client.delete(f"/api/generations/{generation_id}", headers=headers)
    assert delete_response.status_code == 204
    get_response = client.get(f"/api/generations/{generation_id}", headers=headers)
    assert get_response.status_code == 404

    db = SessionLocal()
    try:
        assert db.get(Generation, generation_id) is None
        assert db.query(ModelCallLog).filter(ModelCallLog.generation_id == generation_id).count() == 0
    finally:
        db.close()


def test_only_default_admin_can_login(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "tester_scope_b", "password": "password123"})
    assert response.status_code == 401


def test_admin_quota_is_unlimited_after_generation(client: TestClient):
    headers = auth_headers(client)
    payload = {
        "tool_type": "generate",
        "mode": "topic",
        "topic": "公众号内容规划",
        "config": {}
    }
    with client.stream("POST", "/api/generations/stream", json=payload, headers=headers) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert '"quota_remaining": -1' in body
    me = client.get("/api/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["quota_remaining"] == -1


def test_deepseek_is_default_real_provider_config():
    settings = Settings(ai_provider="deepseek", deepseek_api_key="deepseek-key")
    config = resolve_provider_config(settings)
    assert config is not None
    assert config.name == "deepseek"
    assert config.base_url == "https://api.deepseek.com"
    assert config.api_key == "deepseek-key"
    assert config.model == "deepseek-v4-flash"
    assert config.extra_body["thinking"] == {"type": "disabled"}
    provider = build_ai_provider(settings)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "deepseek"


def test_openrouter_provider_config_adds_optional_headers():
    settings = Settings(
        ai_provider="openrouter",
        openrouter_api_key="openrouter-key",
        openrouter_model_text="google/gemini-3.1-flash-lite",
        openrouter_http_referer="https://creationbox.example",
        openrouter_app_title="CreationBox MVP",
    )
    config = resolve_provider_config(settings)
    assert config is not None
    assert config.name == "openrouter"
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.api_key == "openrouter-key"
    assert config.model == "google/gemini-3.1-flash-lite"
    assert config.extra_headers["HTTP-Referer"] == "https://creationbox.example"
    assert config.extra_headers["X-Title"] == "CreationBox MVP"


def test_missing_real_provider_key_falls_back_to_mock():
    provider = build_ai_provider(Settings(ai_provider="deepseek", ai_api_key="", deepseek_api_key=""))
    assert isinstance(provider, MockAIProvider)


def test_humanize_uses_humanizer_zh_system_prompt():
    request = GenerationRequest(tool_type="humanize", mode="quick", input_text="此外，这不仅是一次更新，而是重要转折。")
    prompt = build_system_prompt(request)
    assert "Humanizer-zh" in prompt
    assert "核心规则速查" in prompt
    assert "只输出优化后的正文" in prompt
    assert "不仅……而且" in prompt
    assert "评分表" in prompt
    assert "不承诺规避检测" in prompt
    assert not prompt.lstrip().startswith("---")


def test_humanizer_skill_prompt_falls_back_when_file_missing(monkeypatch: pytest.MonkeyPatch):
    ai_provider.load_skill_prompt.cache_clear()
    ai_provider.load_humanizer_zh_system_prompt.cache_clear()
    monkeypatch.setitem(ai_provider.SKILL_PROMPT_FILES, "humanize", "missing.md")
    request = GenerationRequest(tool_type="humanize", mode="quick", input_text="此外，这不仅是一次更新，而是重要转折。")
    prompt = build_system_prompt(request)
    assert "你是一位中文文字编辑" in prompt
    assert "最终输出要求" in prompt
    assert "不要输出编辑建议" in prompt
    ai_provider.load_skill_prompt.cache_clear()
    ai_provider.load_humanizer_zh_system_prompt.cache_clear()


def test_humanize_prompt_preserves_format_by_default():
    request = GenerationRequest(tool_type="humanize", mode="quick", input_text="# 标题\n\n- 此外，这是一个重要更新。")
    prompt = build_prompt(request)
    assert "保留原文 Markdown 结构" in prompt
    assert "标题、段落、列表、引用和代码块" in prompt


def test_humanize_prompt_can_disable_format_preservation():
    request = GenerationRequest(
        tool_type="humanize",
        mode="quick",
        input_text="# 标题\n\n- 此外，这是一个重要更新。",
        config={"preserve_format": "false"},
    )
    prompt = build_prompt(request)
    assert "不需要保留原文 Markdown 结构" in prompt
    assert "格式限制" in prompt


def test_aigc_reduce_prompt_preserves_format_by_default():
    request = GenerationRequest(tool_type="aigc_reduce", mode="text", input_text="# 标题\n\n这是一段需要处理的论文内容。")
    system_prompt = build_system_prompt(request)
    prompt = build_prompt(request)
    assert "AIGC-Reduce-zh" in system_prompt
    assert "不大幅改动原文总字数" in system_prompt
    assert "保留原文 Markdown 结构" in prompt
    assert "只输出改写后的正文" in prompt


def test_aigc_reduce_prompt_can_disable_format_preservation():
    request = GenerationRequest(
        tool_type="aigc_reduce",
        mode="text",
        input_text="# 标题\n\n这是一段需要处理的论文内容。",
        config={"preserve_format": "false"},
    )
    prompt = build_prompt(request)
    assert "不需要保留原文 Markdown 结构" in prompt
    assert "自然正文" in prompt


def test_aigc_reduce_markdown_export_title():
    generation = Generation(
        user_id=1,
        tool_type="aigc_reduce",
        mode="text",
        input_snapshot={},
        config_snapshot={},
        output_content="处理结果",
        status="succeeded",
    )
    markdown = generation_to_markdown(generation)
    assert markdown.startswith("# 降AIGC率")


def test_non_humanize_keeps_default_system_prompt():
    request = GenerationRequest(tool_type="generate", mode="topic", topic="内容运营")
    prompt = build_system_prompt(request)
    assert "Article-Generate-zh" in prompt
    assert "公众号文章生成" in prompt


def test_generate_prompt_uses_style_tone_and_multiple_reference_links():
    request = GenerationRequest(
        tool_type="generate",
        mode="link",
        input_url="https://example.com/a\nhttps://example.com/b，https://example.com/c",
        config={"style": "深度拆解", "tone": "犀利但克制", "keywords": "不应使用"},
    )
    prompt = build_prompt(request)
    assert "内容类型：深度拆解" in prompt
    assert "文章语气：犀利但克制" in prompt
    assert "- https://example.com/a" in prompt
    assert "- https://example.com/b" in prompt
    assert "- https://example.com/c" in prompt
    assert "关键词：" not in prompt
    assert "不应使用" not in prompt


def test_generate_link_mode_rejects_empty_reference_list():
    with pytest.raises(ValueError, match="VALIDATION_ERROR"):
        GenerationRequest(tool_type="generate", mode="link", input_url="，；\n", config={})


def test_skill_prompt_loader_falls_back_when_file_missing():
    ai_provider.load_skill_prompt.cache_clear()
    prompt = ai_provider.load_skill_prompt("missing.md", "兜底提示词")
    assert prompt == "兜底提示词"


def png_bytes(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def test_image_inpaint_returns_png(client: TestClient):
    headers = auth_headers(client)
    source = np.full((32, 32, 3), 240, dtype=np.uint8)
    source[12:20, 12:20] = (0, 0, 255)
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[12:20, 12:20] = 255

    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"method": "telea", "radius": "3"},
        files={
            "image": ("source.png", png_bytes(source), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    decoded = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (32, 32)


def test_image_inpaint_supports_ns_method(client: TestClient):
    headers = auth_headers(client)
    source = np.full((24, 24, 3), 220, dtype=np.uint8)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[8:16, 8:16] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"method": "ns", "radius": "2"},
        files={
            "image": ("source.png", png_bytes(source), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_image_inpaint_lama_returns_png(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def fake_lama(source_bgr, mask_gray, settings):
        return png_bytes(source_bgr)

    monkeypatch.setattr(lama_inpaint, "_run_lama_sync", fake_lama)
    headers = auth_headers(client)
    source = np.full((24, 24, 3), 220, dtype=np.uint8)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[8:16, 8:16] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"engine": "lama", "radius": "5"},
        files={
            "image": ("source.png", png_bytes(source), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_image_inpaint_lama_rejects_large_image(client: TestClient):
    headers = auth_headers(client)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[4:12, 4:12] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"engine": "lama", "radius": "5"},
        files={
            "image": ("source.png", b"0" * (10 * 1024 * 1024 + 1), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "IMAGE_TOO_LARGE"


def test_image_inpaint_lama_busy(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    class LockedLamaTask:
        def locked(self):
            return True

        async def acquire(self):
            return None

        def release(self):
            return None

    monkeypatch.setattr(lama_inpaint, "_lama_task_lock", LockedLamaTask())
    headers = auth_headers(client)
    source = np.full((24, 24, 3), 220, dtype=np.uint8)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[8:16, 8:16] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"engine": "lama", "radius": "5"},
        files={
            "image": ("source.png", png_bytes(source), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "LAMA_BUSY"


def test_image_inpaint_lama_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def raise_unavailable(source_bgr, mask_gray, settings):
        raise lama_inpaint.LamaUnavailableError("LAMA_UNAVAILABLE")

    monkeypatch.setattr(lama_inpaint, "_run_lama_sync", raise_unavailable)
    headers = auth_headers(client)
    source = np.full((24, 24, 3), 220, dtype=np.uint8)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[8:16, 8:16] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"engine": "lama", "radius": "5"},
        files={
            "image": ("source.png", png_bytes(source), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "LAMA_UNAVAILABLE"


def test_image_inpaint_rejects_mask_size_mismatch(client: TestClient):
    headers = auth_headers(client)
    source = np.full((32, 32, 3), 240, dtype=np.uint8)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[4:12, 4:12] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"method": "telea", "radius": "3"},
        files={
            "image": ("source.png", png_bytes(source), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "INVALID_MASK"


def test_image_inpaint_rejects_unsupported_type(client: TestClient):
    headers = auth_headers(client)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[4:12, 4:12] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"method": "telea", "radius": "3"},
        files={
            "image": ("source.txt", b"not an image", "text/plain"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "UNSUPPORTED_IMAGE_TYPE"


def test_image_inpaint_rejects_large_image(client: TestClient):
    headers = auth_headers(client)
    mask = np.zeros((24, 24), dtype=np.uint8)
    mask[4:12, 4:12] = 255
    response = client.post(
        "/api/images/inpaint",
        headers=headers,
        data={"method": "telea", "radius": "3"},
        files={
            "image": ("source.png", b"0" * (10 * 1024 * 1024 + 1), "image/png"),
            "mask": ("mask.png", png_bytes(mask), "image/png"),
        },
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "IMAGE_TOO_LARGE"


def test_image_mask_preprocessing_expands_marked_area():
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[14:18, 14:18] = 255
    prepared = _prepare_inpaint_mask(mask, radius=5)
    assert prepared.shape == mask.shape
    assert np.count_nonzero(prepared) > np.count_nonzero(mask)
