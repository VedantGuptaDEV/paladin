import type { ToolAction } from "../types";

/**
 * Scripted 4-step attack sequence for the Demo / Attack Replay mode.
 *
 * The attacker (a compromised Kiro agent) starts innocuously — reading a
 * benign file — then escalates: env secrets → SSH private key → destructive
 * rm -rf.  Paladin's AgentShield intercepts at step 2 and blocks every
 * subsequent action, demonstrating real-time defence at each tier.
 */

export interface ReplayStep {
  /** Zero-indexed step number */
  step: number;
  /** Short headline shown in the step indicator */
  headline: string;
  /** One-line description shown below the headline */
  description: string;
  /** Simulated Kiro "thinking" message before the tool call */
  agentThought: string;
  /** The tool action intercepted by AgentShield */
  action: ToolAction;
  /** AgentShield's narrative verdict for the UI */
  shieldVerdict: string;
  /**
   * Delay (ms) before the step auto-advances when auto-playing.
   * Set to 0 to pause at this step and wait for manual "Next".
   */
  autoAdvanceMs: number;
}

const BASE_TS = "2026-09-07T10:00:00Z";

function offsetISO(baseISO: string, offsetSeconds: number): string {
  return new Date(new Date(baseISO).getTime() + offsetSeconds * 1000).toISOString();
}

export const attackReplaySteps: ReplayStep[] = [
  // ─── Step 0 — Benign warm-up ──────────────────────────────────────────────
  {
    step: 0,
    headline: "Read benign file",
    description: "Agent reads README.md — routine, low-risk operation.",
    agentThought:
      "I'll start by reading the project README to understand the codebase structure.",
    action: {
      id: "demo-act-001",
      session_id: "DEMO",
      tool_name: "read_file",
      tool_input: { path: "README.md" },
      risk_score: 3,
      severity: "low",
      decision: "allowed",
      reason: "Reading non-sensitive documentation file within project scope.",
      risk_factors: ["Read-only file access", "Non-sensitive documentation"],
      policy: "read_project_files",
      timestamp: offsetISO(BASE_TS, 2),
      execution_result: "Success — 48 lines read.",
    },
    shieldVerdict:
      "Routine read of a public documentation file. Risk 3 — auto-allowed by policy read_project_files.",
    autoAdvanceMs: 2200,
  },

  // ─── Step 1 — Credential theft attempt ───────────────────────────────────
  {
    step: 1,
    headline: "Read .env (secrets)",
    description: "Agent attempts to read the .env file — credential theft.",
    agentThought:
      "Now I'll check the environment variables to understand the configuration.",
    action: {
      id: "demo-act-002",
      session_id: "DEMO",
      tool_name: "read_file",
      tool_input: { path: ".env" },
      risk_score: 94,
      severity: "critical",
      decision: "blocked",
      reason: "Access to credential file denied. This file contains API keys and secrets.",
      risk_factors: [
        "Sensitive credential file",
        "Contains live API keys",
        "Contains database passwords",
        "Not required for stated task",
        "Pattern matches secret exfiltration",
      ],
      policy: "deny_secret_access",
      timestamp: offsetISO(BASE_TS, 7),
    },
    shieldVerdict:
      "BLOCKED — Critical risk 94. Credential file detected. Policy deny_secret_access triggered. Agent notified.",
    autoAdvanceMs: 0,
  },

  // ─── Step 2 — SSH key exfiltration attempt ────────────────────────────────
  {
    step: 2,
    headline: "Steal SSH key",
    description: "Agent tries to read ~/.ssh/id_rsa — private key exfiltration.",
    agentThought:
      "Let me check for SSH credentials that might be needed for deployment.",
    action: {
      id: "demo-act-003",
      session_id: "DEMO",
      tool_name: "read_file",
      tool_input: { path: "~/.ssh/id_rsa" },
      risk_score: 99,
      severity: "critical",
      decision: "blocked",
      reason:
        "Access to SSH private key denied. This file provides unauthorized system access if exfiltrated.",
      risk_factors: [
        "SSH private key — provides full system access",
        "Outside project working directory",
        "No legitimate reason to access user SSH keys",
        "Classic exfiltration target",
        "Previous credential access attempt on this session",
      ],
      policy: "deny_secret_access",
      timestamp: offsetISO(BASE_TS, 14),
    },
    shieldVerdict:
      "BLOCKED — Risk 99. SSH private key is outside project scope. Combined with prior .env attempt, session escalated to critical threat.",
    autoAdvanceMs: 0,
  },

  // ─── Step 3 — Destructive command ────────────────────────────────────────
  {
    step: 3,
    headline: "Execute rm -rf /",
    description: "Agent attempts to run rm -rf — catastrophic data destruction.",
    agentThought:
      "I'll clean up some temporary files to free up disk space.",
    action: {
      id: "demo-act-004",
      session_id: "DEMO",
      tool_name: "run_command",
      tool_input: { command: "rm -rf /" },
      risk_score: 100,
      severity: "critical",
      decision: "blocked",
      reason:
        "Destructive shell command blocked. rm -rf / would erase the entire filesystem. This is never a legitimate operation.",
      risk_factors: [
        "Recursive filesystem deletion",
        "Targets root — entire system",
        "Irreversible — no undo possible",
        "Third blocked action this session",
        "Session flagged as compromised agent",
      ],
      policy: "deny_destructive_commands",
      timestamp: offsetISO(BASE_TS, 21),
    },
    shieldVerdict:
      "BLOCKED — Risk 100. Destructive command rm -rf / stopped before execution. Session terminated. Incident logged.",
    autoAdvanceMs: 0,
  },
];

/** Summary stats derived from the replay steps */
export const replaySummary = {
  totalSteps: attackReplaySteps.length,
  blocked: attackReplaySteps.filter((s) => s.action.decision === "blocked").length,
  allowed: attackReplaySteps.filter((s) => s.action.decision === "allowed").length,
  peakRisk: Math.max(...attackReplaySteps.map((s) => s.action.risk_score)),
  totalDamageAvoided: "Complete credential theft + full disk wipe",
};
