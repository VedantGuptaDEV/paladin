/**
 * Activity service — wraps audit event API calls.
 *
 * Always reads from trialHack_output.csv (served from /public).
 */

import { fetchCsvRows, rowsToAuditEvents } from "./csvService";
import type { AuditEvent, AuditEventType } from "../types";

export async function getAuditEvents(
  _sessionId?: string,
  filter?: AuditEventType[],
): Promise<AuditEvent[]> {
  const rows = await fetchCsvRows();
  let events = rowsToAuditEvents(rows);

  if (filter && filter.length > 0) {
    events = events.filter((e) => filter.includes(e.event_type));
  }

  return events;
}
