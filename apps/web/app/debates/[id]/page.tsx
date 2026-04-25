"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
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
  const [eventTypeFilter, setEventTypeFilter] = useState("all");
  const [replaySeq, setReplaySeq] = useState(0);

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

  const eventTypes = useMemo(() => {
    const unique = new Set(events.map((event) => event.event_type));
    return ["all", ...Array.from(unique)];
  }, [events]);

  const filteredEvents = useMemo(() => {
    if (eventTypeFilter === "all") {
      return events;
    }
    return events.filter((event) => event.event_type === eventTypeFilter);
  }, [eventTypeFilter, events]);

  const replayIndex = useMemo(() => {
    if (!filteredEvents.length) {
      return 0;
    }
    const seqs = filteredEvents.map((event) => event.seq);
    const explicit = filteredEvents.findIndex((event) => event.seq === replaySeq);
    if (explicit >= 0) {
      return explicit;
    }
    const nearest = seqs.findIndex((seq) => seq >= replaySeq);
    return nearest >= 0 ? nearest : filteredEvents.length - 1;
  }, [filteredEvents, replaySeq]);

  const replayEvent = filteredEvents[replayIndex] || null;

  const consensusEvent = useMemo(
    () => [...events].reverse().find((event) => event.event_type === "consensus_computed"),
    [events]
  );
  const decisionReportEvent = useMemo(
    () => [...events].reverse().find((event) => event.event_type === "decision_report_generated"),
    [events]
  );
  const evidenceEvent = useMemo(
    () => [...events].reverse().find((event) => event.event_type === "evidence_scored"),
    [events]
  );

  function replayNext() {
    if (!filteredEvents.length) {
      return;
    }
    const nextIndex = Math.min(filteredEvents.length - 1, replayIndex + 1);
    setReplaySeq(filteredEvents[nextIndex].seq);
  }

  function replayPrev() {
    if (!filteredEvents.length) {
      return;
    }
    const prevIndex = Math.max(0, replayIndex - 1);
    setReplaySeq(filteredEvents[prevIndex].seq);
  }

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
        <h3 style={{ marginTop: 0 }}>Decision Report</h3>
        <div className="grid grid-2">
          <article className="card" style={{ padding: 12 }}>
            <strong>Consensus</strong>
            <pre style={{ margin: "8px 0 0", whiteSpace: "pre-wrap", fontSize: 12, color: "#cdd7ff" }}>
              {JSON.stringify(consensusEvent?.payload || { status: "pending" }, null, 2)}
            </pre>
          </article>
          <article className="card" style={{ padding: 12 }}>
            <strong>Decision Report</strong>
            <pre style={{ margin: "8px 0 0", whiteSpace: "pre-wrap", fontSize: 12, color: "#cdd7ff" }}>
              {JSON.stringify(decisionReportEvent?.payload || { status: "pending" }, null, 2)}
            </pre>
          </article>
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>
          Evidence snapshot: {JSON.stringify(evidenceEvent?.payload || { evidence_score: "n/a" })}
        </p>
      </section>

      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h3 style={{ margin: 0 }}>Replay Timeline</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="muted">Filter:</span>
            <select
              className="select"
              style={{ width: 240 }}
              value={eventTypeFilter}
              onChange={(event) => {
                setEventTypeFilter(event.target.value);
                setReplaySeq(0);
              }}
            >
              {eventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {eventType}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="card" style={{ marginTop: 12, padding: 12 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <button className="button" style={{ width: "auto" }} onClick={replayPrev}>
              Prev
            </button>
            <button className="button" style={{ width: "auto" }} onClick={replayNext}>
              Next
            </button>
            <span className="muted" style={{ alignSelf: "center" }}>
              {replayEvent ? `Replay seq ${replayEvent.seq} (${replayIndex + 1}/${filteredEvents.length})` : "No replay event"}
            </span>
          </div>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12, color: "#cdd7ff" }}>
            {JSON.stringify(replayEvent?.payload || {}, null, 2)}
          </pre>
        </div>
        <div className="grid">
          {filteredEvents.map((event) => (
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
          {filteredEvents.length === 0 ? <p className="muted">No events for selected filter.</p> : null}
        </div>
      </section>
    </div>
  );
}
