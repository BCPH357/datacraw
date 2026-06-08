/* =========================================================
   頁面視圖（二）：成員列表 / 成員詳細 / 圖表
   桌面與手機共用，透過 mobile 旗標切換版面
   ========================================================= */

/* ---------- 成員列表 ---------- */
function MembersView({ mobile, onOpenMember }) {
  const D = window.APP_DATA;
  const roles = Object.keys(D.ROLES).filter((r) => D.members.some((m) => m.role === r));
  const [filter, setFilter] = useState(null);
  const shown = filter ? D.members.filter((m) => m.role === filter) : D.members;

  return (
    <div className="view-enter">
      <SectionHead kicker="THE CAST · 成員陣容" title="九個人，九張角色卡"
        note="每位成員都被指派一個最貼近其發言模式的角色。點任一張卡看完整人物誌。" />

      <div style={{ display: "flex", gap: 8, flexWrap: mobile ? "nowrap" : "wrap", overflowX: mobile ? "auto" : "visible",
        marginBottom: 24, marginLeft: mobile ? -18 : 0, marginRight: mobile ? -18 : 0,
        paddingLeft: mobile ? 18 : 0, paddingRight: mobile ? 18 : 0, paddingBottom: mobile ? 6 : 0, alignItems: "center" }}>
        <button onClick={() => setFilter(null)} className="chip"
          style={{ cursor: "pointer", flex: "0 0 auto", padding: mobile ? "8px 13px" : "3px 9px", fontSize: mobile ? 12 : 11,
            borderColor: !filter ? "var(--ink)" : "var(--line-2)", background: !filter ? "var(--ink)" : "transparent", color: !filter ? "var(--ink-rev)" : "var(--ink-2)" }}>
          全部 {D.members.length}
        </button>
        {roles.map((r) => (
          <button key={r} onClick={() => setFilter(filter === r ? null : r)} className="chip"
            style={{ cursor: "pointer", flex: "0 0 auto", padding: mobile ? "8px 13px" : "3px 9px", fontSize: mobile ? 12 : 11,
              borderColor: cvarOf(r), background: filter === r ? cvarOf(r) : "transparent", color: filter === r ? "#fff" : cvarOf(r) }}>
            <span className="sw" style={{ background: filter === r ? "#fff" : cvarOf(r) }} />{r}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: mobile ? "1fr" : "repeat(auto-fill, minmax(280px, 1fr))", gap: mobile ? 14 : 18 }}>
        {shown.map((m) => (
          <PersonaCard key={m.id} m={m} index={D.members.indexOf(m)} onOpen={onOpenMember} />
        ))}
      </div>
    </div>
  );
}

/* 特徵列 */
function FeatureRow({ k, member, members }) {
  const D = window.APP_DATA;
  const meta = D.FEATURES[k];
  const val = member.f[k];
  const vals = members.map((m) => m.f[k]);
  const max = Math.max(...vals);
  const sorted = [...members].sort((a, b) => b.f[k] - a.f[k]);
  const rank = sorted.findIndex((m) => m.id === member.id) + 1;
  const pct = max ? (val / max) * 100 : 0;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "92px 1fr 72px 52px", alignItems: "center", gap: 12,
      padding: "9px 0", borderBottom: "1px solid var(--line)" }}>
      <span style={{ fontSize: 13, color: "var(--ink-2)" }}>{meta.label}</span>
      <div style={{ height: 7, background: "var(--paper-2)" }}>
        <div style={{ height: "100%", width: pct + "%", background: cvarOf(member.role) }} />
      </div>
      <span className="num" style={{ fontSize: 14, textAlign: "right" }}>{fmtVal(k, val)}</span>
      <span className="mono" style={{ fontSize: 11, textAlign: "right", color: rank === 1 ? cvarOf(member.role) : "var(--ink-3)" }}>
        #{rank}
      </span>
    </div>
  );
}

/* ---------- 成員詳細 ---------- */
function DetailView({ mobile, memberId, onOpenMember, goMembers }) {
  const D = window.APP_DATA;
  const m = D.members.find((x) => x.id === memberId);
  const meta = D.ROLES[m.role];
  const idx = D.members.indexOf(m);
  const sameRole = D.members.filter((x) => x.role === m.role && x.id !== m.id);
  const sameCluster = D.members.filter((x) => x.cluster === m.cluster && x.id !== m.id);

  const groups = [
    { name: "互動量", keys: ["message_count", "active_days", "avg_messages_per_day", "avg_message_length", "unique_word_ratio"] },
    { name: "作息時段", keys: ["night_ratio", "morning_ratio", "afternoon_ratio", "evening_ratio"] },
    { name: "訊息型態", keys: ["text_ratio", "sticker_ratio", "image_ratio", "url_ratio", "emoji_ratio"] },
    { name: "對話行為", keys: ["reply_like_ratio", "question_ratio", "topic_start_count", "avg_response_time_min"] },
  ];

  return (
    <div className="view-enter">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 22 }}>
        <button className="btn btn-ghost btn-sm" onClick={goMembers}>← 成員陣容</button>
        <span className="mono" style={{ fontSize: 12, color: "var(--ink-4)" }}>NO.{String(idx + 1).padStart(2, "0")} / {D.members.length}</span>
      </div>

      {/* 角色卡 hero */}
      <div className="panel" style={{ borderTop: `4px solid ${cvarOf(m.role)}`, marginBottom: 18 }}>
        <div style={{ display: "grid", gridTemplateColumns: mobile ? "1fr" : "1.2fr 1fr", gap: 0 }}>
          <div style={{ padding: mobile ? "22px 20px" : "30px 32px", borderRight: mobile ? "none" : "1px solid var(--line)" }}>
            <RoleTag role={m.role} solid />
            <div style={{ display: "flex", gap: mobile ? 16 : 22, alignItems: "center", margin: "20px 0 16px" }}>
              <Seal role={m.role} size={mobile ? 76 : 96} />
              <div>
                <div className="serif" style={{ fontSize: mobile ? 32 : 44, fontWeight: 700, lineHeight: 1, color: cvarOf(m.role) }}>{meta.title}</div>
                <div style={{ fontSize: mobile ? 17 : 20, fontWeight: 600, marginTop: 8 }}>{m.name}</div>
              </div>
            </div>
            <p className="serif" style={{ fontSize: mobile ? 18 : 21, lineHeight: 1.45, margin: "0 0 12px" }}>「{m.tagline}」</p>
            <p style={{ fontSize: 14, color: "var(--ink-2)", lineHeight: 1.6, margin: 0 }}>{meta.desc}</p>

            <div style={{ display: "flex", gap: mobile ? 20 : 28, marginTop: 22, paddingTop: 18, borderTop: "1px solid var(--line)" }}>
              {[["訊息總數", m.f.message_count.toLocaleString("en-US")], ["活躍天數", m.f.active_days + " 天"], ["每日平均", m.f.avg_messages_per_day.toFixed(1) + " 則"]].map(([k, v]) => (
                <div key={k}>
                  <div className="kicker" style={{ marginBottom: 4 }}>{k}</div>
                  <div className="num" style={{ fontSize: mobile ? 20 : 24 }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ padding: mobile ? "18px 16px 22px" : "24px 28px", display: "flex", flexDirection: "column", justifyContent: "center",
            background: softOf(m.role), borderTop: mobile ? "1px solid var(--line)" : "none" }}>
            <div className="kicker" style={{ textAlign: "center", marginBottom: 4 }}>六維特質</div>
            <div style={{ maxWidth: mobile ? 300 : "none", margin: "0 auto", width: "100%" }}>
              <Radar stats={m.stats} axes={D.AXES} color={cvarOf(m.role)} size={300} />
            </div>
          </div>
        </div>
      </div>

      {/* 三大特徵 */}
      <div style={{ display: "grid", gridTemplateColumns: mobile ? "1fr" : "repeat(3, 1fr)", gap: 1, background: "var(--line)",
        border: "1px solid var(--line)", marginBottom: 30 }}>
        {m.top.map((k, i) => {
          const sorted = [...D.members].sort((a, b) => b.f[k] - a.f[k]);
          const rank = sorted.findIndex((x) => x.id === m.id) + 1;
          return (
            <div key={k} style={{ background: "var(--surface)", padding: "18px 22px", display: mobile ? "flex" : "block",
              alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div className="kicker">主要特徵 0{i + 1}</div>
                <div className="serif" style={{ fontSize: 22, fontWeight: 700, marginTop: 8 }}>{D.FEATURES[k].label}</div>
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginTop: mobile ? 0 : 6,
                flexDirection: mobile ? "column" : "row", textAlign: mobile ? "right" : "left" }}>
                <span className="num" style={{ fontSize: 28, color: cvarOf(m.role) }}>{fmtVal(k, m.f[k])}</span>
                <span className="mono" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>群內第 {rank} 名</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 完整特徵 + 相似成員 */}
      <div style={{ display: "grid", gridTemplateColumns: mobile ? "1fr" : "1.6fr 1fr", gap: mobile ? 30 : 18 }}>
        <div>
          <SectionHead kicker="FULL PROFILE" title="完整行為特徵" />
          <div style={{ display: "grid", gridTemplateColumns: mobile ? "1fr" : "1fr 1fr", gap: 28 }}>
            {groups.map((grp) => (
              <div key={grp.name}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ width: 7, height: 7, background: cvarOf(m.role), borderRadius: 2 }} />
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{grp.name}</span>
                </div>
                {grp.keys.map((k) => <FeatureRow key={k} k={k} member={m} members={D.members} />)}
              </div>
            ))}
          </div>
        </div>

        <div>
          <SectionHead kicker="RELATED" title="相似成員" />
          <div style={{ display: "flex", flexDirection: "column", gap: 1, background: "var(--line)", border: "1px solid var(--line)" }}>
            {(sameRole.length ? sameRole : sameCluster).slice(0, 4).map((x) => (
              <div key={x.id} onClick={() => onOpenMember(x.id)} className="bar-row"
                style={{ background: "var(--surface)", padding: "14px 16px", display: "flex", gap: 12, alignItems: "center", cursor: "pointer" }}>
                <Seal role={x.role} size={42} glyphSize={20} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{x.name}</div>
                  <div style={{ fontSize: 12, color: "var(--ink-3)" }}>{D.ROLES[x.role].title}</div>
                </div>
                <span style={{ color: cvarOf(x.role) }}>→</span>
              </div>
            ))}
            {sameRole.length === 0 && sameCluster.length === 0 && (
              <div style={{ background: "var(--surface)", padding: "16px", fontSize: 13.5, color: "var(--ink-3)" }}>
                這個角色在群組裡獨一無二。
              </div>
            )}
          </div>
          <div className="panel panel-pad" style={{ marginTop: 18 }}>
            <div className="kicker" style={{ marginBottom: 8 }}>所屬分群</div>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <span style={{ width: 11, height: 11, borderRadius: 2, background: `var(${D.clusterMeta.clusters[m.cluster].cvar})` }} />
              <span className="serif" style={{ fontSize: 18, fontWeight: 700 }}>{D.clusterMeta.clusters[m.cluster].name}</span>
            </div>
            <p style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 6, marginBottom: 0 }}>
              與 {sameCluster.length} 位成員的整體行為模式最接近。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- 圖表 ---------- */
function ChartsView({ mobile, onOpenMember }) {
  const D = window.APP_DATA;
  const barRows = [...D.members].sort((a, b) => b.f.message_count - a.f.message_count)
    .map((m) => ({ id: m.id, name: m.name, value: m.f.message_count, color: cvarOf(m.role) }));
  const donutData = Object.entries(D.roleDist).map(([role, v]) => ({ label: role, value: v, color: cvarOf(role) }));
  const [hover, setHover] = useState(null);

  return (
    <div className="view-enter">
      <SectionHead kicker="DATA ROOM · 視覺化" title="把整個群組攤開來看"
        note="四張互動圖表——點成員可跳到他的人物誌。" />

      <div style={{ display: "grid", gridTemplateColumns: mobile ? "1fr" : "1.15fr 1fr", gap: 18, marginBottom: 18 }}>
        <div className="panel">
          <div className="panel-head"><span className="panel-title">訊息量排行</span><span className="kicker">MESSAGES</span></div>
          <div className="panel-pad"><BarRanking rows={barRows} onPick={onOpenMember} /></div>
        </div>
        <div className="panel">
          <div className="panel-head"><span className="panel-title">角色分布</span><span className="kicker">ROLES</span></div>
          <div className="panel-pad" style={{ display: "grid", gridTemplateColumns: mobile ? "120px 1fr" : "180px 1fr", gap: 16, alignItems: "center" }}>
            <Donut data={donutData} size={mobile ? 120 : 180} thickness={mobile ? 18 : 26} onHover={setHover} />
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {donutData.map((d) => (
                <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 9, padding: "2px 0",
                  opacity: hover && hover.label !== d.label ? 0.4 : 1, transition: "opacity .15s" }}>
                  <span style={{ width: 9, height: 9, background: d.color, borderRadius: 2 }} />
                  <span style={{ fontSize: 12.5, flex: 1 }}>{d.label}</span>
                  <span className="mono" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="panel-head"><span className="panel-title">活躍時段</span><span className="kicker">24H ACTIVITY</span></div>
        <div className="panel-pad"><Heatmap data={D.heatmap} onPick={onOpenMember} mobile={mobile} dotted={mobile} /></div>
      </div>

      <div className="panel">
        <div className="panel-head"><span className="panel-title">行為分群</span><span className="kicker">PCA · K={D.clusterMeta.best_k} · 解釋變異 {Math.round((D.clusterMeta.explainedVariance || 0) * 100)}% · 輪廓係數 {D.clusterMeta.silhouette}</span></div>
        <div className="panel-pad" style={{ display: "grid", gridTemplateColumns: mobile ? "1fr" : "1fr 240px", gap: 24, alignItems: "center" }}>
          {mobile
            ? <ClusterCards meta={D.clusterMeta} scatter={D.scatter} members={D.members} onPick={onOpenMember} />
            : <Scatter points={D.scatter} members={D.members} meta={D.clusterMeta} onPick={onOpenMember} />}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ fontSize: 13.5, color: "var(--ink-2)", lineHeight: 1.55, margin: 0 }}>
              把每個人的特徵降到兩維後，演算法找出 {D.clusterMeta.best_k} 個自然分組：
            </p>
            {D.clusterMeta.clusters.map((c) => (
              <div key={c.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 11, height: 11, borderRadius: 2, background: `var(${c.cvar})`, flex: "0 0 auto" }} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{c.name}</div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
                    {D.scatter.filter((p) => p.c === c.id).map((p) => D.members.find((m) => m.id === p.id).name).join("、")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { MembersView, DetailView, ChartsView, FeatureRow });
