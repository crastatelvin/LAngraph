from pydantic import BaseModel, Field


class DebateCreateRequest(BaseModel):
    proposal: str = Field(min_length=5, max_length=2000)


class DebateCreateResponse(BaseModel):
    debate_id: str
    proposal: str
    status: str
