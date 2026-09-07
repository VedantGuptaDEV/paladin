/**
 * Session service — wraps all session-related API calls.
 *
 * Mock mode: returns data from src/mock/.
 * Real mode: calls FastAPI /sessions endpoints.
 * CSV mode:  derives stats from trialHack_output.csv (served from /public).
 */

import { USE_MOCK, get, post } from "./api";
import { fetchCsvRows, rowsToStats, rowsToRiskHistory } from "./csvService";
import type { Session, AgentMessage } from "../types";
import { mockSession, mockMessages } from "../mock";

// ─── Sessions ─────────────────────────────────────────────────────────────────

export async function getSessions(): Promise<Session[]> {
  if (USE_MOCK) return [mockSession];
  return get<Session[]>("/sessions");
}

export async function getSession(id: string): Promise<Session> {
  if (USE_MOCK) {
    if (id === mockSession.id) return mockSession;
    throw new Error(`Session ${id} not found`);
  }
  return get<Session>(`/sessions/${id}`);
}

export async function createSession(userPrompt: string): Promise<Session> {
  if (USE_MOCK) {
    return { ...mockSession, id: `SES${Date.now()}`, user_prompt: userPrompt };
  }
  return post<Session>("/sessions", { user_prompt: userPrompt });
}

// ─── Messages ─────────────────────────────────────────────────────────────────

export async function getMessages(sessionId: string): Promise<AgentMessage[]> {
  if (USE_MOCK) return mockMessages.filter((m) => m.session_id === sessionId);
  return get<AgentMessage[]>(`/sessions/${sessionId}/messages`);
}

export async function sendMessage(sessionId: string, content: string): Promise<AgentMessage> {
  if (USE_MOCK) {
    return {
      id: `msg-${Date.now()}`,
      session_id: sessionId,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
  }
  return post<AgentMessage>(`/sessions/${sessionId}/messages`, { content });
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export async function getDashboardStats() {
  const rows = await fetchCsvRows();
  return rowsToStats(rows);
}

export async function getRiskHistory() {
  const rows = await fetchCsvRows();
  return rowsToRiskHistory(rows);
}
