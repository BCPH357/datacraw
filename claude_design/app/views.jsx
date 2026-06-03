/* =========================================================
   頁面視圖
   ========================================================= */

/* 區塊標頭 */
function SectionHead({ kicker, title, note, right }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between",
      borderBottom: "1px solid var(--ink)", paddingBottom: 12, marginBottom: 20, gap: 16 }}>
      <div>
        {kicker && <div className="kicker" style={{ marginBottom: 8 }}>{kicker}</div>}
        <h2 style={{ fontSize: 28 }}>{title}</h2>
        {note && <p style={{ margin: "6px 0 0", color: "var(--ink-2)", fontSize: 14, maxWidth: 620 }}>{note}</p>}
      </div>
      {right}
    </div>
  );
}

/* 半圓健康儀表 */
function Gauge({ value, size = 220 }) {
  const r = size / 2 - 14;
  const cx = size / 2, cy = size / 2;
  const a0 = Math.PI, a1 = 0;
  const ang = a0 + (a1 - a0) * (value / 100);
  // Top semicircle: subtract sin so points sit above the center line (SVG y is
  // inverted). Using +sin placed the value arc + marker on the bottom half,
  // making the indicator swoosh downward across the score.
  const p = (a, rad = r) => [cx + Math.cos(a) * rad, cy - Math.sin(a) * rad];
  const [sx, sy] = p(a0), [ex, ey] = p(a1), [vx, vy] = p(ang);
  const large = 0;
  const col = value >= 75 ? "var(--accent)" : value >= 55 ? "var(--r-topic)" : "var(--r-core)";
  return (
    <svg viewBox={`0 0 ${size} ${size * 0.62}`} width="100%" style={{ display: "block" }}>
      <path d={`M ${sx} ${sy} A ${r} ${r} 0 ${large} 1 ${ex} ${ey}`} fill="none" stroke="var(--paper-3)" strokeWidth="14" strokeLinecap="butt" />
      <path d={`M ${sx} ${sy} A ${r} ${r} 0 0 1 ${vx} ${vy}`} fill="none" stroke={col} strokeWidth="14" strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 1s ease" }} />
      <circle cx={vx} cy={vy} r="7" fill="var(--surface)" stroke={col} strokeWidth="3" />
      <text x={cx} y={cy - 6} textAnchor="middle" style={{ fontFamily: "var(--serif)", fontWeight: 700, fontSize: 52, fill: "var(--ink)" }}>{value}</text>
      <text x={cx} y={cy + 18} textAnchor="middle" style={{ fontFamily: "var(--mono)", fontSize: 11, letterSpacing: ".12em", fill: "var(--ink-3)" }}>/ 100 健康分數</text>
    </svg>
  );
}

/* ---------- 上傳 ---------- */
function UploadView({ onStart, error }) {
  const D = window.APP_DATA;
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);
  const pick = () => inputRef.current && inputRef.current.click();
  const handleFiles = (files) => { const f = files && files[0]; if (f) onStart(f); };
  return (
    <div style={{ maxWidth: 920, margin: "0 auto", padding: "min(9vh, 90px) 40px 80px" }}>
      <div className="kicker" style={{ marginBottom: 22 }}>datacaw — LINE 群組人物誌報告</div>
      <h1 style={{ fontSize: "clamp(44px, 7vw, 82px)", lineHeight: 1.02, letterSpacing: "-0.02em", maxWidth: 14 + "ch" }}>
        你的群組，<br />其實是一齣<span style={{ color: "var(--accent)" }}>群像劇</span>。
      </h1>
      <p style={{ fontSize: 18, color: "var(--ink-2)", maxWidth: 560, marginTop: 22, lineHeight: 1.6 }}>
        上傳一份 LINE 對話記錄，我們會解析每個人的發言節奏、作息與互動方式，
        替群組裡的每個人寫一張專屬的「人物誌角色卡」。
      </p>

      <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
        style={{ marginTop: 40, border: `1.5px dashed ${drag ? "var(--accent)" : "var(--line-2)"}`,
          background: drag ? "var(--accent-3)" : "var(--surface)", padding: "44px 32px", textAlign: "center",
          transition: "all .15s ease" }}>
        <div className="serif" style={{ fontSize: 22, fontWeight: 700 }}>拖曳 LINE 對話記錄 <span className="mono" style={{ fontSize: 15, color: "var(--ink-3)" }}>.txt</span></div>
        <div style={{ color: "var(--ink-3)", fontSize: 13.5, marginTop: 8 }}>LINE 聊天室 → 設定 → 匯出聊天記錄。檔案只在本機處理，不會被保存。</div>
        <input ref={inputRef} type="file" accept=".txt,text/plain" style={{ display: "none" }}
          onChange={(e) => handleFiles(e.target.files)} />
        <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 24 }}>
          <button className="btn" onClick={pick}>選擇檔案</button>
          <button className="btn btn-ghost" onClick={() => onStart("sample")}>使用範例資料 ↗</button>
        </div>
        {error && (
          <div style={{ marginTop: 20, color: "var(--r-core)", fontSize: 14, fontWeight: 600 }}>⚠ {error}</div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, marginTop: 48,
        border: "1px solid var(--line)", background: "var(--line)" }}>
        {[["8", "種人物角色", "從高頻核心到深夜長文"], ["20+", "項行為特徵", "作息、用詞、回覆習慣"], ["1", "份群組健康報告", "誰扛起對話、誰快變幽靈"]].map(([n, t, d], i) => (
          <div key={i} style={{ background: "var(--surface)", padding: "22px 22px" }}>
            <div className="num" style={{ fontSize: 38 }}>{n}</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>{t}</div>
            <div style={{ color: "var(--ink-3)", fontSize: 13, marginTop: 3 }}>{d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- 載入動畫 ---------- */
function LoadingView({ onDone }) {
  const steps = ["解析對話記錄", "抽取每位成員的行為特徵", "分群並尋找最佳分組", "指派人物角色與稱號", "計算群組健康度"];
  const [i, setI] = useState(0);
  useEffect(() => {
    if (i >= steps.length) { const t = setTimeout(onDone, 480); return () => clearTimeout(t); }
    const t = setTimeout(() => setI(i + 1), 620);
    return () => clearTimeout(t);
  }, [i]);
  const pct = Math.min(100, Math.round((i / steps.length) * 100));
  return (
    <div style={{ maxWidth: 560, margin: "0 auto", padding: "16vh 40px" }}>
      <div className="kicker" style={{ marginBottom: 18 }}>分析中 · ANALYSING</div>
      <h2 className="serif" style={{ fontSize: 34 }}>正在解讀你的群組 💬</h2>
      <div style={{ height: 3, background: "var(--paper-3)", marginTop: 28, position: "relative" }}>
        <div style={{ position: "absolute", inset: 0, width: pct + "%", background: "var(--accent)", transition: "width .5s ease" }} />
      </div>
      <div style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 12 }}>
        {steps.map((s, k) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 12,
            opacity: k <= i ? 1 : 0.32, transition: "opacity .3s ease" }}>
            <span className="mono" style={{ fontSize: 13, width: 18,
              color: k < i ? "var(--accent)" : "var(--ink-3)" }}>{k < i ? "✓" : k === i ? "▸" : "·"}</span>
            <span style={{ fontSize: 15, fontWeight: k === i ? 600 : 400 }}>{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- 總覽 ---------- */
function OverviewView({ onOpenMember, goCharts }) {
  const D = window.APP_DATA;
  const g = D.group;
  const donutData = Object.entries(D.roleDist).map(([role, v]) => ({ label: role, value: v, color: cvarOf(role) }));
  const [hover, setHover] = useState(null);

  const metricBars = [
    { label: "發言均衡", v: Math.round((1 - g.dependency) * 100), note: "最高發言者占 21%" },
    { label: "角色多樣", v: Math.round(g.diversity * 100), note: "9 人中有 8 種角色" },
    { label: "在線參與", v: Math.round((1 - g.ghost) * 100), note: "沒有人接近幽靈狀態" },
  ];

  return (
    <div className="view-enter">
      <div className="masthead">
        <div className="masthead-l">
          <div className="edition">
            <span className="tag solid">人物誌報告 No.01</span>
            <span className="tag">{g.range}</span>
          </div>
          <h1 style={{ fontSize: "clamp(36px, 5vw, 58px)", lineHeight: 1.02 }}>{g.name} <span style={{ fontSize: "0.7em" }}>{g.emoji}</span></h1>
        </div>
        <div style={{ textAlign: "right", flex: "0 0 auto" }}>
          <div className="kicker">涵蓋期間</div>
          <div className="num" style={{ fontSize: 30 }}>{g.days}<span className="stat-u">天</span></div>
        </div>
      </div>

      {/* 指標列 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, background: "var(--line)",
        border: "1px solid var(--line)", marginBottom: 34 }}>
        {[["訊息總數", g.messageCount.toLocaleString("en-US"), ""], ["參與成員", g.userCount, "人"],
          ["群組健康", g.health, "/100"], ["角色種類", Object.keys(D.roleDist).length, "種"]].map(([k, v, u], i) => (
          <div key={i} className="stat" style={{ background: "var(--surface)", padding: "18px 22px" }}>
            <div className="stat-k">{k}</div>
            <div className="stat-v">{v}<span className="stat-u">{u}</span></div>
          </div>
        ))}
      </div>

      {/* 健康 + 角色分布 */}
      <div style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr", gap: 18, marginBottom: 34 }}>
        <div className="panel">
          <div className="panel-head"><span className="panel-title">群組健康度</span><span className="kicker">GROUP HEALTH</span></div>
          <div className="panel-pad" style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 28, alignItems: "center" }}>
            <Gauge value={g.health} />
            <div>
              <p className="serif" style={{ fontSize: 18, lineHeight: 1.5, margin: "0 0 16px" }}>
                這是一個分工健康的群組——對話沒有過度集中在某個人身上，角色也夠多元。
              </p>
              {metricBars.map((b) => (
                <div key={b.label} style={{ marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600 }}>{b.label}</span>
                    <span className="num">{b.v}</span>
                  </div>
                  <div style={{ height: 6, background: "var(--paper-2)" }}>
                    <div style={{ height: "100%", width: b.v + "%", background: "var(--accent)" }} />
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 3 }}>{b.note}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><span className="panel-title">角色分布</span><span className="kicker">ROLES</span></div>
          <div className="panel-pad" style={{ display: "grid", gridTemplateColumns: "150px 1fr", gap: 16, alignItems: "center" }}>
            <Donut data={donutData} size={150} thickness={22} onHover={setHover} />
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {donutData.map((d) => (
                <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 9, padding: "3px 0",
                  opacity: hover && hover.label !== d.label ? 0.4 : 1, transition: "opacity .15s" }}>
                  <span style={{ width: 9, height: 9, background: d.color, borderRadius: 2, flex: "0 0 auto" }} />
                  <span style={{ fontSize: 12.5, flex: 1 }}>{d.label}</span>
                  <span className="mono" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 群組之最 */}
      <SectionHead kicker="HALL OF FAME" title="群組之最" note="每個群組都有幾個無法取代的角色。" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, background: "var(--line)",
        border: "1px solid var(--line)", marginBottom: 36 }}>
        {D.superlatives.map((s, i) => (
          <div key={i} style={{ background: "var(--surface)", padding: "20px 22px", cursor: "pointer" }} className="sup-cell"
            onClick={() => onOpenMember(D.members.find((m) => m.name === s.who).id)}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <span className="kicker">{s.key}</span>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: cvarOf(s.role) }} />
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span className="num" style={{ fontSize: 34, color: cvarOf(s.role) }}>{s.val}</span>
              <span style={{ fontSize: 13, color: "var(--ink-3)" }}>{s.unit}</span>
            </div>
            <div style={{ fontWeight: 700, fontSize: 16, marginTop: 6 }}>{s.who}</div>
            <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 2 }}>{s.note}</div>
          </div>
        ))}
      </div>

      {/* 觀察重點 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <div className="panel">
          <div className="panel-head"><span className="panel-title">觀察重點</span><span className="kicker">NOTES</span></div>
          <div className="panel-pad" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {D.observations.map((o, i) => (
              <div key={i} style={{ display: "flex", gap: 12 }}>
                <span style={{ flex: "0 0 auto", width: 22, height: 22, display: "grid", placeItems: "center",
                  background: o.tone === "good" ? "var(--accent-3)" : "var(--r-topic-soft)",
                  color: o.tone === "good" ? "var(--accent-2)" : "var(--r-topic)", fontSize: 13, fontWeight: 700,
                  fontFamily: "var(--mono)" }}>{o.tone === "good" ? "✓" : "!"}</span>
                <span style={{ fontSize: 14.5, lineHeight: 1.5 }}>{o.text}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div className="panel-head"><span className="panel-title">分群結果</span><span className="kicker">CLUSTERS · K={D.clusterMeta.best_k}</span></div>
          <div className="panel-pad" style={{ flex: 1 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {D.clusterMeta.clusters.map((c) => (
                <div key={c.id} style={{ border: "1px solid var(--line)", padding: "12px 14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 9, height: 9, borderRadius: 2, background: `var(${c.cvar})` }} />
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{c.name}</span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 4 }}>
                    {D.scatter.filter((p) => p.c === c.id).length} 位成員
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="panel-pad" style={{ borderTop: "1px solid var(--line)", paddingTop: 14 }}>
            <button className="btn btn-ghost btn-sm" onClick={goCharts}>看完整分群圖 →</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SectionHead, Gauge, UploadView, LoadingView, OverviewView });
