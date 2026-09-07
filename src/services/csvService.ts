/**
 * csvService — fetches /trialHack_output.csv (served from public/) and parses
 * it into the app's internal data shapes.
 *
 * CSV columns:
 *   timestamp, raw_prompt, action_type, target, agent, sensitivity,
 *   target_category, cwd, risk_score
 */

import type { ToolAction, Decision, Severity } from "../types";
import type { AuditEvent } from "../types";

const CSV_URL = "/trialHack_output.csv";

// ─── Raw CSV row ──────────────────────────────────────────────────────────────

export interface CsvRow {
  timestamp: string;
  raw_prompt: string;
  action_type: string;
  target: string;
  agent: string;
  sensitivity: string;
  target_category: string;
  cwd: string;
  risk_score: number | null;
}

// ─── Parsing helpers ──────────────────────────────────────────────────────────

function parseCsv(text: string): CsvRow[] {
  const lines = text.trim().split("\n");
  if (lines.length < 2) return [];

  // First line is header
  const headers = lines[0].split(",").map((h) => h.trim());
  const rows: CsvRow[] = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    const values = line.split(",");
    const raw: Record<string, string> = {};
    headers.forEach((h, idx) => {
      raw[h] = (values[idx] ?? "").trim();
    });

    rows.push({
      timestamp: raw["timestamp"] ?? "",
      raw_prompt: raw["raw_prompt"] ?? "",
      action_type: raw["action_type"] ?? "",
      target: raw["target"] ?? "",
      agent: raw["agent"] ?? "",
      sensitivity: raw["sensitivity"] ?? "",
      target_category: raw["target_category"] ?? "",
      cwd: raw["cwd"] ?? "",
      risk_score: raw["risk_score"] ? parseFloat(raw["risk_score"]) : null,
    });
  }

  // Sort ascending by timestamp so latest is last
  rows.sort((a, b) => (a.timestamp > b.timestamp ? 1 : -1));
  return rows;
}

/** Derive a Decision from action_type + risk_score */
function deriveDecision(row: CsvRow): Decision {
  const score = row.risk_score ?? 0;
  const action = row.action_type.toLowerCase();

  // High-risk actions or high scores get blocked
  if (score >= 70) return "blocked";
  // Medium-risk or destructive actions go to review
  if (score >= 40 || action === "delete" || action === "overwrite") return "approval_required";
  // Everything else is allowed
  return "allowed";
}

/** Derive a Severity from risk_score */
function deriveSeverity(score: number | null): Severity {
  const s = score ?? 0;
  if (s >= 80) return "critical";
  if (s >= 50) return "high";
  if (s >= 25) return "medium";
  return "low";
}

// ─── Public API ───────────────────────────────────────────────────────────────

/** Fetch and parse the CSV, returning raw rows. Throws on network error. */
export async function fetchCsvRows(): Promise<CsvRow[]> {
  const res = await fetch(CSV_URL, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch CSV: ${res.status}`);
  const text = await res.text();
  return parseCsv(text);
}

/** Convert CSV rows → ToolAction list (for Dashboard live activity + actions service). */
export function rowsToActions(rows: CsvRow[]): ToolAction[] {
  return rows.map((row, i) => {
    const decision = deriveDecision(row);
    const riskScore = row.risk_score ?? 0;
    const severity = deriveSeverity(row.risk_score);

    return {
      id: `csv-${i}`,
      session_id: "A82F",
      tool_name: row.action_type || "unknown",
      tool_input: {
        prompt: row.raw_prompt,
        ...(row.target ? { target: row.target } : {}),
        ...(row.cwd ? { cwd: row.cwd } : {}),
      },
      risk_score: riskScore,
      severity,
      decision,
      reason: decision === "blocked"
        ? "High risk score detected by Paladin engine."
        : decision === "approval_required"
        ? "Potentially destructive operation flagged for review."
        : "Action within acceptable risk threshold.",
      risk_factors: [
        ...(row.sensitivity && row.sensitivity !== "normal" ? [`Sensitivity: ${row.sensitivity}`] : []),
        ...(row.target_category ? [`Category: ${row.target_category}`] : []),
      ],
      policy: decision === "blocked" ? "auto_block_high_risk" : "default_policy",
      timestamp: row.timestamp,
    };
  });
}

/** Convert CSV rows → AuditEvent list (for Activity page). */
export function rowsToAuditEvents(rows: CsvRow[]): AuditEvent[] {
  const events: AuditEvent[] = [];

  rows.forEach((row, i) => {
    const decision = deriveDecision(row);
    const riskScore = row.risk_score ?? 0;

    // Tool request event (the actual action Kiro took)
    events.push({
      id: `evt-csv-tool-${i}`,
      session_id: "A82F",
      event_type: "tool_request",
      timestamp: row.timestamp,
      actor: "KIRO",
      summary: row.raw_prompt
        ? `${row.action_type}("${row.raw_prompt}")`
        : row.action_type,
      metadata: {
        tool: row.action_type,
        args: {
          prompt: row.raw_prompt,
          ...(row.target ? { target: row.target } : {}),
          ...(row.cwd ? { cwd: row.cwd } : {}),
        },
      },
    });

    // Shield decision event — only if there was an actual risk evaluation
    if (row.risk_score !== null) {
      const decisionLabel =
        decision === "blocked"
          ? "BLOCKED"
          : decision === "approval_required"
          ? "APPROVAL REQUIRED"
          : "ALLOWED";

      events.push({
        id: `evt-csv-shield-${i}`,
        session_id: "A82F",
        event_type: "shield_decision",
        timestamp: row.timestamp,
        actor: "AGENTSHIELD",
        summary: `${decisionLabel} — Risk ${riskScore.toFixed(0)} — ${row.action_type}`,
        metadata: {
          decision,
          risk_score: riskScore,
          policy: decision === "blocked" ? "auto_block_high_risk" : "default_policy",
          risk_factors: [
            ...(row.sensitivity && row.sensitivity !== "normal"
              ? [`Sensitivity: ${row.sensitivity}`]
              : []),
            ...(row.target_category ? [`Category: ${row.target_category}`] : []),
          ],
        },
      });
    }
  });

  // Return sorted newest-first for Activity feed
  return events.sort((a, b) => (a.timestamp > b.timestamp ? -1 : 1));
}

/** Compute dashboard stats from CSV rows. */
export function rowsToStats(rows: CsvRow[]) {
  const actions = rowsToActions(rows);
  const total = actions.length;

  const allowed = actions.filter((a) => a.decision === "allowed").length;
  const approval_required = actions.filter((a) => a.decision === "approval_required").length;
  const blocked = actions.filter((a) => a.decision === "blocked").length;

  const scoresWithValues = actions
    .map((a) => a.risk_score)
    .filter((s) => s > 0);

  const avg_risk =
    scoresWithValues.length > 0
      ? Math.round(scoresWithValues.reduce((s, v) => s + v, 0) / scoresWithValues.length)
      : 0;

  return {
    actions_analyzed: total,
    allowed,
    approval_required,
    blocked,
    avg_risk,
  };
}

/** Build a risk-over-time series from CSV rows (for the MiniRiskChart). */
export function rowsToRiskHistory(rows: CsvRow[]) {
  return rows
    .filter((r) => r.risk_score !== null)
    .map((r) => ({
      time: r.timestamp.slice(11, 16), // "HH:MM"
      risk: r.risk_score as number,
    }));
}
