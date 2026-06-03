/* =========================================================
   角色卡元件（個性測驗結果卡 / 遊戲角色卡）
   ========================================================= */

/* 角色印章 */
function Seal({ role, size = 64, glyphSize }) {
  const D = window.APP_DATA;
  const meta = D.ROLES[role];
  return (
    <div style={{ width: size, height: size, flex: "0 0 auto", background: softOf(role),
      border: `1.5px solid ${cvarOf(role)}`, display: "grid", placeItems: "center", position: "relative" }}>
      <span className="serif" style={{ fontSize: glyphSize || size * 0.5, fontWeight: 700,
        color: cvarOf(role), lineHeight: 1 }}>{meta.glyph}</span>
    </div>
  );
}

/* 角色標籤 chip */
function RoleTag({ role, solid = false }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7, fontFamily: "var(--mono)",
      fontSize: 11, letterSpacing: ".04em", padding: "4px 10px", whiteSpace: "nowrap",
      border: `1px solid ${cvarOf(role)}`, color: solid ? "#fff" : cvarOf(role),
      background: solid ? cvarOf(role) : "transparent" }}>
      <span style={{ width: 7, height: 7, borderRadius: 2, background: solid ? "#fff" : cvarOf(role) }}></span>
      {role}
    </span>
  );
}

/* 六維 equalizer */
function Equalizer({ stats, axes, role, height = 44 }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${axes.length}, 1fr)`, gap: 6, alignItems: "end", height }}>
      {axes.map((a) => (
        <div key={a} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5, height: "100%" }}>
          <div style={{ flex: 1, width: "100%", display: "flex", alignItems: "flex-end", background: "var(--paper-2)" }}>
            <div style={{ width: "100%", height: `${stats[a]}%`, background: cvarOf(role),
              transition: "height .8s cubic-bezier(.2,.8,.2,1)" }} />
          </div>
          <span className="mono" style={{ fontSize: 9, color: "var(--ink-3)" }}>{a}</span>
        </div>
      ))}
    </div>
  );
}

/* 單一橫向 stat bar */
function StatBar({ label, value, max = 100, color, suffix = "" }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "84px 1fr 52px", alignItems: "center", gap: 12, padding: "6px 0" }}>
      <span style={{ fontSize: 13, color: "var(--ink-2)" }}>{label}</span>
      <div style={{ height: 8, background: "var(--paper-2)", position: "relative" }}>
        <div style={{ position: "absolute", inset: 0, width: `${(value / max) * 100}%`, background: color,
          transition: "width .8s cubic-bezier(.2,.8,.2,1)" }} />
      </div>
      <span className="num" style={{ fontSize: 14, textAlign: "right" }}>{value}{suffix}</span>
    </div>
  );
}

/* 角色卡（網格用） */
function PersonaCard({ m, index, onOpen }) {
  const D = window.APP_DATA;
  const meta = D.ROLES[m.role];
  return (
    <div className="pcard" onClick={() => onOpen(m.id)}
      style={{ background: "var(--surface)", border: "1px solid var(--line)", cursor: "pointer",
        display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>
      <div style={{ height: 4, background: cvarOf(m.role) }}></div>
      <div style={{ padding: "16px 20px 12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>NO.{String(index + 1).padStart(2, "0")}</span>
        <RoleTag role={m.role} />
      </div>
      <div style={{ padding: "0 20px", display: "flex", gap: 16, alignItems: "center" }}>
        <Seal role={m.role} size={62} />
        <div style={{ minWidth: 0 }}>
          <div className="serif" style={{ fontSize: 25, fontWeight: 700, lineHeight: 1.1 }}>{meta.title}</div>
          <div style={{ fontSize: 14, color: "var(--ink-2)", marginTop: 3 }}>{m.name}</div>
        </div>
      </div>
      <p className="serif" style={{ margin: "16px 20px 4px", fontSize: 15.5, color: "var(--ink)", lineHeight: 1.5 }}>
        「{m.tagline}」
      </p>
      <div style={{ padding: "10px 20px 0" }}>
        <Equalizer stats={m.stats} axes={D.AXES} role={m.role} height={46} />
      </div>
      <div style={{ marginTop: 16, padding: "12px 20px", borderTop: "1px solid var(--line)",
        display: "flex", justifyContent: "space-between", fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--ink-2)" }}>
        <span>{m.f.message_count.toLocaleString("en-US")} 則</span>
        <span>活躍 {m.f.active_days} 天</span>
        <span style={{ color: cvarOf(m.role), fontWeight: 700 }}>檢視 →</span>
      </div>
    </div>
  );
}

Object.assign(window, { Seal, RoleTag, Equalizer, StatBar, PersonaCard });
