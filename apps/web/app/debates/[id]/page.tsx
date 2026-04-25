"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { getDebate, getDebateEvents } from "../../../lib/api";

type DebateEvent = {
  seq: number;
  event_type: string;
  payload: Record<string, unknown>;
};

export default function DebateDetailPage() {
  const params = useParams<{ id: string }>();
  const debateId = String(params.id || "");
  const [status, setStatus] = useState("loading");
  const [proposal, setProposal] = useState("");
  const [events, setEvents] = useState<DebateEvent[]>([]);
  const [error, setError] = useState("");

  const loadData = useCallback(async (): Promise<void> => {
    if (!debateId) {
      return;
    }
    try {
      setError("");
      const debate = await getDebate(debateId);
      const debateEvents = await getDebateEvents(debateId);
      setStatus(debate.status);
      setProposal(debate.proposal);
      setEvents(debateEvents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load debate");
    }
  }, [debateId]);

  useEffect(() => {
    void loadData();
    const interval = setInterval(() => {
      void loadData();
    }, 3000);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <div className="grid" style={{ gap: 12 }}>
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>Debate {debateId}</h2>
          <Link href="/">Back to dashboard</Link>
        </div>
        <p>
          <strong>Status:</strong> {status}
        </p>
        <p className="muted">{proposal}</p>
        {error ? <p style={{ color: "#ff9ea8" }}>{error}</p> : null}
      </section>

      <section className="card">
        <h3 style={{ marginTop: 0 }}>Event Timeline</h3>
        <div className="grid">
          {events.map((event) => (
            <article key={event.seq} className="card" style={{ padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{event.event_type}</strong>
                <span className="muted">seq {event.seq}</span>
              </div>
              <pre
                style={{
                  margin: "8px 0 0",
                  whiteSpace: "pre-wrap",
                  fontSize: 12,
                  color: "#cdd7ff",
                }}
              >
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </article>
          ))}
          {events.length === 0 ? <p className="muted">No events yet.</p> : null}
        </div>
      </section>
    </div>
  );
}
