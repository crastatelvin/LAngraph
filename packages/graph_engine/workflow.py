import json
import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError


class DebateWorkflowState(TypedDict):
    proposal: str
    status: str
    events: list[dict]
    parse_failures: int
    fallback_used: bool
    agent_context: list[dict]
    opinions: list[dict]
    round_index: int
    rounds: list[dict]
    moderation_notes: list[str]
    evidence_score: float
    votes: list[dict]
    consensus: dict


class DebateWorkflowResult(TypedDict):
    state: dict
    metrics: dict


class DecisionReport(BaseModel):
    decision: str
    confidence: str
    note: str


class StructuredVote(BaseModel):
    agent_id: str
    stance: str
    confidence: float
    evidence: float
    expertise: float
    reliability: float
    diversity_factor: float
    weighted_value: float


class ConsensusReport(BaseModel):
    decision: str
    confidence: str
    score: float
    supporting_arguments: list[str]
    top_risks: list[str]
    minority_position: str


def _parse_report_with_retry(outputs: list[str]) -> tuple[DecisionReport, bool, int]:
    parse_failures = 0
    for idx, raw in enumerate(outputs):
        try:
            parsed = DecisionReport.model_validate(json.loads(raw))
            return parsed, idx > 0, parse_failures
        except (json.JSONDecodeError, ValidationError):
            parse_failures += 1
            continue
    # Safe fallback if all attempts fail.
    return (
        DecisionReport(
            decision="INCONCLUSIVE",
            confidence="low",
            note="Unable to parse model output. Marked inconclusive.",
        ),
        True,
        parse_failures,
    )


def _proposal_tokens(proposal: str) -> set[str]:
    return {token.strip(".,!?").lower() for token in proposal.split() if token.strip()}


def normalize_proposal(state: DebateWorkflowState) -> DebateWorkflowState:
    cleaned = " ".join(state["proposal"].split())
    state["proposal"] = cleaned
    state["events"].append({"event_type": "proposal_normalized", "payload": {"proposal": cleaned}})
    return state


def fetch_agent_context(state: DebateWorkflowState) -> DebateWorkflowState:
    state["agent_context"] = [
        {
            "agent_id": "optimist",
            "style": "growth",
            "expertise": 0.9,
            "reliability": 0.8,
            "bias_keywords": {"adopt", "improve", "scale", "enable"},
        },
        {
            "agent_id": "risk_analyst",
            "style": "risk",
            "expertise": 0.85,
            "reliability": 0.88,
            "bias_keywords": {"risk", "cost", "security", "compliance"},
        },
        {
            "agent_id": "operator",
            "style": "execution",
            "expertise": 0.8,
            "reliability": 0.83,
            "bias_keywords": {"process", "timeline", "weekly", "cadence"},
        },
    ]
    state["events"].append(
        {
            "event_type": "agent_context_loaded",
            "payload": {"agent_count": len(state["agent_context"])},
        }
    )
    return state


def generate_initial_opinions(state: DebateWorkflowState) -> DebateWorkflowState:
    tokens = _proposal_tokens(state["proposal"])
    opinions: list[dict] = []
    for agent in state["agent_context"]:
        keyword_hits = len(tokens.intersection(agent["bias_keywords"]))
        stance = "YES" if keyword_hits >= 1 else "NO"
        confidence = min(0.95, 0.55 + (keyword_hits * 0.12) + (agent["reliability"] * 0.2))
        opinions.append(
            {
                "agent_id": agent["agent_id"],
                "stance": stance,
                "confidence": round(confidence, 2),
                "reason": f"{agent['style']} perspective with {keyword_hits} keyword matches",
            }
        )
    state["opinions"] = opinions
    state["events"].append(
        {
            "event_type": "initial_opinions_generated",
            "payload": {"opinions": opinions},
        }
    )
    return state


def run_debate_rounds(state: DebateWorkflowState) -> DebateWorkflowState:
    tokens = _proposal_tokens(state["proposal"])
    rounds: list[dict] = []
    notes: list[str] = []
    for idx in range(1, 4):
        agreement = sum(1 for item in state["opinions"] if item["stance"] == "YES")
        disagreement = len(state["opinions"]) - agreement
        round_note = (
            f"Round {idx}: agreement={agreement}, disagreement={disagreement}, "
            f"cost_signal={'cost' in tokens}"
        )
        rounds.append(
            {
                "round": idx,
                "agreement": agreement,
                "disagreement": disagreement,
                "summary": round_note,
            }
        )
        notes.append(round_note)
    state["round_index"] = 3
    state["rounds"] = rounds
    state["moderation_notes"] = notes
    state["events"].append(
        {
            "event_type": "debate_rounds_completed",
            "payload": {"rounds": rounds},
        }
    )
    return state


def score_evidence(state: DebateWorkflowState) -> DebateWorkflowState:
    tokens = _proposal_tokens(state["proposal"])
    score = 0.6
    if {"risk", "security", "compliance"}.intersection(tokens):
        score += 0.08
    if {"cost", "budget"}.intersection(tokens):
        score += 0.05
    if "trigger-parse-failure" in state["proposal"].lower():
        score -= 0.05
    state["evidence_score"] = round(min(0.95, max(0.35, score)), 2)
    state["events"].append(
        {
            "event_type": "evidence_scored",
            "payload": {"evidence_score": state["evidence_score"]},
        }
    )
    return state


def vote_structured(state: DebateWorkflowState) -> DebateWorkflowState:
    votes: list[dict] = []
    for opinion in state["opinions"]:
        agent = next(a for a in state["agent_context"] if a["agent_id"] == opinion["agent_id"])
        stance_score = 1 if opinion["stance"] == "YES" else -1
        weighted = (
            stance_score
            * opinion["confidence"]
            * state["evidence_score"]
            * agent["expertise"]
            * agent["reliability"]
            * 1.0
        )
        vote = StructuredVote(
            agent_id=opinion["agent_id"],
            stance=opinion["stance"],
            confidence=opinion["confidence"],
            evidence=state["evidence_score"],
            expertise=agent["expertise"],
            reliability=agent["reliability"],
            diversity_factor=1.0,
            weighted_value=round(weighted, 4),
        )
        votes.append(vote.model_dump())
    state["votes"] = votes
    state["events"].append(
        {
            "event_type": "structured_votes_recorded",
            "payload": {"votes": votes},
        }
    )
    return state


def consensus_compute(state: DebateWorkflowState) -> DebateWorkflowState:
    total = sum(v["weighted_value"] for v in state["votes"])
    decision = "APPROVED" if total > 0.1 else "REJECTED" if total < -0.1 else "INCONCLUSIVE"
    confidence = "high" if abs(total) > 0.8 else "medium" if abs(total) > 0.35 else "low"
    minority_stance = "NO" if decision == "APPROVED" else "YES"
    minority_count = sum(1 for v in state["votes"] if v["stance"] == minority_stance)
    consensus = ConsensusReport(
        decision=decision,
        confidence=confidence,
        score=round(total, 4),
        supporting_arguments=[
            "Weighted confidence favored operational consistency.",
            "Evidence score cleared the minimum trust threshold.",
        ],
        top_risks=["Execution overhead during rollout", "Potential short-term adoption friction"],
        minority_position=f"{minority_count} agents preferred {minority_stance}",
    )
    state["consensus"] = consensus.model_dump()
    state["events"].append(
        {
            "event_type": "consensus_computed",
            "payload": state["consensus"],
        }
    )
    return state


def generate_decision_report(state: DebateWorkflowState) -> DebateWorkflowState:
    primary_output = json.dumps(
        {
            "decision": state["consensus"]["decision"],
            "confidence": state["consensus"]["confidence"],
            "note": f"Consensus score {state['consensus']['score']} with evidence {state['evidence_score']}.",
        }
    )
    if "trigger-parse-failure" in state["proposal"].lower():
        primary_output = "{invalid_json"

    fallback_output = json.dumps(
        {
            "decision": "INCONCLUSIVE",
            "confidence": "low",
            "note": "Fallback report applied after parse failure.",
        }
    )
    report, used_fallback, parse_failures = _parse_report_with_retry([primary_output, fallback_output])
    state["status"] = "created"
    state["parse_failures"] = parse_failures
    state["fallback_used"] = used_fallback
    if used_fallback:
        state["events"].append(
            {
                "event_type": "report_parse_fallback_used",
                "payload": {"reason": "primary_output_invalid"},
            }
        )
    state["events"].append(
        {
            "event_type": "decision_report_generated",
            "payload": {
                **report.model_dump(),
                "consensus": state["consensus"],
            },
        }
    )
    return state


def run_debate_workflow(proposal: str) -> DebateWorkflowResult:
    started = time.perf_counter()
    graph = StateGraph(DebateWorkflowState)
    graph.add_node("normalize_proposal", normalize_proposal)
    graph.add_node("fetch_agent_context", fetch_agent_context)
    graph.add_node("generate_initial_opinions", generate_initial_opinions)
    graph.add_node("run_debate_rounds", run_debate_rounds)
    graph.add_node("score_evidence", score_evidence)
    graph.add_node("vote_structured", vote_structured)
    graph.add_node("consensus_compute", consensus_compute)
    graph.add_node("generate_decision_report", generate_decision_report)
    graph.add_edge(START, "normalize_proposal")
    graph.add_edge("normalize_proposal", "fetch_agent_context")
    graph.add_edge("fetch_agent_context", "generate_initial_opinions")
    graph.add_edge("generate_initial_opinions", "run_debate_rounds")
    graph.add_edge("run_debate_rounds", "score_evidence")
    graph.add_edge("score_evidence", "vote_structured")
    graph.add_edge("vote_structured", "consensus_compute")
    graph.add_edge("consensus_compute", "generate_decision_report")
    graph.add_edge("generate_decision_report", END)

    app = graph.compile()
    initial: DebateWorkflowState = {
        "proposal": proposal,
        "status": "created",
        "events": [],
        "parse_failures": 0,
        "fallback_used": False,
        "agent_context": [],
        "opinions": [],
        "round_index": 0,
        "rounds": [],
        "moderation_notes": [],
        "evidence_score": 0.0,
        "votes": [],
        "consensus": {},
    }
    result = app.invoke(initial)
    latency_ms = (time.perf_counter() - started) * 1000
    return {
        "state": {
            "proposal": result["proposal"],
            "status": result["status"],
            "events": result["events"],
        },
        "metrics": {
            "parse_failures": result["parse_failures"],
            "fallback_used": result["fallback_used"],
            "latency_ms": round(latency_ms, 2),
        },
    }
