"use client";

import Link from "next/link";
import { useState } from "react";
import { createDebate } from "../lib/api";

export default function DashboardPage() {
  const [proposal, setProposal] = useState("Adopt weekly async planning sync with reliability review.");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<{ debate_id: string; proposal: string; status: string } | null>(null);

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

  return (
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
  );
}
