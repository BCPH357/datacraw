/* =========================================================
   App — 主控 / 路由 / shell
   ========================================================= */
function App() {
  const D = window.APP_DATA;
  // When real data is injected (Streamlit embed / offline report) skip the
  // demo upload + loading screens and land directly on the dashboard.
  const [stage, setStage] = useState(D && D.__embedded ? "app" : "upload"); // upload | loading | app
  const [nav, setNav] = useState("overview");   // overview | members | charts
  const [memberId, setMemberId] = useState(null);
  const [error, setError] = useState(null);
  const mainRef = useRef(null);

  const openMember = (id) => { setMemberId(id); setNav("members"); mainRef.current && (mainRef.current.scrollTop = 0); };
  const go = (n) => { setNav(n); setMemberId(null); mainRef.current && (mainRef.current.scrollTop = 0); };

  // Send the chosen file (or the "sample" sentinel) to the backend, then render
  // the main screen from the real data it returns.
  const analyze = async (arg) => {
    setError(null);
    setStage("loading");
    try {
      let res;
      if (arg === "sample") {
        res = await fetch("/sample");
      } else {
        const form = new FormData();
        form.append("file", arg);
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
      setError(e.message || "分析失敗，請確認檔案格式。");
      setStage("upload");
    }
  };

  if (stage === "upload") return <UploadView onStart={analyze} error={error} />;
  if (stage === "loading") return <LoadingView onDone={() => {}} />;

  const links = [
    { id: "overview", label: "總覽", ix: "01" },
    { id: "members", label: "成員陣容", ix: "02" },
    { id: "charts", label: "視覺化", ix: "03" },
  ];

  let content;
  if (nav === "overview") content = <OverviewView onOpenMember={openMember} goCharts={() => go("charts")} />;
  else if (nav === "members" && memberId) content = <DetailView memberId={memberId} onOpenMember={openMember} goMembers={() => setMemberId(null)} />;
  else if (nav === "members") content = <MembersView onOpenMember={openMember} />;
  else content = <ChartsView onOpenMember={openMember} />;

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail-brand">
          <div className="rail-logo"><span className="dot"></span>datacaw</div>
          <div className="rail-sub">LINE Persona Report</div>
        </div>
        <nav className="rail-nav">
          {links.map((l) => (
            <div key={l.id} className={"rail-link" + (nav === l.id ? " active" : "")}
              onClick={() => go(l.id)}>
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
        <div className="wrap" style={{ paddingTop: 30 }}>{content}</div>
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
