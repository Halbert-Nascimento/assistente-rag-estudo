/* ============================================================
   Shared UI components → window
   ============================================================ */

/* ---------- Icon set (stroke, 1.7) ---------- */
const ICONS = {
  home: "M3 10.5 12 4l9 6.5M5 9.5V20h14V9.5M9.5 20v-6h5v6",
  chat: "M4 5.5h16v11H10l-4 3.5v-3.5H4z",
  layers: "M12 3 3 8l9 5 9-5-9-5ZM3 13l9 5 9-5M3 16.5l9 5 9-5",
  docs: "M7 3.5h7l4 4V20.5H7zM14 3.5V8h4M9.5 12.5h6M9.5 15.5h6",
  chart: "M4 20V4M4 20h16M8 16v-5M12.5 16V8M17 16v-8",
  history: "M3.5 12a8.5 8.5 0 1 0 2.6-6.1M3.5 4.8V9h4.2M12 7.5V12l3 1.8",
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM16 16l4.5 4.5",
  send: "M4.5 12 20 4.5l-4 15.5-4.5-6.5L4.5 12Zm7 1.5L20 4.5",
  spark: "M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.8 2.8M14.9 14.9l2.8 2.8M17.7 6.3l-2.8 2.8M9.1 14.9l-2.8 2.8",
  doc2: "M7 3.5h7l4 4V20.5H7zM14 3.5V8h4",
  check: "M4 12.5 9 17.5 20 6.5",
  shield: "M12 3 5 6v5c0 4.4 3 7.6 7 9 4-1.4 7-4.6 7-9V6l-7-3Z",
  arrowR: "M5 12h14M13 6l6 6-6 6",
  chevR: "M9 6l6 6-6 6",
  plus: "M12 5v14M5 12h14",
  filter: "M4 6h16M7 12h10M10 18h4",
  bolt: "M13 3 5 13h5l-1 8 8-10h-5l1-8Z",
  book: "M5 5.5A2.5 2.5 0 0 1 7.5 3H19v14H7.5A2.5 2.5 0 0 0 5 19.5zM5 19.5A2.5 2.5 0 0 1 7.5 17H19v4H7.5A2.5 2.5 0 0 1 5 19.5z",
  clock: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16ZM12 7.5V12l3 1.8",
  alert: "M12 4 2.5 20.5h19L12 4ZM12 10v4M12 17.2v.2",
  refresh: "M20 11A8 8 0 0 0 6 6.3L3.5 8.5M4 13a8 8 0 0 0 14 4.7l2.5-2.2M3.5 4.5v4h4M20.5 19.5v-4h-4",
  flame: "M12 3c1 3-2 4-2 7a2 2 0 0 0 4 0c2 1.5 3 3.5 3 6a5 5 0 0 1-10 0c0-3 2-4 2-7 0-1 .5-2 3-6Z",
  target: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16ZM12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7ZM12 11.5a.5.5 0 1 0 0 1 .5.5 0 0 0 0-1Z",
  quote: "M7 7h4v4c0 2.5-1.5 4-4 4.5M13 7h4v4c0 2.5-1.5 4-4 4.5",
  trend: "M4 16l5-5 3 3 8-8M14 6h6v6",
  dot3: "M6 12h.01M12 12h.01M18 12h.01",
  copy: "M9 9h9v11H9zM6 15H4V4h11v2",
  ext: "M14 4h6v6M20 4l-8 8M18 13v6H5V6h6",
};

function Icon({ name, size = 18, stroke = 1.7, fill = "none", style, className }) {
  const d = ICONS[name];
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
      strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
      style={style} className={className} aria-hidden="true">
      {d.split("M").filter(Boolean).map((seg, i) => <path key={i} d={"M" + seg} />)}
    </svg>
  );
}

/* ---------- Confidence meter ---------- */
function confColor(v) { return v >= 0.85 ? "var(--high)" : v >= 0.68 ? "var(--mid)" : "var(--low)"; }
function confLabel(v) { return v >= 0.85 ? "Alta confiança" : v >= 0.68 ? "Confiança média" : "Abaixo do limiar"; }

function ConfidenceMeter({ value, compact }) {
  const pct = Math.round(value * 100);
  const c = confColor(value);
  if (compact) {
    return (
      <span className="confm-compact" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 38, height: 6, borderRadius: 20, background: "var(--paper-2)", overflow: "hidden", display: "inline-block" }}>
          <span style={{ display: "block", height: "100%", width: pct + "%", background: c, borderRadius: 20 }} />
        </span>
        <b style={{ color: c, fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{pct}%</b>
      </span>
    );
  }
  return (
    <div className="confm" style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <Icon name="target" size={15} style={{ color: c }} />
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, gap: 10 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: c, whiteSpace: "nowrap" }}>{confLabel(value)}</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: c, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>{pct}% similaridade</span>
        </div>
        <div style={{ height: 7, borderRadius: 20, background: "var(--paper-2)", overflow: "hidden", position: "relative" }}>
          <div style={{ height: "100%", width: pct + "%", background: c, borderRadius: 20, transition: "width .6s cubic-bezier(.2,.7,.3,1)" }} />
          <div title="Limiar de corte (0,68)" style={{ position: "absolute", top: -2, bottom: -2, left: "68%", width: 2, background: "var(--ink-3)", opacity: .5 }} />
        </div>
      </div>
    </div>
  );
}

/* ---------- Source card ---------- */
function fileIcon(tipo) { return tipo === "pdf" ? "doc2" : "doc2"; }

function SourceCard({ src, idx }) {
  return (
    <div className="src-card">
      <span className="src-num">{idx}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="src-name"><Icon name="quote" size={13} style={{ color: "var(--accent)" }} />{src.doc}</div>
        <div className="src-sec">{src.secao}</div>
      </div>
      <ConfidenceMeter value={src.sim} compact />
    </div>
  );
}

/* ---------- Stat card ---------- */
function StatCard({ icon, label, value, delta, suffix, tint }) {
  const up = typeof delta === "number" && delta >= 0;
  return (
    <div className="card stat">
      <div className="stat-icon" style={{ background: tint || "var(--brand-100)", color: tint ? "#fff" : "var(--brand-600)" }}>
        <Icon name={icon} size={18} />
      </div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}<small>{suffix}</small></div>
      {delta != null && (
        <div className="stat-delta" style={{ color: up ? "var(--high)" : "var(--low)" }}>
          <Icon name="trend" size={13} style={{ transform: up ? "none" : "scaleY(-1)" }} />
          {up ? "+" : ""}{delta}{suffix ? "" : ""} <span className="muted" style={{ fontWeight: 500 }}>esta semana</span>
        </div>
      )}
    </div>
  );
}

/* ---------- Ring (donut) ---------- */
function Ring({ value, size = 96, stroke = 9, color = "var(--brand-600)", label, sub }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - value);
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--paper-2)" strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset .7s cubic-bezier(.2,.7,.3,1)" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
        <div>
          <div style={{ fontFamily: "var(--display)", fontWeight: 700, fontSize: size * .26, lineHeight: 1 }}>{label}</div>
          {sub && <div style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 }}>{sub}</div>}
        </div>
      </div>
    </div>
  );
}

/* ---------- Section header ---------- */
function SectionHead({ title, action, onAction }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "0 0 14px" }}>
      <h2 className="h2">{title}</h2>
      {action && <button className="btn btn-ghost" style={{ padding: "7px 13px", fontSize: 13 }} onClick={onAction}>{action}</button>}
    </div>
  );
}

Object.assign(window, { Icon, ICONS, ConfidenceMeter, confColor, confLabel, SourceCard, StatCard, Ring, SectionHead });
