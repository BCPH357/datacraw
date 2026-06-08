/* =========================================================
   App — 主控 / 路由 / 響應式 shell（桌面側邊欄 ↔ 手機漢堡抽屜）
   ========================================================= */
function App() {
  const D = window.APP_DATA;
  const mobile = useMobile(760);
  const [stage, setStage] = useState(D && D.__embedded ? "app" : "upload"); // upload | loading | app
  const [nav, setNav] = useState("overview");   // overview | members | charts
  const [memberId, setMemberId] = useState(null);
  const [error, setError] = useState(null);
  const [drawer, setDrawer] = useState(false);
  const [analysisMode, setAnalysisMode] = useState("rule");
  const mainRef = useRef(null);

  const toTop = () => { if (mainRef.current) mainRef.current.scrollTop = 0; };
  const openMember = (id) => { setMemberId(id); setNav("members"); setDrawer(false); toTop(); };
  const go = (n) => { setNav(n); setMemberId(null); setDrawer(false); toTop(); };

  const analyze = async (arg) => {
    setError(null);
    setStage("loading");
    const bundled = window.APP_DATA;
    try {
      let res;
      if (arg === "sample") {
        res = await fetch(`/sample?mode=${encodeURIComponent(analysisMode)}`);
      } else {
        const form = new FormData();
        form.append("file", arg);
        form.append("mode", analysisMode);
        res = await fetch("/analyze", { method: "POST", body: form });
      }
      if (!res.ok) {
        let message = "分析失敗，請稍後再試。";
        try { message = (await res.json()).error || message; } catch (e) {}
        throw new Error(message);
      }
      window.APP_DATA = await res.json();
      setNav("overview"); setMemberId(null);
      setStage("app");
    } catch (e) {
      // 無後端（靜態預覽 / 離線報告）時，範例資料退回使用內建 data.js
      if (arg === "sample" && bundled) {
        window.APP_DATA = bundled;
        setNav("overview"); setMemberId(null);
        setTimeout(() => setStage("app"), 1400);
        return;
      }
      setError(e.message || "分析失敗，請確認檔案格式。");
      setStage("upload");
    }
  };

  if (stage === "upload") return <UploadView onStart={analyze} error={error} analysisMode={analysisMode} setAnalysisMode={setAnalysisMode} />;
  if (stage === "loading") return <LoadingView onDone={() => {}} />;

  const links = [
    { id: "overview", label: "總覽", ix: "01" },
    { id: "members", label: "成員陣容", ix: "02" },
    { id: "charts", label: "視覺化", ix: "03" },
  ];
  const crumb = nav === "overview" ? "總覽" : nav === "charts" ? "視覺化" : (memberId ? "人物誌" : "成員陣容");

  let content;
  if (nav === "overview") content = <OverviewView mobile={mobile} onOpenMember={openMember} goCharts={() => go("charts")} />;
  else if (nav === "members" && memberId) content = <DetailView mobile={mobile} memberId={memberId} onOpenMember={openMember} goMembers={() => setMemberId(null)} />;
  else if (nav === "members") content = <MembersView mobile={mobile} onOpenMember={openMember} />;
  else content = <ChartsView mobile={mobile} onOpenMember={openMember} />;

  return (
    <div className="shell">
      {/* 桌面側邊欄 */}
      <aside className="rail">
        <div className="rail-brand">
          <div className="rail-logo"><span className="dot"></span>datacaw</div>
          <div className="rail-sub">LINE Persona Report</div>
        </div>
        <nav className="rail-nav">
          {links.map((l) => (
            <div key={l.id} className={"rail-link" + (nav === l.id ? " active" : "")} onClick={() => go(l.id)}>
              <span className="rail-ix">{l.ix}</span>{l.label}
            </div>
          ))}
        </nav>
        <div className="rail-foot">
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>{D.group.name} {D.group.emoji}</div>
          <div className="rail-meta">{D.group.userCount} 位成員 · {D.group.days} 天<br />{D.group.messageCount.toLocaleString("en-US")} 則訊息</div>
          {!(D && D.__embedded) && (
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 14, width: "100%", justifyContent: "center" }}
              onClick={() => { setStage("upload"); setNav("overview"); setMemberId(null); }}>↺ 重新分析</button>
          )}
        </div>
      </aside>

      <main className="main" ref={mainRef} style={{ height: "100vh", overflowY: "auto" }}>
        {/* 手機頂部列 */}
        <div className="m-topbar">
          <div className="m-brand"><span className="dot"></span>datacaw</div>
          <span className="m-crumb">{crumb}</span>
          <button className="m-burger" onClick={() => setDrawer(!drawer)} aria-label="選單"><span></span><span></span><span></span></button>
        </div>

        <div className="wrap" style={{ paddingTop: 30 }}>{content}</div>
      </main>

      {/* 手機抽屜 */}
      <div className={"m-scrim" + (drawer ? " open" : "")} onClick={() => setDrawer(false)}></div>
      <aside className={"m-drawer" + (drawer ? " open" : "")}>
        <div className="m-drawer-brand">
          <div className="m-drawer-logo"><span className="dot"></span>datacaw</div>
          <div className="m-drawer-sub">LINE Persona Report</div>
        </div>
        <nav className="m-drawer-nav">
          {links.map((l) => (
            <button key={l.id} className={"m-nav-link" + (nav === l.id ? " active" : "")} onClick={() => go(l.id)}>
              <span className="ix">{l.ix}</span><span className="lbl">{l.label}</span><span className="arr">→</span>
            </button>
          ))}
        </nav>
        <div className="m-drawer-foot">
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 3 }}>{D.group.name} {D.group.emoji}</div>
          <div className="rail-meta">{D.group.userCount} 位成員 · {D.group.days} 天<br />{D.group.messageCount.toLocaleString("en-US")} 則訊息</div>
          {!(D && D.__embedded) && (
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 14, width: "100%", justifyContent: "center" }}
              onClick={() => { setStage("upload"); setNav("overview"); setMemberId(null); setDrawer(false); }}>↺ 重新分析</button>
          )}
        </div>
      </aside>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
