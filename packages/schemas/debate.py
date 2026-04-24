from pydantic import BaseModel, Field


class DebateCreateRequest(BaseModel):
    proposal: str = Field(min_length=5, max_length=2000)


class DebateCreateResponse(BaseModel):
    debate_id: str
    proposal: str
    status: str


class DebateRecord(BaseModel):
    debate_id: str
    proposal: str
    status: str


class DebateEvent(BaseModel):
    seq: int
    event_type: str
    payload: dict


class DebateEventsResponse(BaseModel):
    debate_id: str
    events: list[DebateEvent]


class DebateApproveResponse(BaseModel):
    debate_id: str
    status: str
