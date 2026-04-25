"use client";

import { useEffect, useState } from "react";
import {
  createAdminApiKey,
  getAdminPolicy,
  getAdminUsage,
  listAdminApiKeys,
  revokeAdminApiKey,
  type AdminApiKeyRecord,
} from "../../lib/api";

export default function AdminPage() {
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null);
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [apiKeys, setApiKeys] = useState<AdminApiKeyRecord[]>([]);
  const [newKeyName, setNewKeyName] = useState("Control Room Key");
  const [newKeyScopes, setNewKeyScopes] = useState("read:debates,write:debates");
  const [newRawKey, setNewRawKey] = useState("");
  const [error, setError] = useState("");

  async function loadAll(): Promise<void> {
    try {
      setError("");
      const [usagePayload, policyPayload, keyRows] = await Promise.all([
        getAdminUsage(24),
        getAdminPolicy(),
        listAdminApiKeys(),
      ]);
      setUsage(usagePayload);
      setPolicy(policyPayload);
      setApiKeys(keyRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load admin data");
    }
  }

  useEffect(() => {
    void loadAll();
  }, []);

  async function onCreateKey(): Promise<void> {
    try {
      const scopes = newKeyScopes
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const response = await createAdminApiKey(newKeyName, scopes);
      setNewRawKey(String(response.raw_key || ""));
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create key");
    }
  }

  async function onRevokeKey(keyId: string): Promise<void> {
    try {
      await revokeAdminApiKey(keyId);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke key");
    }
  }

  return (
    <div className="grid">
      <section className="card">
        <h2 style={{ marginTop: 0 }}>Admin Policy</h2>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(policy || {}, null, 2)}</pre>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Usage Summary (24h)</h2>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(usage?.summary || {}, null, 2)}</pre>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>API Keys</h2>
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "1fr 1fr" }}>
          <input
            className="input"
            value={newKeyName}
            onChange={(event) => setNewKeyName(event.target.value)}
            placeholder="Key name"
          />
          <input
            className="input"
            value={newKeyScopes}
            onChange={(event) => setNewKeyScopes(event.target.value)}
            placeholder="comma-separated scopes"
          />
        </div>
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          <button className="button" onClick={() => void onCreateKey()}>
            Create API Key
          </button>
          <button className="button" onClick={() => void loadAll()}>
            Refresh
          </button>
        </div>
        {newRawKey ? (
          <p className="muted" style={{ marginTop: 8 }}>
            New key (shown once): <code>{newRawKey}</code>
          </p>
        ) : null}
        <div className="grid" style={{ marginTop: 10 }}>
          {apiKeys.map((item) => (
            <article key={item.key_id} className="card" style={{ padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>{item.name}</strong>
                <span className="muted">{item.status}</span>
              </div>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                {item.key_prefix}... | scopes: {item.scopes.join(", ")}
              </p>
              <p className="muted" style={{ margin: "8px 0 0" }}>
                created by {item.created_by} at {item.created_at}
              </p>
              {item.status !== "revoked" ? (
                <div style={{ marginTop: 8 }}>
                  <button className="button" onClick={() => void onRevokeKey(item.key_id)}>
                    Revoke
                  </button>
                </div>
              ) : null}
            </article>
          ))}
          {!apiKeys.length ? <p className="muted">No API keys yet.</p> : null}
        </div>
      </section>

      {error ? <p style={{ color: "#ff9ea8" }}>{error}</p> : null}
    </div>
  );
}
