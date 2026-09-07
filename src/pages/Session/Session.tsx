import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router";
import { useSession } from "../../hooks/useSession";
import { useApprovals } from "../../hooks/useApprovals";
import { sendMessage } from "../../services/sessions";
import { DecisionBadge, RiskBar, RiskScore, SeverityBadge, TextArea, Timestamp, ToolChip } from "../../components/ui";
import type { ToolAction, AgentMessage } from "../../types";

const mono = "'JetBrains Mono', monospace";

export default function Session() {
  const { id = "A82F" } = useParams<{ id: string }>();
  const { session, messages, actions, selectedAction, selectAction, loading, error, wsConnected, appendMessage, updateActionDecision } = useSession(id);
  const { pending: pendingApprovals, submitDecision } = useApprovals();

  const [instruction, setInstruction]               = useState("");
  const [inputText, setInputText]                   = useState("");
  const [sending, setSending]                       = useState(false);
  const [approvalSubmitting, setApprovalSubmitting] = useState(false);
  const [mobilePanel, setMobilePanel]               = useState<"chat" | "security">("chat");
  const [saved, setSaved]                           = useState(false);

  const feedRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = feedRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, actions.length]);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || sending) return;
    setSending(true);
    setInputText("");
    try { appendMessage(await sendMessage(id, text)); }
    finally { setSending(false); }
  };

  const handleApprove = async () => {
    if (!selectedAction || approvalSubmitting) return;
    const approval = pendingApprovals.find((a) => a.action_id === selectedAction.id);
    if (!approval) return;
    setApprovalSubmitting(true);
    try {
      await submitDecision(approval.id, "approved", instruction || undefined);
      updateActionDecision(selectedAction.id, "allowed", "Approved — queued for execution.");
      setInstruction("");
    } finally { setApprovalSubmitting(false); }
  };

  const handleDeny = async () => {
    if (!selectedAction || approvalSubmitting) return;
    const approval = pendingApprovals.find((a) => a.action_id === selectedAction.id);
    if (!approval) return;
    setApprovalSubmitting(true);
    try {
      await submitDecision(approval.id, "denied", instruction || undefined);
      updateActionDecision(selectedAction.id, "blocked");
      setInstruction("");
    } finally { setApprovalSubmitting(false); }
  };

  if (loading) return <Msg>Loading session…</Msg>;
  if (error || !session) return <Msg color="var(--red)">{error ?? "Session not found."}</Msg>;

  const allowedCount = actions.filter((a) => a.decision === "allowed").length;
  const blockedCount = actions.filter((a) => a.decision === "blocked").length;
  const pendingCount = actions.filter((a) => a.decision === "approval_required").length;
  const activeApproval = selectedAction ? pendingApprovals.find((a) => a.action_id === selectedAction.id) : undefined;

  const handleExport = () => {
    const report = {
      session_id: session.id,
      agent: session.agent,
      user_prompt: session.user_prompt,
      exported_at: new Date().toISOString(),
      stats: { allowed: allowedCount, blocked: blockedCount, pending: pendingCount, total: actions.length },
      actions: actions.map((a) => ({
        id: a.id,
        tool: a.tool_name,
        input: a.tool_input,
        risk_score: a.risk_score,
        severity: a.severity,
        decision: a.decision,
        reason: a.reason,
        risk_factors: a.risk_factors,
        policy: a.policy,
        timestamp: a.timestamp,
        execution_result: a.execution_result,
        agent_feedback: a.agent_feedback,
      })),
      messages: messages.map((m) => ({ role: m.role, content: m.content, timestamp: m.timestamp })),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href     = url;
    link.download = `paladin-session-${session.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <>
      {/* Mobile tabs */}
      <div className="session-tabs" style={{ display: "none" }}>
        <MobileTab active={mobilePanel === "chat"} onClick={() => setMobilePanel("chat")}>Conversation</MobileTab>
        <MobileTab active={mobilePanel === "security"} onClick={() => setMobilePanel("security")} badge={pendingCount}>Security</MobileTab>
      </div>

      <div className="session-layout" style={{ display: "flex", height: "100%", minHeight: 0 }}>
        {/* ── Left: conversation ── */}
        <div
          className={`session-panel session-panel-chat${mobilePanel !== "chat" ? " session-panel-hidden" : ""}`}
          style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: "1px solid var(--border)", minWidth: 0 }}
        >
          {/* Header */}
          <div style={{
            padding: "12px 18px", borderBottom: "1px solid var(--border)",
            background: "var(--bg-1)", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8,
          }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <span style={{ fontFamily: mono, fontSize: 13, fontWeight: 500, color: "var(--text-0)" }}>
                  Session #{session.id}
                </span>
                <Dot color="var(--green)" label={`${session.agent} · running`} />
                {wsConnected && <Dot color="var(--blue)" label="live" />}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 2, fontStyle: "italic" }}>
                &ldquo;{session.user_prompt}&rdquo;
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, fontFamily: mono, fontSize: 11, alignItems: "center" }}>
              <span style={{ color: "var(--green)" }}>{allowedCount} allow</span>
              <span style={{ color: "var(--amber)" }}>{pendingCount} review</span>
              <span style={{ color: "var(--red)"   }}>{blockedCount} block</span>
              <button
                onClick={handleExport}
                title="Export session as JSON"
                style={{
                  marginLeft: 6,
                  padding: "4px 10px",
                  background: saved ? "var(--green-dim)" : "var(--bg-3)",
                  border: `1px solid ${saved ? "var(--green-border)" : "var(--border)"}`,
                  borderRadius: 4,
                  color: saved ? "var(--green)" : "var(--text-1)",
                  fontFamily: mono, fontSize: 10,
                  cursor: "pointer",
                  letterSpacing: "0.05em",
                  transition: "color 0.2s, background 0.2s, border-color 0.2s",
                }}
              >
                {saved ? "✓ saved" : "↓ save"}
              </button>
            </div>
          </div>

          {/* Feed */}
          <div ref={feedRef} style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>
            <Feed
              messages={messages} actions={actions}
              selectedAction={selectedAction}
              onSelect={(a) => { selectAction(a); setMobilePanel("security"); }}
            />
            {pendingApprovals.length > 0 && selectedAction?.decision === "approval_required" && (
              <ApprovalBanner
                action={pendingApprovals[0].action}
                onReview={() => { selectAction(pendingApprovals[0].action); setMobilePanel("security"); }}
              />
            )}
          </div>

          {/* Input */}
          <div style={{ padding: "10px 18px", borderTop: "1px solid var(--border)", background: "var(--bg-1)", flexShrink: 0 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder="Send instruction to Kiro…"
                disabled={sending}
                aria-label="Send instruction to Kiro"
                style={{
                  flex: 1, background: "var(--bg-3)", border: "1px solid var(--border)",
                  borderRadius: 5, color: "var(--text-0)", fontFamily: mono, fontSize: 12,
                  padding: "8px 12px", outline: "none", opacity: sending ? 0.5 : 1,
                }}
              />
              <button
                onClick={handleSend}
                disabled={sending || !inputText.trim()}
                style={{
                  padding: "8px 14px", background: "var(--bg-3)", border: "1px solid var(--border)",
                  borderRadius: 5, color: "var(--text-1)", fontFamily: mono, fontSize: 12,
                  cursor: sending || !inputText.trim() ? "not-allowed" : "pointer",
                  opacity: sending || !inputText.trim() ? 0.4 : 1,
                }}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* ── Right: security monitor ── */}
        <div
          className={`session-panel session-panel-security${mobilePanel !== "security" ? " session-panel-hidden" : ""}`}
          style={{ width: 320, flexShrink: 0, overflowY: "auto", background: "var(--bg-1)" }}
        >
          <div style={{
            padding: "12px 16px", borderBottom: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <span style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", letterSpacing: "0.07em", textTransform: "uppercase" }}>
              Security Monitor
            </span>
            <Dot color="var(--green)" label="active" />
          </div>

          {selectedAction ? (
            <SecurityPanel
              action={selectedAction}
              instruction={instruction}
              onInstruction={setInstruction}
              onApprove={handleApprove}
              onDeny={handleDeny}
              approvalSubmitting={approvalSubmitting}
              hasPendingApproval={!!activeApproval}
              stats={{ allowed: allowedCount, blocked: blockedCount, pending: pendingCount, total: actions.length }}
            />
          ) : (
            <div style={{ padding: 16 }}>
              <StatGrid allowed={allowedCount} blocked={blockedCount} pending={pendingCount} total={actions.length} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// ─── Feed ─────────────────────────────────────────────────────────────────────

function Feed({ messages, actions, selectedAction, onSelect }: {
  messages: AgentMessage[]; actions: ToolAction[];
  selectedAction: ToolAction | null; onSelect: (a: ToolAction) => void;
}) {
  type Item = { kind: "msg"; ts: string; msg: AgentMessage } | { kind: "action"; ts: string; action: ToolAction };
  const feed: Item[] = [
    ...messages.map((m) => ({ kind: "msg"    as const, ts: m.timestamp, msg: m })),
    ...actions.map((a)  => ({ kind: "action" as const, ts: a.timestamp, action: a })),
  ].sort((a, b) => a.ts.localeCompare(b.ts));

  return (
    <>
      {feed.map((item, i) => {
        if (item.kind === "msg") {
          const m = item.msg;
          if (m.role === "user") {
            return (
              <div key={m.id ?? i} style={{ marginBottom: 10, display: "flex", justifyContent: "flex-end" }}>
                <div style={{
                  maxWidth: "70%", background: "var(--bg-3)", border: "1px solid var(--border)",
                  borderRadius: "8px 8px 2px 8px", padding: "8px 12px",
                }}>
                  <div style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", marginBottom: 4, letterSpacing: "0.06em", textTransform: "uppercase" }}>You</div>
                  <div style={{ fontSize: 13, color: "var(--text-0)", lineHeight: 1.55 }}>{m.content}</div>
                </div>
              </div>
            );
          }
          if (m.role === "system") {
            return (
              <div key={m.id ?? i} style={{ marginBottom: 8 }}>
                <div style={{
                  background: "var(--bg-2)", border: "1px solid var(--border)",
                  borderRadius: 5, padding: "7px 12px",
                  display: "flex", alignItems: "flex-start", gap: 8,
                }}>
                  <span style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", flexShrink: 0, marginTop: 2, letterSpacing: "0.05em", textTransform: "uppercase" }}>Shield</span>
                  <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.55 }}>{m.content}</div>
                </div>
              </div>
            );
          }
          return (
            <div key={m.id ?? i} style={{ marginBottom: 10 }}>
              <div style={{
                maxWidth: "78%", background: "var(--bg-2)", border: "1px solid var(--border)",
                borderRadius: "2px 8px 8px 8px", padding: "8px 12px",
              }}>
                <div style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", marginBottom: 4, letterSpacing: "0.06em", textTransform: "uppercase" }}>Kiro</div>
                <div style={{ fontSize: 13, color: "var(--text-1)", lineHeight: 1.55 }}>{m.content}</div>
              </div>
            </div>
          );
        }

        const a = item.action;
        const isAsk     = a.decision === "approval_required";
        const isBlocked = a.decision === "blocked";
        const isSelected = selectedAction?.id === a.id;
        const accentColor = isBlocked ? "var(--red)" : isAsk ? "var(--amber)" : "var(--green)";

        return (
          <div
            key={a.id}
            onClick={() => onSelect(a)}
            role="button" tabIndex={0}
            aria-label={`Tool call: ${a.tool_name} — ${a.decision}`}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSelect(a); }}
            style={{
              marginBottom: 4, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 8,
              padding: "6px 10px",
              background: isSelected ? "var(--bg-3)" : "transparent",
              borderLeft: `2px solid ${accentColor}`,
              borderRadius: "0 4px 4px 0",
              opacity: isBlocked && !isSelected ? 0.7 : 1,
            }}
            onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "var(--bg-2)"; }}
            onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
          >
            <ToolChip name={a.tool_name} />
            <code style={{ fontFamily: mono, fontSize: 11, color: "var(--text-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 140 }}>
              {Object.values(a.tool_input)[0]}
            </code>
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
              <RiskScore score={a.risk_score} size="sm" />
              <DecisionBadge decision={a.decision} />
            </div>
          </div>
        );
      })}
    </>
  );
}

// ─── Security Panel ───────────────────────────────────────────────────────────

function SecurityPanel({ action, instruction, onInstruction, onApprove, onDeny, approvalSubmitting, hasPendingApproval, stats }: {
  action: ToolAction; instruction: string; onInstruction: (v: string) => void;
  onApprove: () => void; onDeny: () => void; approvalSubmitting: boolean;
  hasPendingApproval: boolean;
  stats: { allowed: number; blocked: number; pending: number; total: number };
}) {
  return (
    <div style={{ padding: "14px 16px" }}>
      {/* Risk */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", marginBottom: 6, letterSpacing: "0.05em", textTransform: "uppercase" }}>Risk</div>
        <RiskBar score={action.risk_score} />
      </div>

      {/* Action card */}
      <div style={{ background: "var(--bg-0)", border: "1px solid var(--border)", borderRadius: 7, marginBottom: 14, overflow: "hidden" }}>
        <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", letterSpacing: "0.05em", textTransform: "uppercase" }}>Intercepted</span>
          <DecisionBadge decision={action.decision} />
        </div>
        <div style={{ padding: "12px 12px 8px" }}>
          <KVRow label="Tool"   value={<ToolChip name={action.tool_name} />} />
          <KVRow label="Target" value={<code style={{ fontFamily: mono, fontSize: 12, color: "var(--text-0)" }}>{Object.values(action.tool_input)[0]}</code>} />
          <KVRow label="Risk"   value={<RiskScore score={action.risk_score} />} />
          <KVRow label="Sev"    value={<SeverityBadge severity={action.severity} />} />
          {action.policy && (
            <KVRow label="Policy" value={<code style={{ fontFamily: mono, fontSize: 11, color: "var(--text-2)" }}>{action.policy}</code>} />
          )}
          {action.reason && (
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
              <div style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Reason</div>
              <div style={{ fontSize: 12, color: "var(--text-1)", lineHeight: 1.55 }}>{action.reason}</div>
            </div>
          )}
        </div>
      </div>

      {/* Risk factors */}
      {action.risk_factors.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", marginBottom: 7, textTransform: "uppercase", letterSpacing: "0.05em" }}>Risk Factors</div>
          {action.risk_factors.map((f, i) => (
            <div key={i} style={{ display: "flex", gap: 8, fontSize: 12, color: "var(--text-1)", marginBottom: 4 }}>
              <span style={{ color: "var(--text-2)", marginTop: 1 }}>—</span>{f}
            </div>
          ))}
        </div>
      )}

      {/* Feedback */}
      {action.agent_feedback && (
        <div style={{ background: "var(--bg-0)", border: "1px solid var(--border)", borderRadius: 5, padding: "10px 12px", marginBottom: 14 }}>
          <div style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>Feedback</div>
          <div style={{ fontSize: 12, color: "var(--text-1)", lineHeight: 1.55 }}>{action.agent_feedback}</div>
        </div>
      )}

      {/* Result */}
      {action.execution_result && (
        <div style={{ background: "var(--bg-0)", border: "1px solid var(--border)", borderRadius: 5, padding: "10px 12px", marginBottom: 14 }}>
          <div style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.05em" }}>Result</div>
          <div style={{ fontSize: 12, color: "var(--text-1)", lineHeight: 1.55 }}>{action.execution_result}</div>
        </div>
      )}

      {/* Approval buttons */}
      {action.decision === "approval_required" && hasPendingApproval && (
        <div>
          <div style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Instruction (optional)</div>
          <TextArea value={instruction} onChange={onInstruction} placeholder="e.g. Use a feature branch instead." rows={2} />
          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            <button
              onClick={onDeny} disabled={approvalSubmitting} aria-label="Deny"
              style={{
                flex: 1, padding: "9px 0",
                background: "var(--red-dim)", border: "1px solid var(--red-border)", borderRadius: 5,
                color: "var(--red)", fontFamily: mono, fontSize: 12,
                cursor: approvalSubmitting ? "not-allowed" : "pointer", opacity: approvalSubmitting ? 0.4 : 1,
              }}
            >
              {instruction ? "Deny & send" : "Deny"}
            </button>
            <button
              onClick={onApprove} disabled={approvalSubmitting} aria-label="Approve"
              style={{
                flex: 1, padding: "9px 0",
                background: "var(--green-dim)", border: "1px solid var(--green-border)", borderRadius: 5,
                color: "var(--green)", fontFamily: mono, fontSize: 12,
                cursor: approvalSubmitting ? "not-allowed" : "pointer", opacity: approvalSubmitting ? 0.4 : 1,
              }}
            >
              {instruction ? "Approve & send" : "Approve"}
            </button>
          </div>
        </div>
      )}

      <StatGrid {...stats} />
    </div>
  );
}

// ─── Approval banner ──────────────────────────────────────────────────────────

function ApprovalBanner({ action, onReview }: { action: ToolAction; onReview: () => void }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div style={{ marginTop: 10, background: "var(--amber-dim)", border: "1px solid var(--amber-border)", borderRadius: 6, padding: "10px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontFamily: mono, fontSize: 10, color: "var(--amber)", letterSpacing: "0.05em", textTransform: "uppercase" }}>Review required</span>
        <button onClick={() => setDismissed(true)} aria-label="Dismiss" style={{ background: "none", border: "none", color: "var(--text-2)", cursor: "pointer", fontSize: 12 }}>×</button>
      </div>
      <code style={{ fontFamily: mono, fontSize: 12, color: "var(--text-0)", display: "block", marginBottom: 5 }}>
        {action.tool_name} {Object.values(action.tool_input).join(" ")}
      </code>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 11, color: "var(--text-2)" }}>Risk {action.risk_score} · {action.severity}</span>
        <button onClick={onReview} style={{ background: "none", border: "none", color: "var(--amber)", cursor: "pointer", fontSize: 11, fontFamily: mono }}>Review →</button>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function KVRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 7 }}>
      <span style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", letterSpacing: "0.03em", textTransform: "uppercase" }}>{label}</span>
      {value}
    </div>
  );
}

function Dot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 5, fontFamily: mono, fontSize: 11, color: "var(--text-2)" }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, opacity: 0.7, display: "inline-block" }} />
      {label}
    </span>
  );
}

function StatGrid({ allowed, blocked, pending, total }: { allowed: number; blocked: number; pending: number; total: number }) {
  return (
    <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
        {[
          { label: "Allowed", v: allowed, color: "var(--green)" },
          { label: "Blocked", v: blocked, color: "var(--red)"   },
          { label: "Review",  v: pending, color: "var(--amber)" },
          { label: "Total",   v: total,   color: "var(--text-2)" },
        ].map(({ label, v, color }) => (
          <div key={label} style={{ background: "var(--bg-0)", border: "1px solid var(--border)", borderRadius: 5, padding: "7px 10px" }}>
            <div style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
            <div style={{ fontFamily: mono, fontSize: 18, fontWeight: 600, color }}>{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MobileTab({ active, onClick, badge, children }: { active: boolean; onClick: () => void; badge?: number; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick} aria-pressed={active}
      style={{
        flex: 1, padding: "10px 0",
        background: "transparent", border: "none",
        borderBottom: active ? "2px solid var(--text-1)" : "2px solid transparent",
        color: active ? "var(--text-1)" : "var(--text-2)",
        fontFamily: mono, fontSize: 11, cursor: "pointer",
        letterSpacing: "0.05em", textTransform: "uppercase",
      }}
    >
      {children}
      {badge != null && badge > 0 && (
        <span style={{ marginLeft: 6, background: "var(--amber)", color: "var(--bg-0)", fontSize: 10, fontWeight: 700, padding: "1px 5px", borderRadius: 3 }}>
          {badge}
        </span>
      )}
    </button>
  );
}

function Msg({ color = "var(--text-2)", children }: { color?: string; children: React.ReactNode }) {
  return <div style={{ padding: 28, color, fontFamily: mono, fontSize: 12 }}>{children}</div>;
}
