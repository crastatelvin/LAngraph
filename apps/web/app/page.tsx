"use client";

import Link from "next/link";
import { useState } from "react";
import {
  anchorDecision,
  createDebate,
  createFederation,
  createFederationSession,
  evolveAgent,
  flushSlackOutbound,
  getAdminOverview,
  getAdminSlo,
  getDependencyHealth,
  getFederationDecision,
  getSlackOutboundStatus,
  getTxStatus,
  ingestAgentOutcome,
  listAgents,
  patchAgent,
  recalibrateAgent,
  rollbackAgent,
  joinFederationSession,
} from "../lib/api";

export default function DashboardPage() {
  const [proposal, setProposal] = useState("Adopt weekly async planning sync with reliability review.");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<{ debate_id: string; proposal: string; status: string } | null>(null);
  const [federationName, setFederationName] = useState("Global Product Council");
  const [federationId, setFederationId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [federationOutput, setFederationOutput] = useState<Record<string, unknown> | null>(null);
  const [chainDebateId, setChainDebateId] = useState("");
  const [reportHash, setReportHash] = useState("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
  const [txHash, setTxHash] = useState("");
  const [chainOutput, setChainOutput] = useState<Record<string, unknown> | null>(null);
  const [agentId, setAgentId] = useState("agent-web-001");
  const [agentTraitsText, setAgentTraitsText] = useState('{"risk_tolerance": 0.4, "priority": "reliability"}');
  const [agentOutput, setAgentOutput] = useState<Record<string, unknown> | Array<Record<string, unknown>> | null>(null);
  const [outcomeDebateId, setOutcomeDebateId] = useState("debate-web-001");
  const [predictedConfidence, setPredictedConfidence] = useState("0.55");
  const [actualScore, setActualScore] = useState("0.80");
  const [rollbackVersion, setRollbackVersion] = useState("1");
  const [adminOutput, setAdminOutput] = useState<Record<string, unknown> | null>(null);

  async function onCreate() {
    try {
      setLoading(true);
      setError("");
      const response = await createDebate(proposal);
      setCreated(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  async function onCreateFederation() {
    try {
      const response = await createFederation(federationName);
      setFederationId(response.federation_id);
      setFederationOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create federation");
    }
  }

  async function onCreateSession() {
    try {
      const response = await createFederationSession(federationId, "treaty");
      setSessionId(response.session_id);
      setFederationOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    }
  }

  async function onJoinSession() {
    try {
      const response = await joinFederationSession(sessionId, {
        parliament_name: "Web Control Room Parliament",
        position: "APPROVED",
        confidence: 0.8,
        summary: "Automated federation submission from control room UI.",
        weight: 1.0,
      });
      setFederationOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to join session");
    }
  }

  async function onGetDecision() {
    try {
      const response = await getFederationDecision(sessionId);
      setFederationOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch decision");
    }
  }

  async function onAnchor() {
    try {
      const debateId = chainDebateId || created?.debate_id || "";
      if (!debateId) {
        setError("Provide debate id for anchoring");
        return;
      }
      const response = await anchorDecision(debateId, reportHash);
      setTxHash(String(response.tx_hash || ""));
      setChainOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to anchor decision");
    }
  }

  async function onTxStatus() {
    try {
      const response = await getTxStatus(txHash);
      setChainOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tx status");
    }
  }

  async function onListAgents() {
    try {
      const response = await listAgents();
      setAgentOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to list agents");
    }
  }

  async function onPatchAgent() {
    try {
      const traits = JSON.parse(agentTraitsText) as Record<string, unknown>;
      const response = await patchAgent(agentId, traits, "web_control_room_update");
      setAgentOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to patch agent");
    }
  }

  async function onRecalibrateAgent() {
    try {
      const response = await recalibrateAgent(agentId);
      setAgentOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to recalibrate agent");
    }
  }

  async function onIngestOutcome() {
    try {
      const response = await ingestAgentOutcome(agentId, {
        debate_id: outcomeDebateId,
        predicted_confidence: Number(predictedConfidence),
        actual_score: Number(actualScore),
        notes: "Web panel outcome ingestion",
      });
      setAgentOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ingest outcome");
    }
  }

  async function onEvolveAgent() {
    try {
      const response = await evolveAgent(agentId, {
        max_delta: 0.1,
        reason: "web_evolution_cycle",
      });
      setAgentOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to evolve agent");
    }
  }

  async function onRollbackAgent() {
    try {
      const response = await rollbackAgent(agentId, Number(rollbackVersion));
      setAgentOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rollback agent");
    }
  }

  async function onAdminOverview() {
    try {
      const response = await getAdminOverview(true);
      setAdminOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch admin overview");
    }
  }

  async function onAdminSlo() {
    try {
      const response = await getAdminSlo();
      setAdminOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch admin SLO");
    }
  }

  async function onAdminDependencyHealth() {
    try {
      const response = await getDependencyHealth();
      setAdminOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch dependency health");
    }
  }

  async function onSlackQueueStatus() {
    try {
      const response = await getSlackOutboundStatus();
      setAdminOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch queue status");
    }
  }

  async function onSlackQueueFlush() {
    try {
      const response = await flushSlackOutbound();
      setAdminOutput(response);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to flush queue");
    }
  }

  return (
    <div className="grid">
      <div className="grid grid-2">
      <section className="card">
        <h2 style={{ marginTop: 0 }}>New Debate</h2>
        <p className="muted">Create a debate and jump straight into the event timeline.</p>
        <textarea
          className="textarea"
          rows={5}
          value={proposal}
          onChange={(event) => setProposal(event.target.value)}
          placeholder="Enter proposal..."
        />
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button className="button primary" onClick={onCreate} disabled={loading || proposal.length < 5}>
            {loading ? "Creating..." : "Create Debate"}
          </button>
        </div>
        {error ? <p style={{ color: "#ff9ea8" }}>{error}</p> : null}
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Latest Result</h2>
        {!created ? (
          <p className="muted">No debate created in this session yet.</p>
        ) : (
          <>
            <p>
              <strong>ID:</strong> {created.debate_id}
            </p>
            <p>
              <strong>Status:</strong> {created.status}
            </p>
            <p className="muted">{created.proposal}</p>
            <Link href={`/debates/${created.debate_id}`}>Open debate timeline</Link>
          </>
        )}
      </section>
      </div>

      <div className="grid grid-2">
        <section className="card">
          <h2 style={{ marginTop: 0 }}>Federation Panel</h2>
          <p className="muted">Create federation, open session, submit parliament, and fetch global decision.</p>
          <input
            className="input"
            value={federationName}
            onChange={(event) => setFederationName(event.target.value)}
            placeholder="Federation name"
          />
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button className="button" onClick={onCreateFederation}>
              Create Federation
            </button>
          </div>
          <input
            className="input"
            style={{ marginTop: 8 }}
            value={federationId}
            onChange={(event) => setFederationId(event.target.value)}
            placeholder="Federation ID"
          />
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button className="button" onClick={onCreateSession} disabled={!federationId}>
              Create Session
            </button>
          </div>
          <input
            className="input"
            style={{ marginTop: 8 }}
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            placeholder="Session ID"
          />
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button className="button" onClick={onJoinSession} disabled={!sessionId}>
              Join Session
            </button>
            <button className="button" onClick={onGetDecision} disabled={!sessionId}>
              Get Decision
            </button>
          </div>
        </section>

        <section className="card">
          <h2 style={{ marginTop: 0 }}>Chain Panel</h2>
          <p className="muted">Anchor decision report hashes and query transaction status.</p>
          <input
            className="input"
            value={chainDebateId}
            onChange={(event) => setChainDebateId(event.target.value)}
            placeholder="Debate ID (optional if latest exists)"
          />
          <input
            className="input"
            style={{ marginTop: 8 }}
            value={reportHash}
            onChange={(event) => setReportHash(event.target.value)}
            placeholder="Report hash"
          />
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button className="button" onClick={onAnchor} disabled={reportHash.length < 16}>
              Anchor Decision
            </button>
          </div>
          <input
            className="input"
            style={{ marginTop: 8 }}
            value={txHash}
            onChange={(event) => setTxHash(event.target.value)}
            placeholder="Transaction hash"
          />
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button className="button" onClick={onTxStatus} disabled={!txHash}>
              Get TX Status
            </button>
          </div>
        </section>
      </div>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Agents Panel</h2>
        <p className="muted">Manage agents, ingest outcomes, evolve traits, and rollback versions.</p>
        <input
          className="input"
          value={agentId}
          onChange={(event) => setAgentId(event.target.value)}
          placeholder="Agent ID"
        />
        <textarea
          className="textarea"
          style={{ marginTop: 8 }}
          rows={4}
          value={agentTraitsText}
          onChange={(event) => setAgentTraitsText(event.target.value)}
          placeholder='{"risk_tolerance": 0.4}'
        />
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          <button className="button" onClick={onListAgents}>
            List Agents
          </button>
          <button className="button" onClick={onPatchAgent} disabled={!agentId}>
            Patch Agent
          </button>
          <button className="button" onClick={onRecalibrateAgent} disabled={!agentId}>
            Recalibrate
          </button>
        </div>
        <input
          className="input"
          style={{ marginTop: 8 }}
          value={outcomeDebateId}
          onChange={(event) => setOutcomeDebateId(event.target.value)}
          placeholder="Outcome debate ID"
        />
        <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <input
            className="input"
            value={predictedConfidence}
            onChange={(event) => setPredictedConfidence(event.target.value)}
            placeholder="Predicted confidence"
          />
          <input
            className="input"
            value={actualScore}
            onChange={(event) => setActualScore(event.target.value)}
            placeholder="Actual score"
          />
        </div>
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          <button className="button" onClick={onIngestOutcome} disabled={!agentId || !outcomeDebateId}>
            Ingest Outcome
          </button>
          <button className="button" onClick={onEvolveAgent} disabled={!agentId}>
            Evolve
          </button>
        </div>
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          <input
            className="input"
            style={{ maxWidth: 160 }}
            value={rollbackVersion}
            onChange={(event) => setRollbackVersion(event.target.value)}
            placeholder="Rollback version"
          />
          <button className="button" onClick={onRollbackAgent} disabled={!agentId || !rollbackVersion}>
            Rollback
          </button>
        </div>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Admin Ops Panel</h2>
        <p className="muted">Run operational checks and queue actions for production readiness monitoring.</p>
        <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="button" style={{ width: "auto" }} onClick={onAdminOverview}>
            Overview
          </button>
          <button className="button" style={{ width: "auto" }} onClick={onAdminSlo}>
            SLO
          </button>
          <button className="button" style={{ width: "auto" }} onClick={onAdminDependencyHealth}>
            Dependencies
          </button>
          <button className="button" style={{ width: "auto" }} onClick={onSlackQueueStatus}>
            Queue Status
          </button>
          <button className="button" style={{ width: "auto" }} onClick={onSlackQueueFlush}>
            Flush Queue
          </button>
        </div>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Ops Output</h2>
        {federationOutput ? (
          <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(federationOutput, null, 2)}</pre>
        ) : null}
        {chainOutput ? (
          <pre style={{ marginTop: 10, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(chainOutput, null, 2)}</pre>
        ) : null}
        {agentOutput ? (
          <pre style={{ marginTop: 10, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(agentOutput, null, 2)}</pre>
        ) : null}
        {adminOutput ? (
          <pre style={{ marginTop: 10, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(adminOutput, null, 2)}</pre>
        ) : null}
        {!federationOutput && !chainOutput && !agentOutput && !adminOutput ? (
          <p className="muted">No federation/chain/agent/admin responses yet.</p>
        ) : null}
        {error ? <p style={{ color: "#ff9ea8" }}>{error}</p> : null}
      </section>
    </div>
  );
}
