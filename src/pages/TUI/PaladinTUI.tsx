import React, { useState, useEffect, useRef, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type View = "session" | "dashboard" | "approvals" | "activity" | "policies" | "settings";

type MsgRole = "user" | "kiro" | "system" | "error" | "success" | "info";

interface ChatMessage {
  id: number;
  role: MsgRole;
  content: string;
  ts: string;
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const SHIELD_ART = `         ╭─────────────────────────╮
        ╱ ·   ·   ·   ·   ·   ·    ╲
       │  ·  ██████████  ·  ·   ·   │
       │  · ██  ·  ·  ██ ·  ·   ·   │
       │  · ██  ·  ·  ██ ·  ·   ·   │
       │  · ██████████  ·  ·   ·   · │
       │  · ██  ·  ·  ·  ·  ·   ·   │
       │  · ██  ·  ·  ·  ·  ·   ·   │
       │  ·  ·  ·  ·  ·  ·  ·   ·   │
       │      ╔═══════════════╗      │
       │      ║  P A L A D I N ║      │
       │      ╚═══════════════╝      │
        ╲  ·   ·   ·   ·   ·   ·   ╱
         ╰─────────────────────────╯`;

const WELCOME_MSG = `Welcome to [bold]Paladin AgentShield[/bold] — Runtime security for autonomous AI agents.
Type a query or use /help to see available commands.`;

function now(): string {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

let _id = 1;
function uid() { return _id++; }

// ─── Mock data ────────────────────────────────────────────────────────────────

const MOCK_APPROVALS = [
  { id: "APR001", tool: "bash", risk: 72, cmd: "rm -rf ./build", status: "pending" },
  { id: "APR002", tool: "write_file", risk: 45, cmd: "config.prod.yml", status: "pending" },
  { id: "APR003", tool: "curl", risk: 58, cmd: "POST /api/deploy", status: "pending" },
];

const MOCK_ACTIVITY = [
  { ts: "10:00:12", tool: "read_file",  decision: "allowed",           risk: 8  },
  { ts: "10:00:45", tool: "bash",       decision: "allowed",           risk: 15 },
  { ts: "10:01:03", tool: "write_file", decision: "approval_required", risk: 65 },
  { ts: "10:01:30", tool: "bash",       decision: "blocked",           risk: 88 },
  { ts: "10:02:11", tool: "curl",       decision: "allowed",           risk: 22 },
  { ts: "10:02:58", tool: "read_file",  decision: "allowed",           risk: 5  },
  { ts: "10:03:17", tool: "fs.write",   decision: "approval_required", risk: 71 },
  { ts: "10:03:44", tool: "exec",       decision: "blocked",           risk: 95 },
];

const MOCK_POLICIES = [
  { id: "POL001", name: "No shell access",           action: "block",    enabled: true  },
  { id: "POL002", name: "Require approval on writes", action: "approval", enabled: true  },
  { id: "POL003", name: "Allow read-only operations", action: "allow",    enabled: true  },
  { id: "POL004", name: "Block network egress",       action: "block",    enabled: false },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

// Shield ASCII art with colour-coded lines
function ShieldDisplay() {
  const lines = SHIELD_ART.split("\n");
  return (
    <div className="tui-chat-logo">
      <pre className="tui-shield-art tui-glow">
        {lines.map((line, i) => {
          let color = "var(--tui-accent)";
          if (line.includes("PALADIN") || line.includes("P A L A D I N")) {
            color = "var(--tui-accent-bright)";
          } else if (line.includes("╔") || line.includes("╚") || line.includes("║")) {
            color = "#60c8d0";
          } else if (line.includes("██")) {
            color = "#1ccdd8";
          } else if (line.includes("╭") || line.includes("╰") || line.includes("╱") || line.includes("╲")) {
            color = "var(--tui-muted)";
          } else {
            color = "var(--tui-text-dim)";
          }
          return (
            <span key={i} style={{ color }}>
              {line}
              {i < lines.length - 1 ? "\n" : ""}
            </span>
          );
        })}
      </pre>
    </div>
  );
}

// Single chat message
function ChatMsg({ msg }: { msg: ChatMessage }) {
  const whoLabel: Record<MsgRole, string> = {
    user:    "You",
    kiro:    "Kiro",
    system:  "Shield",
    error:   "Error",
    success: "Done",
    info:    "Info",
  };

  return (
    <div className="tui-msg">
      <span className="tui-msg-ts">{msg.ts}</span>
      <span className={`tui-msg-who ${msg.role}`}>{whoLabel[msg.role]}</span>
      <span className={`tui-msg-body ${msg.role}`}>{msg.content}</span>
    </div>
  );
}

// Typing indicator
function TypingIndicator() {
  return (
    <div className="tui-msg">
      <span className="tui-msg-ts">{now()}</span>
      <span className="tui-msg-who kiro">Kiro</span>
      <span className="tui-msg-body">
        <span className="tui-typing">
          <span /><span /><span />
        </span>
      </span>
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

interface SidebarProps {
  currentView: View;
  onNavigate: (v: View) => void;
  collapsed: boolean;
  pendingCount: number;
}

function TuiSidebar({ currentView, onNavigate, collapsed, pendingCount }: SidebarProps) {
  const navItems: { id: View; label: string; icon: string; badge?: number }[] = [
    { id: "session",   label: "Active Session", icon: "◉" },
    { id: "dashboard", label: "Dashboard",      icon: "⊞" },
    { id: "approvals", label: "Approvals",      icon: "✓", badge: pendingCount > 0 ? pendingCount : undefined },
    { id: "activity",  label: "Activity",       icon: "≋" },
    { id: "policies",  label: "Policies",       icon: "⛊" },
    { id: "settings",  label: "Settings",       icon: "⚙" },
  ];

  return (
    <aside className={`tui-sidebar${collapsed ? " collapsed" : ""}`}>
      {/* Header */}
      <div className="tui-sidebar-header">
        <div className="tui-sidebar-logo">
          <span className="tui-sidebar-logo-icon">🛡</span>
          <span className="tui-sidebar-logo-text">Paladin</span>
        </div>
        <div className="tui-sidebar-subtitle">AgentShield v0.1</div>
      </div>

      {/* Nav items */}
      <nav className="tui-sidebar-nav">
        {navItems.map((item) => (
          <div
            key={item.id}
            className={`tui-nav-item${currentView === item.id ? " active" : ""}`}
            onClick={() => onNavigate(item.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onNavigate(item.id)}
            aria-current={currentView === item.id ? "page" : undefined}
          >
            <span className="tui-nav-item-icon">{item.icon}</span>
            <span>{item.label}</span>
            {item.badge !== undefined && (
              <span className="tui-nav-badge">{item.badge}</span>
            )}
          </div>
        ))}
      </nav>

      {/* Footer status */}
      <div className="tui-sidebar-footer">
        <div className="tui-status-row">
          <span>Kiro CLI</span>
          <span className="tui-status-dot ok" title="OK" />
        </div>
        <div className="tui-status-row">
          <span>AgentShield</span>
          <span className="tui-status-dot ok" title="OK" />
        </div>
        <div className="tui-status-row">
          <span>Protection</span>
          <span className="tui-status-dot ok" title="ON" />
        </div>
      </div>
    </aside>
  );
}

// ─── Session View ─────────────────────────────────────────────────────────────

interface SessionViewProps {
  messages: ChatMessage[];
  isTyping: boolean;
}

function SessionView({ messages, isTyping }: SessionViewProps) {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  return (
    <div className="tui-chat">
      <ShieldDisplay />
      <div className="tui-chat-log" ref={logRef}>
        {messages.map((msg) => (
          <ChatMsg key={msg.id} msg={msg} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>
      <div className="tui-session-bar">
        <span className="tui-session-bar-item">
          <span className="tui-status-dot ok" style={{ width: 5, height: 5 }} />
          <span>Session #A82F</span>
        </span>
        <span className="tui-session-bar-item" style={{ color: "var(--tui-green)" }}>
          RUNNING
        </span>
        <span className="tui-session-bar-item">Kiro agent connected</span>
      </div>
    </div>
  );
}

// ─── Dashboard View ───────────────────────────────────────────────────────────

function DashboardView() {
  const stats = [
    { label: "Analyzed",   val: 47, color: "var(--tui-text)" },
    { label: "Allowed",    val: 38, color: "var(--tui-green)" },
    { label: "Blocked",    val: 4,  color: "var(--tui-red)" },
    { label: "Review",     val: 5,  color: "var(--tui-amber)" },
    { label: "Avg Risk",   val: 23, color: "var(--tui-accent)" },
    { label: "Sessions",   val: 3,  color: "var(--tui-text)" },
  ];

  const recentActivity = MOCK_ACTIVITY.slice(0, 5);

  return (
    <div className="tui-view">
      <div className="tui-view-title">
        <span>⊞</span>
        <span>Dashboard — Paladin AgentShield</span>
      </div>
      <hr className="tui-view-divider" />

      {/* Stats grid */}
      <div className="tui-stats-grid">
        {stats.map((s) => (
          <div key={s.label} className="tui-stat-box">
            <div className="tui-stat-val" style={{ color: s.color }}>{s.val}</div>
            <div className="tui-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* System status */}
      <div className="tui-card">
        <div className="tui-card-header">System Status</div>
        {[
          { label: "AgentShield",  status: "active",    ok: true },
          { label: "Kiro CLI",     status: "connected", ok: true },
          { label: "Auto Block",   status: "enabled",   ok: true },
          { label: "Auto Allow",   status: "enabled",   ok: true },
          { label: "Backend API",  status: "http://localhost:8000", ok: true },
        ].map((row) => (
          <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 7, fontSize: 11 }}>
            <span style={{ color: "var(--tui-muted)" }}>{row.label}</span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className={`tui-status-dot ${row.ok ? "ok" : "err"}`} style={{ width: 5, height: 5 }} />
              <span style={{ color: row.ok ? "var(--tui-green)" : "var(--tui-red)", fontSize: 10 }}>{row.status}</span>
            </span>
          </div>
        ))}
      </div>

      {/* Recent activity */}
      <div className="tui-card">
        <div className="tui-card-header">Recent Activity</div>
        <table className="tui-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Tool</th>
              <th>Decision</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {recentActivity.map((r, i) => (
              <tr key={i}>
                <td style={{ color: "var(--tui-text-dim)" }}>{r.ts}</td>
                <td style={{ color: "var(--tui-accent-bright)" }}>{r.tool}</td>
                <td>
                  <DecisionTag decision={r.decision} />
                </td>
                <td>
                  <RiskNum val={r.risk} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DecisionTag({ decision }: { decision: string }) {
  if (decision === "allowed") return <span className="tui-tag green">allow</span>;
  if (decision === "blocked") return <span className="tui-tag red">block</span>;
  if (decision === "approval_required") return <span className="tui-tag amber">review</span>;
  return <span className="tui-tag cyan">{decision}</span>;
}

function RiskNum({ val }: { val: number }) {
  const color = val >= 76 ? "var(--tui-red)" : val >= 40 ? "var(--tui-amber)" : "var(--tui-green)";
  return <span style={{ color, fontWeight: 600 }}>{val}</span>;
}

// ─── Approvals View ───────────────────────────────────────────────────────────

interface ApprovalsViewProps {
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
}

function ApprovalsView({ onApprove, onDeny }: ApprovalsViewProps) {
  const [approvals, setApprovals] = useState(MOCK_APPROVALS);

  function handleApprove(id: string) {
    setApprovals((a) => a.filter((x) => x.id !== id));
    onApprove(id);
  }

  function handleDeny(id: string) {
    setApprovals((a) => a.filter((x) => x.id !== id));
    onDeny(id);
  }

  return (
    <div className="tui-view">
      <div className="tui-view-title">
        <span>✓</span>
        <span>Pending Approvals</span>
        {approvals.length > 0 && (
          <span className="tui-nav-badge" style={{ marginLeft: 6 }}>{approvals.length}</span>
        )}
      </div>
      <hr className="tui-view-divider" />

      {approvals.length === 0 ? (
        <div className="tui-card" style={{ textAlign: "center", padding: 32, color: "var(--tui-text-dim)" }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>✓</div>
          <div>No pending approvals</div>
        </div>
      ) : (
        approvals.map((a) => (
          <div key={a.id} className="tui-card" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
              <div>
                <span style={{ color: "var(--tui-accent-bright)", fontWeight: 700, fontSize: 12 }}>{a.id}</span>
                <span style={{ marginLeft: 10, fontSize: 10 }}>
                  <span className="tui-tag amber">review</span>
                </span>
              </div>
              <RiskNum val={a.risk} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "90px 1fr", gap: "5px 0", fontSize: 11, marginBottom: 14 }}>
              <span style={{ color: "var(--tui-muted)" }}>Tool</span>
              <span style={{ color: "var(--tui-accent)" }}>{a.tool}</span>
              <span style={{ color: "var(--tui-muted)" }}>Command</span>
              <code style={{ color: "var(--tui-text)", background: "var(--tui-bg-card)", padding: "1px 6px", borderRadius: 3, fontSize: 10 }}>{a.cmd}</code>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => handleApprove(a.id)}
                style={{
                  background: "rgba(52,216,116,0.12)",
                  color: "var(--tui-green)",
                  border: "1px solid rgba(52,216,116,0.35)",
                  borderRadius: 3,
                  padding: "5px 14px",
                  fontFamily: "inherit",
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  cursor: "pointer",
                }}
              >
                Approve
              </button>
              <button
                onClick={() => handleDeny(a.id)}
                style={{
                  background: "rgba(240,97,94,0.1)",
                  color: "var(--tui-red)",
                  border: "1px solid rgba(240,97,94,0.3)",
                  borderRadius: 3,
                  padding: "5px 14px",
                  fontFamily: "inherit",
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  cursor: "pointer",
                }}
              >
                Deny
              </button>
              <span style={{ fontSize: 10, color: "var(--tui-text-dim)", alignSelf: "center", marginLeft: 4 }}>
                paladin approve {a.id}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ─── Activity View ────────────────────────────────────────────────────────────

function ActivityView() {
  return (
    <div className="tui-view">
      <div className="tui-view-title">
        <span>≋</span>
        <span>Activity Log</span>
      </div>
      <hr className="tui-view-divider" />

      <div className="tui-card">
        <table className="tui-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Tool</th>
              <th>Decision</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_ACTIVITY.map((r, i) => (
              <tr key={i}>
                <td style={{ color: "var(--tui-text-dim)", fontSize: 10 }}>{r.ts}</td>
                <td style={{ color: "var(--tui-accent-bright)" }}>{r.tool}</td>
                <td>
                  <DecisionTag decision={r.decision} />
                </td>
                <td>
                  <RiskNum val={r.risk} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 10, fontSize: 10, color: "var(--tui-text-dim)", letterSpacing: "0.04em" }}>
        Showing last 8 events · Use <code style={{ color: "var(--tui-accent)", background: "var(--tui-bg-card)", padding: "1px 5px", borderRadius: 2 }}>paladin activity</code> in the session for more
      </div>
    </div>
  );
}

// ─── Policies View ────────────────────────────────────────────────────────────

function PoliciesView() {
  const [policies, setPolicies] = useState(MOCK_POLICIES);

  function toggle(id: string) {
    setPolicies((ps) => ps.map((p) => p.id === id ? { ...p, enabled: !p.enabled } : p));
  }

  return (
    <div className="tui-view">
      <div className="tui-view-title">
        <span>⛊</span>
        <span>Policies</span>
      </div>
      <hr className="tui-view-divider" />

      <div className="tui-card">
        <div className="tui-card-header">Active Policies ({policies.filter((p) => p.enabled).length}/{policies.length})</div>
        <table className="tui-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>ID</th>
              <th>Name</th>
              <th>Action</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.id}>
                <td>
                  <span className={`tui-status-dot ${p.enabled ? "ok" : "err"}`} style={{ width: 6, height: 6 }} />
                </td>
                <td style={{ color: "var(--tui-text-dim)", fontSize: 10 }}>{p.id}</td>
                <td>{p.name}</td>
                <td>
                  {p.action === "block"    && <span className="tui-tag red">block</span>}
                  {p.action === "allow"    && <span className="tui-tag green">allow</span>}
                  {p.action === "approval" && <span className="tui-tag amber">review</span>}
                </td>
                <td>
                  <button
                    onClick={() => toggle(p.id)}
                    style={{
                      background: "transparent",
                      border: `1px solid ${p.enabled ? "var(--tui-border)" : "rgba(52,216,116,0.3)"}`,
                      color: p.enabled ? "var(--tui-red)" : "var(--tui-green)",
                      borderRadius: 3,
                      padding: "2px 8px",
                      fontFamily: "inherit",
                      fontSize: 9,
                      fontWeight: 700,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      cursor: "pointer",
                    }}
                  >
                    {p.enabled ? "Disable" : "Enable"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ fontSize: 10, color: "var(--tui-text-dim)" }}>
        Use <code style={{ color: "var(--tui-accent)", background: "var(--tui-bg-card)", padding: "1px 5px", borderRadius: 2 }}>paladin policy add</code> in the session to create new policies.
      </div>
    </div>
  );
}

// ─── Settings View ────────────────────────────────────────────────────────────

function SettingsView() {
  const rows = [
    { section: "Paladin CLI",   key: "Version",       val: "0.1.0" },
    { section: "Paladin CLI",   key: "Python",        val: "3.x" },
    { section: "Backend",       key: "API Base URL",  val: "http://localhost:8000" },
    { section: "Backend",       key: "WebSocket",     val: "ws://localhost:8000/ws" },
    { section: "Kiro CLI",      key: "Binary",        val: "kiro / kiro-cli" },
    { section: "Kiro CLI",      key: "Status",        val: "connected" },
  ];

  const keybinds = [
    { key: "s",      desc: "Toggle sidebar" },
    { key: "?",      desc: "Show help" },
    { key: "q",      desc: "Quit (TUI only)" },
    { key: "Escape", desc: "Close modal" },
    { key: "Enter",  desc: "Send message" },
    { key: "↑ / ↓", desc: "Navigate sidebar" },
  ];

  const sections = Array.from(new Set(rows.map((r) => r.section)));

  return (
    <div className="tui-view">
      <div className="tui-view-title">
        <span>⚙</span>
        <span>Settings</span>
      </div>
      <hr className="tui-view-divider" />

      {sections.map((sec) => (
        <div key={sec} className="tui-card" style={{ marginBottom: 10 }}>
          <div className="tui-card-header">{sec}</div>
          {rows.filter((r) => r.section === sec).map((r) => (
            <div key={r.key} style={{ display: "flex", justifyContent: "space-between", marginBottom: 7, fontSize: 11 }}>
              <span style={{ color: "var(--tui-muted)" }}>{r.key}</span>
              <span style={{ color: "var(--tui-accent-bright)" }}>{r.val}</span>
            </div>
          ))}
        </div>
      ))}

      <div className="tui-card">
        <div className="tui-card-header">Keyboard Shortcuts</div>
        {keybinds.map((kb) => (
          <div key={kb.key} style={{ display: "flex", gap: 14, marginBottom: 6, fontSize: 11 }}>
            <kbd style={{
              background: "var(--tui-bg-card)",
              border: "1px solid var(--tui-border)",
              borderRadius: 3,
              padding: "1px 7px",
              fontSize: 10,
              color: "var(--tui-accent-bright)",
              minWidth: 52,
              textAlign: "center",
              fontFamily: "inherit",
            }}>{kb.key}</kbd>
            <span style={{ color: "var(--tui-muted)" }}>{kb.desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Help Modal ───────────────────────────────────────────────────────────────

interface HelpModalProps {
  onClose: () => void;
}

function HelpModal({ onClose }: HelpModalProps) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const commands = [
    { cmd: "paladin init",          desc: "Initialise Paladin in the current project" },
    { cmd: "paladin start",         desc: "Start the Paladin agent session" },
    { cmd: "paladin status",        desc: "Show current session status" },
    { cmd: "paladin run <query>",   desc: "Run a query via Kiro" },
    { cmd: "paladin approvals",     desc: "List pending approvals" },
    { cmd: "paladin approve <id>",  desc: "Approve an action by ID" },
    { cmd: "paladin deny <id>",     desc: "Deny an action by ID" },
    { cmd: "paladin activity",      desc: "Show the activity log" },
    { cmd: "paladin policy list",   desc: "List all policies" },
    { cmd: "paladin policy add",    desc: "Add a new policy (interactive)" },
    { cmd: "paladin config",        desc: "Show / edit configuration" },
    { cmd: "paladin doctor",        desc: "Check system health" },
    { cmd: "paladin version",       desc: "Show version info" },
  ];

  const slashCmds = [
    { cmd: "/help  or  ?",  desc: "Show this help" },
    { cmd: "/clear",        desc: "Clear the session log" },
    { cmd: "/run <query>",  desc: "Send a direct Kiro query" },
  ];

  const navKeys = [
    { key: "s",     desc: "Toggle sidebar" },
    { key: "?",     desc: "Open help modal" },
    { key: "Esc",   desc: "Close modal" },
    { key: "Enter", desc: "Send command" },
  ];

  return (
    <div className="tui-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="tui-modal" role="dialog" aria-modal="true" aria-label="Help">
        <div className="tui-modal-title">
          <span>🛡 PALADIN CLI — Help</span>
          <button className="tui-modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="tui-modal-body">
          <div className="tui-help-section">
            <div className="tui-help-section-title">Commands</div>
            {commands.map((c) => (
              <div key={c.cmd} className="tui-help-row">
                <span className="tui-help-cmd">{c.cmd}</span>
                <span className="tui-help-desc">{c.desc}</span>
              </div>
            ))}
          </div>

          <div className="tui-help-section">
            <div className="tui-help-section-title">Slash Commands</div>
            {slashCmds.map((c) => (
              <div key={c.cmd} className="tui-help-row">
                <span className="tui-help-cmd">{c.cmd}</span>
                <span className="tui-help-desc">{c.desc}</span>
              </div>
            ))}
          </div>

          <div className="tui-help-section">
            <div className="tui-help-section-title">Navigation</div>
            {navKeys.map((k) => (
              <div key={k.key} className="tui-help-row">
                <span className="tui-help-cmd">
                  <kbd style={{
                    background: "var(--tui-bg-card)",
                    border: "1px solid var(--tui-border)",
                    borderRadius: 3,
                    padding: "1px 6px",
                    fontSize: 10,
                    color: "var(--tui-accent-bright)",
                    fontFamily: "inherit",
                  }}>{k.key}</kbd>
                </span>
                <span className="tui-help-desc">{k.desc}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="tui-modal-footer">
          Press <kbd style={{ background: "var(--tui-bg-card)", border: "1px solid var(--tui-border)", borderRadius: 3, padding: "0 5px", fontSize: 10, color: "var(--tui-accent-bright)", fontFamily: "inherit" }}>Escape</kbd> to close
        </div>
      </div>
    </div>
  );
}

// ─── Input Bar ────────────────────────────────────────────────────────────────

interface InputBarProps {
  onSubmit: (val: string) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}

function InputBar({ onSubmit, inputRef }: InputBarProps) {
  const [value, setValue] = useState("");

  function handleSubmit() {
    if (!value.trim()) return;
    onSubmit(value.trim());
    setValue("");
  }

  return (
    <div className="tui-input-bar">
      <span className="tui-input-prompt">❯</span>
      <input
        ref={inputRef}
        className="tui-input-field"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Type a command or query…  (/help for commands)"
        aria-label="Command input"
        autoComplete="off"
        spellCheck={false}
      />
      <button className="tui-input-send" onClick={handleSubmit} aria-label="Send">
        Send
      </button>
    </div>
  );
}

// ─── Title bar ────────────────────────────────────────────────────────────────

interface TitlebarProps {
  onHelp: () => void;
  onToggleSidebar: () => void;
}

function Titlebar({ onHelp, onToggleSidebar }: TitlebarProps) {
  return (
    <div className="tui-titlebar">
      <span className="tui-titlebar-title">🛡 Paladin — AgentShield</span>
      <div className="tui-titlebar-right">
        <span className="tui-titlebar-key">
          <kbd>s</kbd> sidebar
        </span>
        <span className="tui-titlebar-key">
          <kbd>?</kbd> help
        </span>
        <span style={{ color: "var(--tui-text-dim)" }}>v0.1.0</span>
        <span
          onClick={onToggleSidebar}
          style={{ cursor: "pointer", color: "var(--tui-accent)", userSelect: "none" }}
          title="Toggle sidebar (s)"
        >
          [s]
        </span>
        <span
          onClick={onHelp}
          style={{ cursor: "pointer", color: "var(--tui-accent)", userSelect: "none" }}
          title="Help (?)"
        >
          [?]
        </span>
      </div>
    </div>
  );
}

// ─── Command handler ──────────────────────────────────────────────────────────

function handleCommand(
  raw: string,
  addMsg: (role: MsgRole, content: string) => void,
  navigate: (v: View) => void,
  setTyping: (v: boolean) => void,
  openHelp: () => void,
  clearChat: () => void,
): void {
  const text = raw.trim();
  if (!text) return;

  // User message always echoed
  addMsg("user", text);

  if (text.startsWith("/")) {
    const cmd = text.slice(1).trim().toLowerCase();
    if (cmd === "help" || cmd === "h" || cmd === "?") {
      openHelp();
    } else if (cmd === "clear") {
      clearChat();
      addMsg("system", "Log cleared.");
    } else if (cmd.startsWith("run ")) {
      const query = text.slice(5).trim();
      simulateKiroResponse(query, addMsg, setTyping);
    } else {
      addMsg("error", `Unknown command: /${cmd}  — try /help`);
    }
    return;
  }

  // Paladin sub-commands
  const parts = text.toLowerCase().split(/\s+/);
  const base = parts[0] === "paladin" ? parts[1] : parts[0];
  const args = parts[0] === "paladin" ? parts.slice(2) : parts.slice(1);

  switch (base) {
    case "help":
      openHelp();
      break;

    case undefined:
    case "":
      addMsg("info", `Paladin CLI v0.1.0 — AgentShield runtime security.\nType /help for available commands.`);
      break;

    case "init":
      addMsg("system", "Initialising Paladin in current directory…");
      setTimeout(() => addMsg("success", "Paladin initialised!\nConfig written to: .paladin.json"), 600);
      break;

    case "start":
      addMsg("system", "Connecting to AgentShield backend…");
      setTimeout(() => addMsg("success", "Paladin started. 3 session(s) found on backend."), 700);
      break;

    case "status":
      addMsg("info",
        "Session #A82F\n" +
        "  Agent:    Kiro\n" +
        "  Status:   RUNNING\n" +
        "  Actions:  47\n" +
        "  Backend:  http://localhost:8000"
      );
      break;

    case "run": {
      const query = args.join(" ");
      if (!query) { addMsg("error", "Usage: paladin run <query>"); break; }
      simulateKiroResponse(query, addMsg, setTyping);
      break;
    }

    case "approvals":
      navigate("approvals");
      addMsg("system", "Switched to Approvals view.");
      break;

    case "approve":
      if (!args[0]) { addMsg("error", "Usage: paladin approve <id>"); break; }
      addMsg("success", `Approved action ${args[0].toUpperCase()}.`);
      break;

    case "deny":
      if (!args[0]) { addMsg("error", "Usage: paladin deny <id>"); break; }
      addMsg("success", `Denied action ${args[0].toUpperCase()}.`);
      break;

    case "activity":
      navigate("activity");
      addMsg("system", "Switched to Activity view.");
      break;

    case "policy":
      if (!args[0] || args[0] === "list") {
        navigate("policies");
        addMsg("system", "Switched to Policies view.");
      } else if (args[0] === "add") {
        addMsg("info", "Policy add — use the Policies view for now.\nFull interactive mode coming soon.");
      } else if (args[0] === "test") {
        addMsg("info", "Policy test mode — enter a tool call to simulate.\nFeature coming soon.");
      } else {
        addMsg("error", `Unknown policy subcommand: ${args[0]}\nUsage: paladin policy [list|add|test]`);
      }
      break;

    case "config":
      navigate("settings");
      addMsg("system", "Switched to Settings view.");
      break;

    case "doctor":
      addMsg("info",
        "Doctor — System Health Check\n\n" +
        "  ✓  Kiro CLI         found at /usr/local/bin/kiro\n" +
        "  !  Backend API      not reachable at http://localhost:8000\n" +
        "  ✓  Python           3.12 (ok)\n" +
        "  ✓  Textual          8.2.8\n\n" +
        "  Some issues found. Review above."
      );
      break;

    case "version":
      addMsg("info",
        "Paladin v0.1.0\n" +
        "Python 3.12\n" +
        "Kiro CLI: kiro-cli\n" +
        "API: http://localhost:8000"
      );
      break;

    default:
      // Treat as a free-form Kiro query
      simulateKiroResponse(text, addMsg, setTyping);
      break;
  }
}

function simulateKiroResponse(
  query: string,
  addMsg: (role: MsgRole, content: string) => void,
  setTyping: (v: boolean) => void,
) {
  setTyping(true);
  const delay = 900 + Math.random() * 800;
  setTimeout(() => {
    setTyping(false);
    addMsg(
      "kiro",
      `[Kiro response for: "${query}"]\n\nThis is a simulated response — connect a live Kiro CLI binary and the real kiro-cli-chat output will appear here instead.`
    );
  }, delay);
}

// ─── Main TUI Component ───────────────────────────────────────────────────────

export default function PaladinTUI() {
  const [currentView, setCurrentView] = useState<View>("session");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [helpOpen, setHelpOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: uid(), role: "system", content: WELCOME_MSG, ts: now() },
  ]);

  const inputRef = useRef<HTMLInputElement | null>(null);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Don't intercept when modal is open
      if (helpOpen) return;

      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA";

      if (e.key === "s" && !isInput) {
        e.preventDefault();
        setSidebarOpen((v) => !v);
      }
      if ((e.key === "?" || e.key === "/") && !isInput) {
        e.preventDefault();
        setHelpOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [helpOpen]);

  const addMsg = useCallback((role: MsgRole, content: string) => {
    setMessages((prev) => [...prev, { id: uid(), role, content, ts: now() }]);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  const navigate = useCallback((view: View) => {
    setCurrentView(view);
    // Always switch back to session when user interacts from input
  }, []);

  function onInputSubmit(val: string) {
    // Switch to session for command output
    setCurrentView("session");
    handleCommand(val, addMsg, navigate, setIsTyping, () => setHelpOpen(true), clearChat);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  function onApprove(id: string) {
    addMsg("success", `Approved action ${id}.`);
  }

  function onDeny(id: string) {
    addMsg("error", `Denied action ${id}.`);
  }

  const pendingCount = MOCK_APPROVALS.length;

  return (
    <div className="tui-root">
      {/* Title bar */}
      <Titlebar onHelp={() => setHelpOpen(true)} onToggleSidebar={() => setSidebarOpen((v) => !v)} />

      {/* Body */}
      <div className="tui-body">
        <TuiSidebar
          currentView={currentView}
          onNavigate={setCurrentView}
          collapsed={!sidebarOpen}
          pendingCount={pendingCount}
        />

        <div className="tui-main">
          <div className="tui-content">
            {currentView === "session" && (
              <SessionView messages={messages} isTyping={isTyping} />
            )}
            {currentView === "dashboard" && <DashboardView />}
            {currentView === "approvals" && (
              <ApprovalsView onApprove={onApprove} onDeny={onDeny} />
            )}
            {currentView === "activity" && <ActivityView />}
            {currentView === "policies" && <PoliciesView />}
            {currentView === "settings" && <SettingsView />}
          </div>

          {/* Input bar */}
          <InputBar onSubmit={onInputSubmit} inputRef={inputRef} />
        </div>
      </div>

      {/* Help modal */}
      {helpOpen && <HelpModal onClose={() => { setHelpOpen(false); inputRef.current?.focus(); }} />}
    </div>
  );
}
