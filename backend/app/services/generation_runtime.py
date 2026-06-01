import json
from app.schemas.generation import GenerationRequest


def sse_event(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def input_snapshot(payload: GenerationRequest) -> dict:
    return {
        "input_text": payload.input_text,
        "input_url": payload.input_url,
        "topic": payload.topic,
        "materials": payload.materials,
    }
