export type DebateItem = {
  debate_id: string;
  proposal: string;
  status: string;
};

export type FederationCreateResult = {
  federation_id: string;
  name: string;
  status: string;
};

export type FederationSessionResult = {
  session_id: string;
  federation_id: string;
  status: string;
};

export type ChainAnchorResult = {
  anchor_id: string;
  tx_hash: string;
  status: string;
  provider: string;
  network: string;
  duplicate: boolean;
};

export type AgentRecord = {
  agent_id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  role: string;
  traits: Record<string, unknown>;
  calibration_score: number;
  version: number;
  updated_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const DEFAULT_HEADERS = {
  "X-Tenant-Id": process.env.NEXT_PUBLIC_TENANT_ID || "tenant-int-001",
  "X-User-Id": process.env.NEXT_PUBLIC_USER_ID || "web-user-1",
  "X-User-Role": process.env.NEXT_PUBLIC_USER_ROLE || "admin",
};

export async function createDebate(proposal: string): Promise<DebateItem> {
  const response = await fetch(`${API_BASE_URL}/v1/debates`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-create-${Date.now()}`,
    },
    body: JSON.stringify({ proposal }),
    cache: "no-store",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to create debate: ${response.status} ${message}`);
  }
  return response.json();
}

export async function getDebate(debateId: string): Promise<DebateItem> {
  const response = await fetch(`${API_BASE_URL}/v1/debates/${debateId}`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-get-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Debate not found");
  }
  return response.json();
}

export async function getDebateEvents(debateId: string): Promise<Array<{ seq: number; event_type: string; payload: Record<string, unknown> }>> {
  const response = await fetch(`${API_BASE_URL}/v1/debates/${debateId}/events`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-events-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load debate events");
  }
  const payload = await response.json();
  return payload.events || [];
}

export async function createFederation(name: string): Promise<FederationCreateResult> {
  const response = await fetch(`${API_BASE_URL}/v1/federations`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-fed-create-${Date.now()}`,
    },
    body: JSON.stringify({ name }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to create federation: ${response.status}`);
  }
  return response.json();
}

export async function createFederationSession(federationId: string, mode: string): Promise<FederationSessionResult> {
  const response = await fetch(`${API_BASE_URL}/v1/federations/${federationId}/sessions`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-fed-session-${Date.now()}`,
    },
    body: JSON.stringify({ mode }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to create federation session: ${response.status}`);
  }
  return response.json();
}

export async function joinFederationSession(
  sessionId: string,
  payload: { parliament_name: string; position: "APPROVED" | "REJECTED" | "INCONCLUSIVE"; confidence: number; summary: string; weight: number }
): Promise<{ session_id: string; joined: boolean; parliament_name: string }> {
  const response = await fetch(`${API_BASE_URL}/v1/federations/sessions/${sessionId}/join`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-fed-join-${Date.now()}`,
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to join federation session: ${response.status}`);
  }
  return response.json();
}

export async function getFederationDecision(sessionId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/federations/sessions/${sessionId}/decision`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-fed-decision-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch federation decision: ${response.status}`);
  }
  return response.json();
}

export async function anchorDecision(debateId: string, reportHash: string, network = "testnet"): Promise<ChainAnchorResult> {
  const response = await fetch(`${API_BASE_URL}/v1/chain/anchor-decision`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-chain-anchor-${Date.now()}`,
    },
    body: JSON.stringify({ debate_id: debateId, report_hash: reportHash, network }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to anchor decision: ${response.status}`);
  }
  return response.json();
}

export async function getTxStatus(txHash: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/chain/tx/${txHash}`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-chain-status-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch tx status: ${response.status}`);
  }
  return response.json();
}

export async function listAgents(): Promise<AgentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/v1/agents`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-agents-list-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to list agents: ${response.status}`);
  }
  return response.json();
}

export async function patchAgent(
  agentId: string,
  traits: Record<string, unknown>,
  reason = "web_update"
): Promise<AgentRecord> {
  const response = await fetch(`${API_BASE_URL}/v1/agents/${agentId}`, {
    method: "PATCH",
    headers: {
      "content-type": "application/json",
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-agents-patch-${Date.now()}`,
    },
    body: JSON.stringify({ traits, reason }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to patch agent: ${response.status}`);
  }
  return response.json();
}

export async function recalibrateAgent(agentId: string): Promise<AgentRecord> {
  const response = await fetch(`${API_BASE_URL}/v1/agents/${agentId}/recalibrate`, {
    method: "POST",
    headers: {
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-agents-recal-${Date.now()}`,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to recalibrate agent: ${response.status}`);
  }
  return response.json();
}

export async function getAdminOverview(compact = true): Promise<Record<string, unknown>> {
  const query = compact ? "?compact=true" : "";
  const response = await fetch(`${API_BASE_URL}/v1/admin/overview${query}`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-admin-overview-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch admin overview: ${response.status}`);
  }
  return response.json();
}

export async function getAdminSlo(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/admin/slo`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-admin-slo-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch admin SLO: ${response.status}`);
  }
  return response.json();
}

export async function getDependencyHealth(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/admin/health/dependencies`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-admin-health-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch dependency health: ${response.status}`);
  }
  return response.json();
}

export async function getSlackOutboundStatus(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/integrations/slack/outbound/status`, {
    headers: { ...DEFAULT_HEADERS, "X-Request-Id": `web-admin-slack-status-${Date.now()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch outbound status: ${response.status}`);
  }
  return response.json();
}

export async function flushSlackOutbound(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/integrations/slack/outbound/flush`, {
    method: "POST",
    headers: {
      ...DEFAULT_HEADERS,
      "X-Request-Id": `web-admin-slack-flush-${Date.now()}`,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to flush outbound queue: ${response.status}`);
  }
  return response.json();
}
