/**
 * Actions service — wraps ToolAction-related API calls.
 *
 * Always reads from trialHack_output.csv (served from /public).
 */

import { fetchCsvRows, rowsToActions } from "./csvService";
import type { ToolAction } from "../types";

export async function getActions(_sessionId?: string): Promise<ToolAction[]> {
  const rows = await fetchCsvRows();
  const actions = rowsToActions(rows);
  // Return newest-first for the live activity feed
  return actions.slice().reverse();
}

export async function getAction(actionId: string): Promise<ToolAction> {
  const actions = await getActions();
  const action = actions.find((a) => a.id === actionId);
  if (!action) throw new Error(`Action ${actionId} not found`);
  return action;
}
