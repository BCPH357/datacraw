/* =========================================================
   圖表元件（全 SVG / CSS 手繪）
   ========================================================= */
const { useState, useMemo, useRef, useEffect } = React;

/* ---------- 格式化 ---------- */
function fmtVal(key, val) {
  const meta = (window.APP_DATA.FEATURES[key]) || {};
  let s;
  switch (meta.fmt) {
    case "pct": s = Math.round(val * 100) + "%"; break;
    case "f1":  s = val.toFixed(1); break;
    case "f0":  s = Math.round(val).toString(); break;
    case "int": s = Math.round(val).toLocaleString("en-US"); break;
    default:    s = String(val);
  }
  return meta.unit ? s + " " + meta.unit : s;
}
function cvarOf(role) { return "var(" + window.APP_DATA.ROLES[role].cvar + ")"; }
function softOf(role) { return "var(" + window.APP_DATA.ROLES[role].soft + ")"; }
function useMobile(bp = 760) {
  const q = "(max-width: " + bp + "px)";
  const [m, setM] = useState(() => typeof window !== "undefined" && window.matchMedia(q).matches);
  useEffect(() => {
    const mq = window.matchMedia(q);
    const h = (e) => setM(e.matches);
    mq.addEventListener ? mq.addEventListener("change", h) : mq.addListener(h);
    setM(mq.matches);
    return () => { mq.removeEventListener ? mq.removeEventListener("change", h) : mq.removeListener(h); };
  }, []);
  return m;
}

/* ====================================================
   雷達圖
   ==================================================== */
function Radar({ stats, axes, color, size = 240, fill = 0.16, showLabels = true, animate = true }) {
  const cx = size / 2, cy = size / 2;
  const pad = showLabels ? 46 : 14;
  const R = size / 2 - pad;
  const n = axes.length;
  const angle = (i) => (Math.PI * 2 * i) / n - Math.PI / 2;
  const pt = (i, r) => [cx + Math.cos(angle(i)) * R * r, cy + Math.sin(angle(i)) * R * r];

  const rings = [0.25, 0.5, 0.75, 1];
  const dataPts = axes.map((a, i) => pt(i, Math.max(0.04, (stats[a] || 0) / 100)));
  const poly = dataPts.map((p) => p.join(",")).join(" ");

  const [shown, setShown] = useState(!animate);
  useEffect(() => { if (animate) { const t = setTimeout(() => setShown(true), 60); return () => clearTimeout(t); } }, [animate]);

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width="100%" style={{ display: "block" }}>
      {rings.map((r, ri) => (
        <polygon key={ri}
          points={axes.map((a, i) => pt(i, r).join(",")).join(" ")}
          fill="none" stroke="var(--line)" strokeWidth={ri === rings.length - 1 ? 1.2 : 1} />
      ))}
      {axes.map((a, i) => {
        const [x, y] = pt(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeWidth="1" />;
      })}
      <polygon points={poly} fill={color} fillOpacity={fill} stroke={color} strokeWidth="2"
        style={{
          transformOrigin: "center", transform: shown ? "scale(1)" : "scale(0.02)",
          opacity: shown ? 1 : 0, transition: "transform .7s cubic-bezier(.2,.8,.2,1), opacity .4s ease",
        }} />
      {dataPts.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r="3.4" fill="var(--surface)" stroke={color} strokeWidth="2"
          style={{ opacity: shown ? 1 : 0, transition: "opacity .4s ease .3s" }} />
      ))}
      {showLabels && axes.map((a, i) => {
        const [x, y] = pt(i, 1.16);
        const anchor = Math.abs(x - cx) < 6 ? "middle" : x > cx ? "start" : "end";
        return (
          <g key={i}>
            <text x={x} y={y - 4} textAnchor={anchor} dominantBaseline="middle"
              style={{ fontFamily: "var(--sans)", fontSize: 12.5, fontWeight: 600, fill: "var(--ink)" }}>{a}</text>
            <text x={x} y={y + 12} textAnchor={anchor} dominantBaseline="middle"
              style={{ fontFamily: "var(--mono)", fontSize: 11, fill: "var(--ink-3)" }}>{stats[a]}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ====================================================
   甜甜圈（角色分布）
   ==================================================== */
function Donut({ data, size = 230, thickness = 30, onHover }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = size / 2 - 6;
  const inner = r - thickness;
  const cx = size / 2, cy = size / 2;
  let acc = -Math.PI / 2;
  const [hi, setHi] = useState(-1);

  const arc = (a0, a1) => {
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const p = (a, rad) => [cx + Math.cos(a) * rad, cy + Math.sin(a) * rad];
    const [x0, y0] = p(a0, r), [x1, y1] = p(a1, r);
    const [x2, y2] = p(a1, inner), [x3, y3] = p(a0, inner);
    return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} L ${x2} ${y2} A ${inner} ${inner} 0 ${large} 0 ${x3} ${y3} Z`;
  };

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width="100%" style={{ display: "block" }}>
      {data.map((d, i) => {
        const a0 = acc, a1 = acc + (d.value / total) * Math.PI * 2; acc = a1;
        const active = hi === i;
        return (
          <path key={i} d={arc(a0, a1 - 0.012)} fill={d.color}
            opacity={hi === -1 || active ? 1 : 0.32}
            style={{ cursor: "pointer", transition: "opacity .18s ease, transform .2s ease",
              transformOrigin: "center", transform: active ? "scale(1.035)" : "scale(1)" }}
            onMouseEnter={() => { setHi(i); onHover && onHover(d); }}
            onMouseLeave={() => { setHi(-1); onHover && onHover(null); }} />
        );
      })}
      <text x={cx} y={cy - 6} textAnchor="middle"
        style={{ fontFamily: "var(--serif)", fontWeight: 700, fontSize: 34, fill: "var(--ink)" }}>{data.length}</text>
      <text x={cx} y={cy + 16} textAnchor="middle"
        style={{ fontFamily: "var(--mono)", fontSize: 10.5, letterSpacing: ".1em", fill: "var(--ink-3)" }}>ROLE TYPES</text>
    </svg>
  );
}

/* ====================================================
   排行長條（訊息量）
   ==================================================== */
function BarRanking({ rows, onPick }) {
  const max = Math.max(...rows.map((r) => r.value));
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {rows.map((r, i) => (
        <div key={r.id} onClick={() => onPick && onPick(r.id)}
          style={{ display: "grid", gridTemplateColumns: "26px 64px 1fr 78px", alignItems: "center",
            gap: 12, padding: "11px 0", borderBottom: "1px solid var(--line)", cursor: onPick ? "pointer" : "default" }}
          className="bar-row">
          <span className="mono" style={{ fontSize: 12, color: "var(--ink-4)" }}>{String(i + 1).padStart(2, "0")}</span>
          <span style={{ fontWeight: 600, fontSize: 14, whiteSpace: "nowrap" }}>{r.name}</span>
          <div style={{ height: 22, background: "var(--paper-2)", position: "relative", overflow: "hidden" }}>
            <div style={{ position: "absolute", inset: 0, width: `${(r.value / max) * 100}%`,
              background: r.color, transition: "width .9s cubic-bezier(.2,.8,.2,1)" }} />
          </div>
          <span className="num" style={{ textAlign: "right", fontSize: 17 }}>{r.value.toLocaleString("en-US")}</span>
        </div>
      ))}
    </div>
  );
}

/* ====================================================
   時段熱力圖
   ==================================================== */
function Heatmap({ data, onPick, mobile = false, dotted = false }) {
  const hours = Array.from({ length: 24 }, (_, h) => h);
  const ticks = [0, 6, 12, 18, 23];
  return (
    <div style={{ overflowX: mobile ? "visible" : "auto" }}>
      <div style={{ minWidth: mobile ? 0 : 560 }}>
        <div style={{ display: "grid", gridTemplateColumns: (mobile ? "40px" : "62px") + " repeat(24, " + (mobile ? "minmax(0, 1fr)" : "1fr") + ")", gap: mobile ? 1.5 : 3 }}>
          <div></div>
          {hours.map((h) => (
            <div key={h} className="mono" style={{ fontSize: 9, color: "var(--ink-4)", textAlign: "center", height: 14 }}>
              {ticks.includes(h) ? String(h).padStart(2, "0") : ""}
            </div>
          ))}
          {data.map((row) => (
            <React.Fragment key={row.id}>
              <div onClick={() => onPick && onPick(row.id)}
                style={{ fontSize: 12.5, fontWeight: 600, display: "flex", alignItems: "center",
                  justifyContent: mobile ? "flex-start" : "flex-end", paddingRight: mobile ? 4 : 8, cursor: onPick ? "pointer" : "default" }}>{row.name}</div>
              {row.hours.map((v, h) => dotted ? (
                <div key={h} style={{ aspectRatio: "1 / 1.5", display: "grid", placeItems: "center" }}>
                  <span style={{ width: Math.max(2, 7 * v), height: Math.max(2, 7 * v), borderRadius: 999, background: cvarOf(row.role), opacity: 0.25 + v * 0.75 }} />
                </div>
              ) : (
                <div key={h} title={`${row.name} · ${String(h).padStart(2, "0")}:00`}
                  style={{ aspectRatio: mobile ? "1 / 1.5" : "1 / 1.05", background: cvarOf(row.role),
                    opacity: 0.10 + v * 0.9, borderRadius: 1 }} />
              ))}
            </React.Fragment>
          ))}
        </div>
        <div style={{ display: "flex", gap: 16, marginTop: 16, alignItems: "center", flexWrap: "wrap" }}>
          {!mobile && <span className="kicker">作息</span>}
          {[["00\u201306", "\u591c"], ["06\u201312", "\u6668"], ["12\u201318", "\u5348"], ["18\u201324", "\u665a"]].map(([t, l]) => (
            <span key={t} className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{l} {t}</span>
          ))}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 7 }}>
            <span className="mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>少</span>
            {[0.15, 0.4, 0.65, 0.9, 1].map((o) => (
              <div key={o} style={{ width: 16, height: 12, background: "var(--ink)", opacity: o }} />
            ))}
            <span className="mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>多</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ====================================================
   分群散佈
   ==================================================== */
function Scatter({ points, members, meta, size = 440, onPick }) {
  const pad = 30;
  const span = size - pad * 2;
  const byId = useMemo(() => Object.fromEntries(members.map((m) => [m.id, m])), [members]);
  const [hi, setHi] = useState(null);
  const X = (x) => pad + x * span;
  const Y = (y) => pad + (1 - y) * span;

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width="100%" style={{ display: "block" }}>
      {[0.25, 0.5, 0.75].map((g) => (
        <g key={g}>
          <line x1={X(g)} y1={pad} x2={X(g)} y2={size - pad} stroke="var(--line)" strokeDasharray="2 4" />
          <line x1={pad} y1={Y(g)} x2={size - pad} y2={Y(g)} stroke="var(--line)" strokeDasharray="2 4" />
        </g>
      ))}
      <line x1={pad} y1={size - pad} x2={size - pad} y2={size - pad} stroke="var(--ink)" strokeWidth="1.2" />
      <line x1={pad} y1={pad} x2={pad} y2={size - pad} stroke="var(--ink)" strokeWidth="1.2" />
      {/* cluster hulls (soft blobs) */}
      {meta.clusters.map((cl) => {
        const pts = points.filter((p) => p.c === cl.id);
        const mx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
        const my = pts.reduce((s, p) => s + p.y, 0) / pts.length;
        return <circle key={cl.id} cx={X(mx)} cy={Y(my)} r="62" fill={`var(${cl.cvar})`} opacity="0.07" />;
      })}
      {points.map((p) => {
        const m = byId[p.id];
        const cl = meta.clusters[p.c];
        const active = hi === p.id;
        return (
          <g key={p.id} style={{ cursor: "pointer" }}
            onMouseEnter={() => setHi(p.id)} onMouseLeave={() => setHi(null)}
            onClick={() => onPick && onPick(p.id)}>
            <circle cx={X(p.x)} cy={Y(p.y)} r={active ? 11 : 8} fill={`var(${cl.cvar})`}
              stroke="var(--surface)" strokeWidth="2" style={{ transition: "r .15s ease" }} />
            <text x={X(p.x)} y={Y(p.y) - 14} textAnchor="middle"
              style={{ fontFamily: "var(--sans)", fontSize: 12, fontWeight: 600, fill: "var(--ink)",
                opacity: active ? 1 : 0.78 }}>{m.name}</text>
          </g>
        );
      })}
      <text x={size - pad} y={size - pad + 18} textAnchor="end"
        style={{ fontFamily: "var(--mono)", fontSize: 10, fill: "var(--ink-4)" }}>主成分 1 →</text>
      <text x={pad - 8} y={pad - 10} textAnchor="start"
        style={{ fontFamily: "var(--mono)", fontSize: 10, fill: "var(--ink-4)" }}>↑ 主成分 2</text>
    </svg>
  );
}

/* 分群卡片（手機用，取代散佈圖） */
function ClusterCards({ meta, scatter, members, onPick }) {
  const byId = Object.fromEntries(members.map((m) => [m.id, m]));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1, background: "var(--line)", border: "1px solid var(--line)" }}>
      {meta.clusters.map((c) => {
        const mem = scatter.filter((p) => p.c === c.id).map((p) => byId[p.id]).filter(Boolean);
        return (
          <div key={c.id} style={{ background: "var(--surface)", padding: "15px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 11 }}>
              <span style={{ width: 11, height: 11, borderRadius: 3, background: `var(${c.cvar})`, flex: "0 0 auto" }} />
              <span className="serif" style={{ fontWeight: 700, fontSize: 16 }}>{c.name}</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: "auto" }}>{mem.length} 位</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
              {mem.map((m) => (
                <button key={m.id} onClick={() => onPick && onPick(m.id)}
                  style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "6px 10px 6px 7px",
                    border: "1px solid var(--line-2)", background: "var(--paper)", cursor: "pointer" }}>
                  <span style={{ width: 22, height: 22, flex: "0 0 auto", background: softOf(m.role), border: `1.5px solid ${cvarOf(m.role)}`, display: "grid", placeItems: "center" }}>
                    <span className="serif" style={{ fontSize: 11, fontWeight: 700, color: cvarOf(m.role), lineHeight: 1 }}>{window.APP_DATA.ROLES[m.role].glyph}</span>
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{m.name}</span>
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { Radar, Donut, BarRanking, Heatmap, Scatter, ClusterCards, useMobile, fmtVal, cvarOf, softOf });
