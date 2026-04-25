export type DebateItem = {
  debate_id: string;
  proposal: string;
  status: string;
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
