import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { getDashboardStats, getRiskHistory } from "../../services/sessions";
import { getActions } from "../../services/actions";
import { Card, CardHeader, DecisionBadge, MetricCard, PageHeader, RiskScore, Timestamp, ToolChip } from "../../components/ui";
import type { ToolAction } from "../../types";

const mono = "'JetBrains Mono', monospace";

type Stats = { actions_analyzed: number; allowed: number; approval_required: number; blocked: number; avg_risk: number };
type RiskPoint = { time: string; risk: number };

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [riskHistory, setRiskHistory] = useState<RiskPoint[]>([]);
  const [actions, setActions] = useState<ToolAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const [st, rh, acts] = await Promise.all([
          getDashboardStats(), getRiskHistory(), getActions("A82F"),
        ]);
        if (!cancelled) { setStats(st); setRiskHistory(rh); setActions(acts); }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <Msg>Loading…</Msg>;
  if (error || !stats) return <Msg color="var(--red)">{error ?? "Failed to load."}</Msg>;

  return (
    <div style={{ padding: "28px 28px 48px" }}>
      <PageHeader
        title="Paladin"
        subtitle="Runtime security for autonomous AI agents."
        right={
          <div style={{
            display: "flex", alignItems: "center", gap: 7,
            background: "var(--bg-2)", border: "1px solid var(--border)",
            borderRadius: 5, padding: "6px 11px",
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", opacity: 0.8, display: "inline-block" }} />
            <span style={{ fontFamily: mono, fontSize: 10, fontWeight: 500, color: "var(--text-1)", letterSpacing: "0.06em" }}>
              PROTECTION ACTIVE
            </span>
          </div>
        }
      />

      {/* Stats */}
      <div className="stats-grid" style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 8, marginBottom: 20 }}>
        <MetricCard label="Analyzed" value={stats.actions_analyzed} />
        <MetricCard label="Allowed"  value={stats.allowed}          accent="var(--green)" />
        <MetricCard label="Review"   value={stats.approval_required} accent="var(--amber)" />
        <MetricCard label="Blocked"  value={stats.blocked}          accent="var(--red)"   />
        <MetricCard label="Avg Risk" value={String(stats.avg_risk)} accent="var(--text-1)" />
      </div>

      <div className="dashboard-grid" style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 14 }}>
        {/* Left */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Card>
            <CardHeader
              title="Live Activity"
              right={
                <span style={{ display: "flex", alignItems: "center", gap: 5, fontFamily: mono, fontSize: 10, color: "var(--text-2)" }}>
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)", opacity: 0.7, display: "inline-block" }} />
                  live
                </span>
              }
            />
            <div>
              {actions.length === 0 && (
                <div style={{ padding: "20px 16px", color: "var(--text-2)", fontFamily: mono, fontSize: 12, textAlign: "center" }}>
                  No activity yet.
                </div>
              )}
              {actions.map((action, i) => (
                <div
                  key={action.id}
                  onClick={() => navigate("/session/A82F")}
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "9px 16px",
                    borderBottom: i < actions.length - 1 ? "1px solid var(--bg-2)" : "none",
                    cursor: "pointer",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-2)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <Timestamp iso={action.timestamp} />
                  <ToolChip name={action.tool_name} />
                  <span style={{ fontFamily: mono, fontSize: 11, color: "var(--text-2)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {Object.values(action.tool_input)[0]}
                  </span>
                  <RiskScore score={action.risk_score} size="sm" />
                  <DecisionBadge decision={action.decision} />
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Risk Over Time" />
            <div style={{ padding: "14px 16px 16px" }}>
              <MiniRiskChart data={riskHistory} />
            </div>
          </Card>
        </div>

        {/* Right */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Card>
            <CardHeader title="Decision Split" />
            <div style={{ padding: "14px 16px" }}>
              <DistBar label="Allowed" value={stats.allowed}           total={stats.actions_analyzed} color="var(--green)" />
              <DistBar label="Review"  value={stats.approval_required} total={stats.actions_analyzed} color="var(--amber)" />
              <DistBar label="Blocked" value={stats.blocked}           total={stats.actions_analyzed} color="var(--red)"   />
            </div>
          </Card>

          <Card>
            <CardHeader title="System Status" />
            <div style={{ padding: "12px 16px" }}>
              {[
                { label: "AgentShield", value: "active"    },
                { label: "Kiro CLI",    value: "connected" },
                { label: "Reka AI",     value: "connected" },
                { label: "Auto Block",  value: "enabled"   },
                { label: "Auto Allow",  value: "enabled"   },
              ].map((row) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: "var(--text-1)" }}>{row.label}</span>
                  <span style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", letterSpacing: "0.04em" }}>{row.value}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function DistBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontFamily: mono, fontSize: 10, color: "var(--text-1)", letterSpacing: "0.04em", textTransform: "uppercase" }}>{label}</span>
        <span style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)" }}>{value} · {pct}%</span>
      </div>
      <div style={{ height: 2, background: "var(--bg-4)", borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2 }} />
      </div>
    </div>
  );
}

function MiniRiskChart({ data }: { data: RiskPoint[] }) {
  if (data.length < 2) return null;
  const h = 64;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = h - (d.risk / 100) * h;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 100 ${h}`} preserveAspectRatio="none" style={{ width: "100%", height: h, display: "block" }}>
      <defs>
        <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.25" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline points={`0,${h} ${pts} 100,${h}`} fill="url(#rg)" style={{ color: "var(--text-1)" }} />
      <polyline points={pts} fill="none" stroke="var(--text-1)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function Msg({ color = "var(--text-2)", children }: { color?: string; children: React.ReactNode }) {
  return <div style={{ padding: 28, color, fontFamily: mono, fontSize: 12 }}>{children}</div>;
}
