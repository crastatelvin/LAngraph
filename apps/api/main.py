from fastapi import FastAPI

from packages.schemas.debate import DebateCreateRequest, DebateCreateResponse

app = FastAPI(title="AI Parliament API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/debates", response_model=DebateCreateResponse)
def create_debate(payload: DebateCreateRequest) -> DebateCreateResponse:
    # Placeholder MVP endpoint; LangGraph orchestration comes in Phase 1 tasks.
    return DebateCreateResponse(
        debate_id="todo-generated-id",
        proposal=payload.proposal,
        status="created",
    )
