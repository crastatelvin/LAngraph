"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getFederationDecision, getFederationSubmissions } from "../../../lib/api";

type Submission = {
  id: number;
  parliament_name: string;
  position: string;
  confidence: number;
  summary: string;
  weight: number;
  submitted_by: string;
  submitted_at: string;
};

export default function FederationSessionPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = String(params.sessionId || "");
  const [decision, setDecision] = useState<Record<string, unknown> | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [error, setError] = useState("");
  const [polling, setPolling] = useState(true);

  const load = useCallback(async (): Promise<void> => {
    if (!sessionId) {
      return;
    }
    try {
      setError("");
      const [decisionPayload, submissionsPayload] = await Promise.all([
        getFederationDecision(sessionId),
        getFederationSubmissions(sessionId),
      ]);
      setDecision(decisionPayload);
      setSubmissions((submissionsPayload.submissions as Submission[]) || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load federation session");
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!polling) {
      return;
    }
    const interval = setInterval(() => {
      void load();
    }, 4000);
    return () => clearInterval(interval);
  }, [load, polling]);

  const weightedScore = useMemo(() => {
    if (!submissions.length) {
      return 0;
    }
    let total = 0;
    let weights = 0;
    for (const submission of submissions) {
      const stance = submission.position === "APPROVED" ? 1 : submission.position === "REJECTED" ? -1 : 0;
      total += stance * submission.confidence * submission.weight;
      weights += submission.weight;
    }
    return weights > 0 ? Number((total / weights).toFixed(4)) : 0;
  }, [submissions]);

  return (
    <div className="grid" style={{ gap: 12 }}>
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div>
            <h2 style={{ margin: 0 }}>Federation Session {sessionId}</h2>
            <p className="muted" style={{ margin: "6px 0 0" }}>
              Live decision polling and submission history
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

      <section className="card">
        <h3 style={{ marginTop: 0 }}>Decision Snapshot</h3>
        <div className="grid grid-2">
          <article className="card" style={{ padding: 12 }}>
            <strong>API Decision</strong>
            <pre style={{ margin: "8px 0 0", whiteSpace: "pre-wrap", fontSize: 12, color: "#cdd7ff" }}>
              {JSON.stringify(decision || { status: "pending" }, null, 2)}
            </pre>
          </article>
          <article className="card" style={{ padding: 12 }}>
            <strong>Weighted Replay</strong>
            <p className="muted" style={{ marginTop: 8 }}>
              Submission count: {submissions.length}
            </p>
            <p style={{ margin: 0 }}>
              <strong>Computed score:</strong> {weightedScore}
            </p>
          </article>
        </div>
        {error ? <p style={{ color: "#ff9ea8" }}>{error}</p> : null}
      </section>

      <section className="card">
        <h3 style={{ marginTop: 0 }}>Submission History</h3>
        <div className="grid">
          {submissions.map((item) => (
            <article key={item.id} className="card" style={{ padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>{item.parliament_name}</strong>
                <span className="muted">
                  {item.position} | conf {item.confidence} | w {item.weight}
                </span>
              </div>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                {item.summary}
              </p>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                by {item.submitted_by} at {item.submitted_at}
              </p>
            </article>
          ))}
          {!submissions.length ? <p className="muted">No submissions yet for this session.</p> : null}
        </div>
      </section>
    </div>
  );
}
