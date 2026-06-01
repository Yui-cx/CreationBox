from pydantic import BaseModel


class MeResponse(BaseModel):
    id: int
    username: str
    email: str | None
    is_admin: bool
    quota_total: int
    quota_used: int
    quota_remaining: int
