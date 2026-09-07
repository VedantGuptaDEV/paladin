import { useState, useEffect, useCallback, useRef } from "react";
import { attackReplaySteps, replaySummary } from "../mock/attackReplay";
import type { ReplayStep } from "../mock/attackReplay";
import { DecisionBadge, RiskScore, ToolChip } from "./ui";

const mono = "'JetBrains Mono', monospace";

// ─── Risk colour helpers ──────────────────────────────────────────────────────

function riskColor(score: number) {
  if (score >= 76) return "var(--red)";
  if (score >= 41) return "var(--amber)";
  return "var(--green)";
}

function riskDim(score: number) {
  if (score >= 76) return "var(--red-dim)";
  if (score >= 41) return "var(--amber-dim)";
  return "var(--green-dim)";
}

// ─── AttackReplayModal ────────────────────────────────────────────────────────

interface AttackReplayModalProps {
  onClose: () => void;
}

type Phase = "intro" | "playing" | "summary";

export default function AttackReplayModal({ onClose }: AttackReplayModalProps) {
  const [phase, setPhase] = useState<Phase>("intro");
  const [currentStep, setCurrentStep] = useState(0);
  const [visibleSteps, setVisibleSteps] = useState<number[]>([]);
  const [shieldAnimating, setShieldAnimating] = useState(false);
  const [autoPlaying, setAutoPlaying] = useState(false);

  const autoRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  // Scroll the feed to bottom whenever visibleSteps grows
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [visibleSteps.length]);

  // Cleanup auto-play timer on unmount
  useEffect(() => {
    return () => {
      if (autoRef.current) clearTimeout(autoRef.current);
    };
  }, []);

  const revealStep = useCallback(
    (idx: number) => {
      setCurrentStep(idx);
      setVisibleSteps((prev) => (prev.includes(idx) ? prev : [...prev, idx]));

      const step = attackReplaySteps[idx];
      const isBlocked = step.action.decision === "blocked";

      // Animate shield intercept for blocked actions
      if (isBlocked) {
        setShieldAnimating(true);
        setTimeout(() => setShieldAnimating(false), 900);
      }
    },
    [],
  );

  const goNext = useCallback(() => {
    if (currentStep < attackReplaySteps.length - 1) {
      revealStep(currentStep + 1);
    } else {
      setPhase("summary");
    }
  }, [currentStep, revealStep]);

  // Auto-play: advance after autoAdvanceMs if > 0
  useEffect(() => {
    if (!autoPlaying || phase !== "playing") return;
    if (autoRef.current) clearTimeout(autoRef.current);

    const step = attackReplaySteps[currentStep];
    if (step.autoAdvanceMs > 0) {
      autoRef.current = setTimeout(() => goNext(), step.autoAdvanceMs);
    }
    // steps with autoAdvanceMs === 0 require manual "Next"
    return () => {
      if (autoRef.current) clearTimeout(autoRef.current);
    };
  }, [autoPlaying, currentStep, phase, goNext]);

  const startReplay = () => {
    setPhase("playing");
    setVisibleSteps([]);
    setCurrentStep(0);
    setAutoPlaying(true);
    // Reveal step 0 immediately
    setTimeout(() => revealStep(0), 100);
  };

  const restart = () => {
    setPhase("intro");
    setVisibleSteps([]);
    setCurrentStep(0);
    setAutoPlaying(false);
    if (autoRef.current) clearTimeout(autoRef.current);
  };

  const currentStepData = attackReplaySteps[currentStep];
  const allDone = currentStep === attackReplaySteps.length - 1 && visibleSteps.includes(currentStep);
  const canGoNext = phase === "playing" && allDone && phase !== "summary";

  return (
    /* Backdrop */
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.72)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "16px",
        backdropFilter: "blur(3px)",
      }}
    >
      {/* Modal */}
      <div
        style={{
          width: "100%", maxWidth: 860,
          background: "var(--bg-1)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
          display: "flex", flexDirection: "column",
          maxHeight: "90vh",
          boxShadow: "0 24px 80px rgba(0,0,0,0.55)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "14px 20px",
            borderBottom: "1px solid var(--border)",
            background: "var(--bg-0)",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-0)", letterSpacing: "-0.02em" }}>
              Attack Replay
            </span>
            <span
              style={{
                fontFamily: mono, fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase",
                color: "var(--red)", background: "var(--red-dim)",
                padding: "2px 7px", borderRadius: 3,
              }}
            >
              demo mode
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "none", border: "none", color: "var(--text-2)",
              cursor: "pointer", fontSize: 18, lineHeight: 1, padding: "2px 6px",
            }}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>

          {/* ── Intro ── */}
          {phase === "intro" && (
            <div
              style={{
                flex: 1, display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                padding: "40px 32px", textAlign: "center",
              }}
            >
              <div
                style={{
                  width: 56, height: 56, borderRadius: "50%",
                  background: "var(--red-dim)", border: "2px solid var(--red-border)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 24, marginBottom: 20,
                }}
              >
                ⚡
              </div>
              <h2
                style={{
                  fontSize: 18, fontWeight: 600, color: "var(--text-0)",
                  margin: "0 0 10px", letterSpacing: "-0.02em",
                }}
              >
                Compromised Agent Scenario
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-2)", maxWidth: 480, lineHeight: 1.7, margin: "0 0 10px" }}>
                This demo replays a scripted attack where a compromised AI agent
                escalates from innocuous file reads to credential theft and
                full-disk deletion.
              </p>
              <p style={{ fontSize: 13, color: "var(--text-2)", maxWidth: 480, lineHeight: 1.7, margin: "0 0 32px" }}>
                Watch <strong style={{ color: "var(--text-1)" }}>Paladin AgentShield</strong> intercept
                every malicious action in real time — before any damage occurs.
              </p>

              {/* Attack preview */}
              <div
                style={{
                  display: "flex", gap: 0, marginBottom: 36, flexWrap: "wrap", justifyContent: "center",
                }}
              >
                {attackReplaySteps.map((s, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center" }}>
                    <div
                      style={{
                        display: "flex", flexDirection: "column", alignItems: "center",
                        gap: 6, padding: "10px 16px",
                        background: "var(--bg-2)", border: "1px solid var(--border)",
                        borderRadius: i === 0 ? "6px 0 0 6px" : i === attackReplaySteps.length - 1 ? "0 6px 6px 0" : "0",
                        borderLeft: i > 0 ? "none" : undefined,
                        minWidth: 120,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: mono, fontSize: 9, color: "var(--text-2)",
                          textTransform: "uppercase", letterSpacing: "0.06em",
                        }}
                      >
                        Step {i + 1}
                      </span>
                      <span style={{ fontSize: 12, color: "var(--text-1)", fontWeight: 500 }}>
                        {s.headline}
                      </span>
                      <span
                        style={{
                          fontFamily: mono, fontSize: 10, fontWeight: 600,
                          color: riskColor(s.action.risk_score),
                          background: riskDim(s.action.risk_score),
                          padding: "1px 6px", borderRadius: 3,
                        }}
                      >
                        risk {s.action.risk_score}
                      </span>
                    </div>
                    {i < attackReplaySteps.length - 1 && (
                      <span style={{ color: "var(--text-2)", fontSize: 11, zIndex: 1 }}>›</span>
                    )}
                  </div>
                ))}
              </div>

              <button
                onClick={startReplay}
                style={{
                  padding: "11px 32px",
                  background: "var(--text-0)", color: "var(--bg-0)",
                  border: "none", borderRadius: 6,
                  fontFamily: mono, fontSize: 12, fontWeight: 600,
                  letterSpacing: "0.05em", cursor: "pointer",
                  textTransform: "uppercase",
                }}
              >
                ▶ Start Replay
              </button>
            </div>
          )}

          {/* ── Playing ── */}
          {phase === "playing" && (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

              {/* Step indicator */}
              <div
                style={{
                  padding: "12px 20px", borderBottom: "1px solid var(--border)",
                  display: "flex", alignItems: "center", gap: 8, flexShrink: 0,
                  background: "var(--bg-0)",
                }}
              >
                {attackReplaySteps.map((s, i) => {
                  const revealed = visibleSteps.includes(i);
                  const active   = i === currentStep;
                  const blocked  = s.action.decision === "blocked";
                  return (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div
                        style={{
                          display: "flex", alignItems: "center", gap: 6,
                          padding: "4px 10px", borderRadius: 4,
                          background: active ? (blocked ? "var(--red-dim)" : "var(--green-dim)") : "transparent",
                          border: `1px solid ${active ? (blocked ? "var(--red-border)" : "var(--green-border)") : "var(--border)"}`,
                          opacity: revealed ? 1 : 0.35,
                          transition: "all 0.3s ease",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: mono, fontSize: 9, color: "var(--text-2)",
                            textTransform: "uppercase", letterSpacing: "0.05em",
                          }}
                        >
                          {i + 1}
                        </span>
                        <span style={{ fontFamily: mono, fontSize: 10, color: "var(--text-1)" }}>
                          {s.headline}
                        </span>
                        {revealed && (
                          <span style={{ fontSize: 11, color: blocked ? "var(--red)" : "var(--green)" }}>
                            {blocked ? "✕" : "✓"}
                          </span>
                        )}
                      </div>
                      {i < attackReplaySteps.length - 1 && (
                        <span style={{ color: "var(--border)", fontSize: 10 }}>—</span>
                      )}
                    </div>
                  );
                })}
                <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
                  {shieldAnimating && (
                    <span
                      style={{
                        fontFamily: mono, fontSize: 10, color: "var(--red)",
                        background: "var(--red-dim)", padding: "3px 8px", borderRadius: 4,
                        letterSpacing: "0.06em", animation: "shieldPulse 0.9s ease-out",
                      }}
                    >
                      ⛨ SHIELD ACTIVE
                    </span>
                  )}
                </div>
              </div>

              {/* Feed */}
              <div
                ref={feedRef}
                style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}
              >
                {visibleSteps.map((idx) => (
                  <StepCard
                    key={idx}
                    step={attackReplaySteps[idx]}
                    isLatest={idx === currentStep}
                  />
                ))}

                {/* Waiting indicator — auto-plays step 0 then pauses on blocked */}
                {!allDone && visibleSteps.length > 0 && (
                  <div
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      fontFamily: mono, fontSize: 11, color: "var(--text-2)",
                    }}
                  >
                    <span style={{ animation: "blink 1.2s step-start infinite" }}>▍</span>
                    Agent thinking…
                  </div>
                )}
              </div>

              {/* Footer controls */}
              <div
                style={{
                  padding: "12px 20px", borderTop: "1px solid var(--border)",
                  background: "var(--bg-0)", flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                }}
              >
                <button
                  onClick={restart}
                  style={{
                    background: "none", border: "1px solid var(--border)", borderRadius: 5,
                    color: "var(--text-2)", fontFamily: mono, fontSize: 11,
                    padding: "6px 12px", cursor: "pointer", letterSpacing: "0.04em",
                  }}
                >
                  ↺ Restart
                </button>

                <div style={{ display: "flex", gap: 8 }}>
                  {/* Next step (manual advance for blocked steps) */}
                  {visibleSteps.includes(currentStep) && currentStep < attackReplaySteps.length - 1 && (
                    <button
                      onClick={goNext}
                      style={{
                        padding: "8px 18px",
                        background: "var(--bg-3)", border: "1px solid var(--border)",
                        borderRadius: 5, color: "var(--text-1)",
                        fontFamily: mono, fontSize: 11, fontWeight: 500,
                        letterSpacing: "0.04em", cursor: "pointer",
                      }}
                    >
                      Next step →
                    </button>
                  )}
                  {/* Finish when all steps shown */}
                  {canGoNext && (
                    <button
                      onClick={() => setPhase("summary")}
                      style={{
                        padding: "8px 18px",
                        background: "var(--text-0)", color: "var(--bg-0)",
                        border: "none", borderRadius: 5,
                        fontFamily: mono, fontSize: 11, fontWeight: 600,
                        letterSpacing: "0.04em", cursor: "pointer",
                      }}
                    >
                      See Summary →
                    </button>
                  )}
                  {allDone && currentStep === attackReplaySteps.length - 1 && (
                    <button
                      onClick={() => setPhase("summary")}
                      style={{
                        padding: "8px 18px",
                        background: "var(--text-0)", color: "var(--bg-0)",
                        border: "none", borderRadius: 5,
                        fontFamily: mono, fontSize: 11, fontWeight: 600,
                        letterSpacing: "0.04em", cursor: "pointer",
                      }}
                    >
                      See Summary →
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Summary ── */}
          {phase === "summary" && (
            <div
              style={{
                flex: 1, overflowY: "auto", padding: "32px 32px 40px",
                display: "flex", flexDirection: "column", alignItems: "center",
              }}
            >
              <div
                style={{
                  width: 48, height: 48, borderRadius: "50%",
                  background: "var(--green-dim)", border: "2px solid var(--green-border)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 22, marginBottom: 16,
                }}
              >
                🛡
              </div>
              <h2
                style={{
                  fontSize: 17, fontWeight: 600, color: "var(--text-0)",
                  margin: "0 0 6px", letterSpacing: "-0.02em",
                }}
              >
                Attack Contained
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-2)", margin: "0 0 28px", lineHeight: 1.6 }}>
                Paladin AgentShield intercepted every malicious action before execution.
              </p>

              {/* Stats row */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, width: "100%", maxWidth: 620, marginBottom: 28 }}>
                {[
                  { label: "Steps",        value: String(replaySummary.totalSteps), color: "var(--text-0)" },
                  { label: "Blocked",      value: String(replaySummary.blocked),    color: "var(--red)"    },
                  { label: "Allowed",      value: String(replaySummary.allowed),    color: "var(--green)"  },
                  { label: "Peak Risk",    value: String(replaySummary.peakRisk),   color: "var(--red)"    },
                ].map(({ label, value, color }) => (
                  <div
                    key={label}
                    style={{
                      background: "var(--bg-2)", border: "1px solid var(--border)",
                      borderRadius: 7, padding: "14px 16px", textAlign: "center",
                    }}
                  >
                    <div style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
                      {label}
                    </div>
                    <div style={{ fontFamily: mono, fontSize: 22, fontWeight: 700, color }}>
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Replay timeline */}
              <div style={{ width: "100%", maxWidth: 620, marginBottom: 28 }}>
                <div style={{ fontFamily: mono, fontSize: 10, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 10 }}>
                  Attack Timeline
                </div>
                {attackReplaySteps.map((s, i) => {
                  const blocked = s.action.decision === "blocked";
                  return (
                    <div
                      key={i}
                      style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "8px 12px", marginBottom: 4,
                        background: "var(--bg-2)", border: "1px solid var(--border)",
                        borderRadius: 5,
                        borderLeft: `3px solid ${blocked ? "var(--red)" : "var(--green)"}`,
                      }}
                    >
                      <ToolChip name={s.action.tool_name} />
                      <code style={{ fontFamily: mono, fontSize: 11, color: "var(--text-2)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {Object.values(s.action.tool_input)[0]}
                      </code>
                      <RiskScore score={s.action.risk_score} size="sm" />
                      <DecisionBadge decision={s.action.decision} />
                    </div>
                  );
                })}
              </div>

              {/* Damage avoided callout */}
              <div
                style={{
                  width: "100%", maxWidth: 620, marginBottom: 28,
                  background: "var(--red-dim)", border: "1px solid var(--red-border)",
                  borderRadius: 7, padding: "14px 18px",
                }}
              >
                <div style={{ fontFamily: mono, fontSize: 10, color: "var(--red)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 6 }}>
                  Damage Avoided
                </div>
                <div style={{ fontSize: 13, color: "var(--text-1)", lineHeight: 1.6 }}>
                  {replaySummary.totalDamageAvoided}
                </div>
              </div>

              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={restart}
                  style={{
                    padding: "9px 22px",
                    background: "var(--bg-3)", border: "1px solid var(--border)",
                    borderRadius: 5, color: "var(--text-1)",
                    fontFamily: mono, fontSize: 11,
                    cursor: "pointer", letterSpacing: "0.04em",
                  }}
                >
                  ↺ Replay
                </button>
                <button
                  onClick={onClose}
                  style={{
                    padding: "9px 22px",
                    background: "var(--text-0)", color: "var(--bg-0)",
                    border: "none", borderRadius: 5,
                    fontFamily: mono, fontSize: 11, fontWeight: 600,
                    cursor: "pointer", letterSpacing: "0.04em",
                  }}
                >
                  Done
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

// ─── StepCard ─────────────────────────────────────────────────────────────────

function StepCard({ step, isLatest }: { step: ReplayStep; isLatest: boolean }) {
  const [shieldRevealed, setShieldRevealed] = useState(false);
  const blocked  = step.action.decision === "blocked";
  const accentColor = blocked ? "var(--red)" : "var(--green)";
  const accentDim   = blocked ? "var(--red-dim)" : "var(--green-dim)";
  const accentBorder = blocked ? "var(--red-border)" : "var(--green-border)";

  // Stagger: show agent thought first, then shield verdict after short delay
  useEffect(() => {
    const t = setTimeout(() => setShieldRevealed(true), 700);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      style={{
        borderRadius: 8, overflow: "hidden",
        border: `1px solid ${isLatest ? accentBorder : "var(--border)"}`,
        boxShadow: isLatest ? `0 0 0 1px ${accentColor}22` : "none",
        animation: "stepIn 0.35s ease-out",
      }}
    >
      {/* Step header */}
      <div
        style={{
          padding: "9px 14px",
          background: isLatest ? accentDim : "var(--bg-2)",
          borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", gap: 10,
        }}
      >
        <span
          style={{
            fontFamily: mono, fontSize: 9, color: "var(--text-2)",
            textTransform: "uppercase", letterSpacing: "0.07em",
            background: "var(--bg-0)", padding: "2px 6px", borderRadius: 3,
          }}
        >
          step {step.step + 1}
        </span>
        <span style={{ fontFamily: mono, fontSize: 11, fontWeight: 500, color: "var(--text-0)" }}>
          {step.headline}
        </span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <RiskScore score={step.action.risk_score} size="sm" />
          <DecisionBadge decision={step.action.decision} />
        </div>
      </div>

      <div style={{ padding: "12px 14px", background: "var(--bg-1)" }}>
        {/* Agent "thinking" bubble */}
        <div
          style={{
            display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 12,
          }}
        >
          <span
            style={{
              fontFamily: mono, fontSize: 9, color: "var(--text-2)",
              textTransform: "uppercase", letterSpacing: "0.05em",
              background: "var(--bg-3)", padding: "2px 6px", borderRadius: 3,
              flexShrink: 0, marginTop: 1,
            }}
          >
            Kiro
          </span>
          <p style={{ fontSize: 12, color: "var(--text-1)", margin: 0, lineHeight: 1.6, fontStyle: "italic" }}>
            &ldquo;{step.agentThought}&rdquo;
          </p>
        </div>

        {/* Tool call row */}
        <div
          style={{
            display: "flex", alignItems: "center", gap: 8, marginBottom: 10,
            background: "var(--bg-0)", border: "1px solid var(--border)",
            borderRadius: 5, padding: "7px 10px",
          }}
        >
          <span style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Tool</span>
          <ToolChip name={step.action.tool_name} />
          <code style={{ fontFamily: mono, fontSize: 11, color: "var(--text-0)", flex: 1 }}>
            {Object.values(step.action.tool_input)[0]}
          </code>
        </div>

        {/* Risk bar */}
        <div style={{ marginBottom: 10 }}>
          <div style={{ height: 3, background: "var(--bg-4)", borderRadius: 2, overflow: "hidden" }}>
            <div
              style={{
                width: `${step.action.risk_score}%`,
                height: "100%",
                background: riskColor(step.action.risk_score),
                borderRadius: 2,
                transition: "width 0.6s ease",
              }}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 3 }}>
            <span style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", letterSpacing: "0.04em" }}>risk score</span>
            <span style={{ fontFamily: mono, fontSize: 9, color: riskColor(step.action.risk_score) }}>
              {step.action.risk_score}/100
            </span>
          </div>
        </div>

        {/* Shield verdict — fades in after delay */}
        {shieldRevealed && (
          <div
            style={{
              background: blocked ? "var(--red-dim)" : "var(--green-dim)",
              border: `1px solid ${blocked ? "var(--red-border)" : "var(--green-border)"}`,
              borderRadius: 5, padding: "9px 12px",
              animation: "fadeUp 0.4s ease-out",
            }}
          >
            <div
              style={{
                fontFamily: mono, fontSize: 9, color: accentColor,
                textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 4,
              }}
            >
              ⛨ AgentShield
            </div>
            <p style={{ fontSize: 12, color: "var(--text-1)", margin: 0, lineHeight: 1.6 }}>
              {step.shieldVerdict}
            </p>
          </div>
        )}

        {/* Risk factors (only for blocked) */}
        {blocked && step.action.risk_factors.length > 0 && shieldRevealed && (
          <div style={{ marginTop: 10, animation: "fadeUp 0.4s ease-out 0.15s both" }}>
            <div style={{ fontFamily: mono, fontSize: 9, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 5 }}>
              Risk factors
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
              {step.action.risk_factors.map((f, i) => (
                <span
                  key={i}
                  style={{
                    fontFamily: mono, fontSize: 10, color: "var(--red)",
                    background: "var(--red-dim)", padding: "2px 7px", borderRadius: 3,
                  }}
                >
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
