"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getAgentOutcomes, getAgentVersions, listAgents, type AgentOutcome, type AgentRecord, type AgentVersionRecord } from "../../../lib/api";

export default function AgentDetailPage() {
  const params = useParams<{ agentId: string }>();
  const agentId = String(params.agentId || "");
  const [agent, setAgent] = useState<AgentRecord | null>(null);
  const [outcomes, setOutcomes] = useState<AgentOutcome[]>([]);
  const [versions, setVersions] = useState<AgentVersionRecord[]>([]);
  const [polling, setPolling] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (): Promise<void> => {
    if (!agentId) {
      return;
    }
    try {
      setError("");
      const [agents, outcomeRows, versionRows] = await Promise.all([
        listAgents(),
        getAgentOutcomes(agentId),
        getAgentVersions(agentId),
      ]);
      setAgent(agents.find((item) => item.agent_id === agentId) || null);
      setOutcomes(outcomeRows);
      setVersions(versionRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agent analytics");
    }
  }, [agentId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!polling) {
      return;
    }
    const interval = setInterval(() => {
      void load();
    }, 5000);
    return () => clearInterval(interval);
  }, [load, polling]);

  const calibrationTrend = useMemo(() => {
    return versions
      .slice()
      .reverse()
      .map((entry) => ({
        version: entry.version,
        calibration_score: entry.calibration_score,
      }));
  }, [versions]);

  const avgOutcomeScore = useMemo(() => {
    if (!outcomes.length) {
      return 0;
    }
    const sum = outcomes.reduce((acc, item) => acc + item.outcome_score, 0);
    return Number((sum / outcomes.length).toFixed(4));
  }, [outcomes]);

  return (
    <div className="grid" style={{ gap: 12 }}>
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div>
            <h2 style={{ margin: 0 }}>Agent Evolution: {agentId}</h2>
            <p className="muted" style={{ margin: "6px 0 0" }}>
              Calibration, outcomes, and version trajectory
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="button" style={{ width: "auto" }} onClick={() => setPolling((prev) => !prev)}>
              {polling ? "Pause Polling" : "Resume Polling"}
            </button>
            <button className="button" style={{ width: "auto" }} onClick={() => void load()}>
              Refresh
            </button>
            <Link href="/">Back to dashboard</Link>
          </div>
        </div>
      </section>

      <section className="grid grid-2">
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Current Profile</h3>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
            {JSON.stringify(agent || { status: "not_found" }, null, 2)}
          </pre>
        </article>
        <article className="card">
          <h3 style={{ marginTop: 0 }}>Evolution Metrics</h3>
          <p className="muted" style={{ marginBottom: 4 }}>
            Outcome events: {outcomes.length}
          </p>
          <p className="muted" style={{ marginBottom: 4 }}>
            Version records: {versions.length}
          </p>
          <p style={{ margin: 0 }}>
            <strong>Average outcome score:</strong> {avgOutcomeScore}
          </p>
        </article>
      </section>

      <section className="card">
        <h3 style={{ marginTop: 0 }}>Calibration Trend</h3>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
          {JSON.stringify(calibrationTrend, null, 2)}
        </pre>
      </section>

      <section className="card">
        <h3 style={{ marginTop: 0 }}>Recent Outcomes</h3>
        <div className="grid">
          {outcomes.map((item) => (
            <article key={item.id} className="card" style={{ padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>Debate {item.debate_id}</strong>
                <span className="muted">score {item.outcome_score}</span>
              </div>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                pred {item.predicted_confidence} vs actual {item.actual_score}
              </p>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                {item.notes || "No notes"}
              </p>
            </article>
          ))}
          {!outcomes.length ? <p className="muted">No outcomes recorded yet.</p> : null}
        </div>
      </section>

      <section className="card">
        <h3 style={{ marginTop: 0 }}>Version History</h3>
        <div className="grid">
          {versions.map((item) => (
            <article key={`${item.id}-${item.version}`} className="card" style={{ padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <strong>Version {item.version}</strong>
                <span className="muted">{item.reason}</span>
              </div>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                calibration {item.calibration_score} at {item.created_at}
              </p>
              <pre style={{ marginTop: 8, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(item.traits, null, 2)}</pre>
            </article>
          ))}
          {!versions.length ? <p className="muted">No versions available yet.</p> : null}
        </div>
      </section>

      {error ? <p style={{ color: "#ff9ea8" }}>{error}</p> : null}
    </div>
  );
}
