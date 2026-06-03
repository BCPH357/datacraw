/* =========================================================
   假資料 — 「永康街吃貨團 🍜」9 位成員
   全部為虛構，繁體中文友群情境
   ========================================================= */
(function () {
  // 角色定義（取自 roles.py，含稱號 / 印章字 / 色彩）
  const ROLES = {
    "高頻核心型": { glyph: "核", title: "群組引擎",   cvar: "--r-core",   soft: "--r-core-soft",   desc: "互動量和活躍天數都偏高，是群組討論的主要推進者。" },
    "話題啟動型": { glyph: "啟", title: "開場王",     cvar: "--r-topic",  soft: "--r-topic-soft",  desc: "常開啟新話題或提出問題，會把對話往下一段推進。" },
    "表情回應型": { glyph: "情", title: "氣氛組組長", cvar: "--r-emoji",  soft: "--r-emoji-soft",  desc: "常用貼圖或表情快速互動，讓群組氣氛保持輕鬆。" },
    "圖像分享型": { glyph: "像", title: "現場直擊者", cvar: "--r-image",  soft: "--r-image-soft",  desc: "偏好用圖片或媒體補充資訊，圖像型互動較明顯。" },
    "資訊轉譯型": { glyph: "訊", title: "情報販子",   cvar: "--r-info",   soft: "--r-info-soft",   desc: "常分享連結或資訊，詞彙變化也比較高。" },
    "夜間長文型": { glyph: "夜", title: "深夜哲學家", cvar: "--r-night",  soft: "--r-night-soft",  desc: "常在夜間出現，訊息也比較完整，適合承接需要脈絡的討論。" },
    "思考回覆型": { glyph: "思", title: "群組軍師",   cvar: "--r-think",  soft: "--r-think-soft",  desc: "回覆比例高且內容較完整，常扮演整理與補充的角色。" },
    "穩定參與型": { glyph: "穩", title: "定海神針",   cvar: "--r-stable", soft: "--r-stable-soft", desc: "各項互動特徵相對平均，是群組中的穩定參與者。" },
  };

  // 六維雷達軸
  const AXES = ["活躍", "開話題", "表情", "影像", "夜貓", "回應"];

  // 特徵中文標籤 + 格式
  const FEATURES = {
    message_count:        { label: "訊息總數",     fmt: "int" },
    active_days:          { label: "活躍天數",     fmt: "int", unit: "天" },
    avg_messages_per_day: { label: "每日平均訊息", fmt: "f1" },
    night_ratio:          { label: "夜間比例",     fmt: "pct" },
    morning_ratio:        { label: "早晨比例",     fmt: "pct" },
    afternoon_ratio:      { label: "午後比例",     fmt: "pct" },
    evening_ratio:        { label: "傍晚比例",     fmt: "pct" },
    avg_message_length:   { label: "平均訊息長度", fmt: "f0", unit: "字" },
    median_message_length:{ label: "長度中位數",   fmt: "f0", unit: "字" },
    text_ratio:           { label: "純文字比例",   fmt: "pct" },
    sticker_ratio:        { label: "貼圖比例",     fmt: "pct" },
    image_ratio:          { label: "圖片比例",     fmt: "pct" },
    url_ratio:            { label: "連結比例",     fmt: "pct" },
    emoji_ratio:          { label: "emoji 比例",   fmt: "pct" },
    reply_like_ratio:     { label: "回覆率",       fmt: "pct" },
    topic_start_count:    { label: "開啟話題數",   fmt: "int", unit: "次" },
    avg_response_time_min:{ label: "平均回覆時間", fmt: "f1", unit: "分" },
    question_ratio:       { label: "提問率",       fmt: "pct" },
    unique_word_ratio:    { label: "詞彙多樣度",   fmt: "pct" },
  };

  const M = [
    { id: "ziry", name: "子睿", role: "高頻核心型", cluster: 0,
      tagline: "群組沒有他就安靜了。",
      stats: { 活躍: 95, 開話題: 70, 表情: 55, 影像: 40, 夜貓: 35, 回應: 72 },
      top: ["message_count", "active_days", "avg_messages_per_day"],
      f: { message_count:5840, active_days:392, avg_messages_per_day:14.9, night_ratio:.12, morning_ratio:.18, afternoon_ratio:.30, evening_ratio:.40, avg_message_length:24, median_message_length:18, text_ratio:.74, sticker_ratio:.14, image_ratio:.06, url_ratio:.06, emoji_ratio:.22, reply_like_ratio:.58, topic_start_count:142, avg_response_time_min:8.2, question_ratio:.18, unique_word_ratio:.42 } },

    { id: "ache", name: "阿哲", role: "話題啟動型", cluster: 1,
      tagline: "「欸欸我跟你們說」本人。",
      stats: { 活躍: 68, 開話題: 96, 表情: 50, 影像: 45, 夜貓: 30, 回應: 60 },
      top: ["topic_start_count", "question_ratio", "message_count"],
      f: { message_count:3210, active_days:280, avg_messages_per_day:11.5, night_ratio:.08, morning_ratio:.26, afternoon_ratio:.34, evening_ratio:.32, avg_message_length:21, median_message_length:15, text_ratio:.70, sticker_ratio:.12, image_ratio:.08, url_ratio:.10, emoji_ratio:.18, reply_like_ratio:.44, topic_start_count:188, avg_response_time_min:12.0, question_ratio:.58, unique_word_ratio:.50 } },

    { id: "mei", name: "小美", role: "表情回應型", cluster: 2,
      tagline: "貼圖庫存量驚人。",
      stats: { 活躍: 80, 開話題: 45, 表情: 97, 影像: 40, 夜貓: 42, 回應: 78 },
      top: ["sticker_ratio", "emoji_ratio", "reply_like_ratio"],
      f: { message_count:4120, active_days:350, avg_messages_per_day:11.8, night_ratio:.14, morning_ratio:.20, afternoon_ratio:.30, evening_ratio:.36, avg_message_length:11, median_message_length:7, text_ratio:.42, sticker_ratio:.44, image_ratio:.08, url_ratio:.03, emoji_ratio:.66, reply_like_ratio:.70, topic_start_count:60, avg_response_time_min:5.4, question_ratio:.22, unique_word_ratio:.30 } },

    { id: "vivi", name: "Vivi", role: "圖像分享型", cluster: 2,
      tagline: "現場照永遠第一手。",
      stats: { 活躍: 58, 開話題: 42, 表情: 48, 影像: 95, 夜貓: 28, 回應: 55 },
      top: ["image_ratio", "afternoon_ratio", "reply_like_ratio"],
      f: { message_count:2680, active_days:210, avg_messages_per_day:12.8, night_ratio:.07, morning_ratio:.22, afternoon_ratio:.40, evening_ratio:.31, avg_message_length:14, median_message_length:9, text_ratio:.40, sticker_ratio:.12, image_ratio:.42, url_ratio:.06, emoji_ratio:.24, reply_like_ratio:.48, topic_start_count:70, avg_response_time_min:10.0, question_ratio:.20, unique_word_ratio:.36 } },

    { id: "dawen", name: "大文", role: "資訊轉譯型", cluster: 1,
      tagline: "連結界的 RSS。",
      stats: { 活躍: 52, 開話題: 58, 表情: 35, 影像: 60, 夜貓: 40, 回應: 50 },
      top: ["url_ratio", "unique_word_ratio", "avg_message_length"],
      f: { message_count:2240, active_days:240, avg_messages_per_day:9.3, night_ratio:.12, morning_ratio:.28, afternoon_ratio:.32, evening_ratio:.28, avg_message_length:28, median_message_length:22, text_ratio:.66, sticker_ratio:.06, image_ratio:.12, url_ratio:.40, emoji_ratio:.14, reply_like_ratio:.42, topic_start_count:96, avg_response_time_min:14.0, question_ratio:.26, unique_word_ratio:.62 } },

    { id: "akai", name: "阿凱", role: "夜間長文型", cluster: 3,
      tagline: "凌晨兩點的小論文。",
      stats: { 活躍: 46, 開話題: 50, 表情: 30, 影像: 38, 夜貓: 96, 回應: 52 },
      top: ["night_ratio", "avg_message_length", "median_message_length"],
      f: { message_count:1980, active_days:190, avg_messages_per_day:10.4, night_ratio:.58, morning_ratio:.04, afternoon_ratio:.14, evening_ratio:.24, avg_message_length:46, median_message_length:38, text_ratio:.80, sticker_ratio:.05, image_ratio:.07, url_ratio:.12, emoji_ratio:.10, reply_like_ratio:.50, topic_start_count:80, avg_response_time_min:22.0, question_ratio:.30, unique_word_ratio:.58 } },

    { id: "yichen", name: "宜蓁", role: "思考回覆型", cluster: 3,
      tagline: "總是那個收尾的人。",
      stats: { 活躍: 66, 開話題: 55, 表情: 44, 影像: 40, 夜貓: 34, 回應: 94 },
      top: ["reply_like_ratio", "avg_response_time_min", "avg_message_length"],
      f: { message_count:2960, active_days:300, avg_messages_per_day:9.9, night_ratio:.16, morning_ratio:.22, afternoon_ratio:.30, evening_ratio:.32, avg_message_length:32, median_message_length:26, text_ratio:.78, sticker_ratio:.08, image_ratio:.06, url_ratio:.12, emoji_ratio:.16, reply_like_ratio:.88, topic_start_count:88, avg_response_time_min:6.0, question_ratio:.28, unique_word_ratio:.54 } },

    { id: "wang", name: "老王", role: "穩定參與型", cluster: 0,
      tagline: "永遠都在，剛剛好。",
      stats: { 活躍: 60, 開話題: 52, 表情: 55, 影像: 50, 夜貓: 40, 回應: 60 },
      top: ["text_ratio", "morning_ratio", "afternoon_ratio"],
      f: { message_count:2510, active_days:320, avg_messages_per_day:7.8, night_ratio:.15, morning_ratio:.25, afternoon_ratio:.30, evening_ratio:.30, avg_message_length:19, median_message_length:13, text_ratio:.62, sticker_ratio:.16, image_ratio:.10, url_ratio:.12, emoji_ratio:.20, reply_like_ratio:.54, topic_start_count:84, avg_response_time_min:11.0, question_ratio:.24, unique_word_ratio:.46 } },

    { id: "tingwei", name: "庭瑋", role: "穩定參與型", cluster: 0,
      tagline: "群組的背景音樂。",
      stats: { 活躍: 50, 開話題: 46, 表情: 52, 影像: 46, 夜貓: 36, 回應: 56 },
      top: ["text_ratio", "evening_ratio", "reply_like_ratio"],
      f: { message_count:1927, active_days:268, avg_messages_per_day:7.2, night_ratio:.13, morning_ratio:.24, afternoon_ratio:.32, evening_ratio:.31, avg_message_length:17, median_message_length:12, text_ratio:.60, sticker_ratio:.18, image_ratio:.11, url_ratio:.10, emoji_ratio:.22, reply_like_ratio:.52, topic_start_count:70, avg_response_time_min:12.0, question_ratio:.22, unique_word_ratio:.44 } },
  ];

  const totalMessages = M.reduce((s, m) => s + m.f.message_count, 0);

  // 角色分布
  const roleDist = {};
  M.forEach((m) => { roleDist[m.role] = (roleDist[m.role] || 0) + 1; });

  // 程序化時段熱力圖：每人 24 小時強度（依時段比例塑形）
  function hourCurve(m) {
    const seg = (h) => h < 6 ? "night" : h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
    const w = { night: m.f.night_ratio, morning: m.f.morning_ratio, afternoon: m.f.afternoon_ratio, evening: m.f.evening_ratio };
    const peak = { night: 1.5, morning: 9, afternoon: 14.5, evening: 21 };
    const out = [];
    for (let h = 0; h < 24; h++) {
      const s = seg(h);
      const base = w[s];
      const bump = Math.exp(-Math.pow((h - peak[s]) / 2.4, 2));
      out.push(base * (0.45 + 0.85 * bump));
    }
    const max = Math.max(...out) || 1;
    return out.map((v) => v / max);
  }
  const heatmap = M.map((m) => ({ id: m.id, name: m.name, role: m.role, hours: hourCurve(m) }));

  // 群組健康度
  const dependency = M[0].f.message_count / totalMessages;       // 0.213
  const diversity = Object.keys(roleDist).length / M.length;      // 8/9
  const ghost = 0;
  const health = +(100 * (0.45 * (1 - dependency) + 0.35 * diversity + 0.20 * (1 - ghost))).toFixed(1);

  // 超級之最（編輯式 highlight）
  const superlatives = [
    { key: "最活躍",   who: "子睿", role: "高頻核心型", val: "5,840", unit: "則訊息", note: "全群 21% 的訊息出自他手" },
    { key: "開場王",   who: "阿哲", role: "話題啟動型", val: "188",   unit: "次起頭", note: "幾乎每兩天就丟一個新話題" },
    { key: "貼圖王",   who: "小美", role: "表情回應型", val: "44%",   unit: "為貼圖", note: "純文字反而是少數" },
    { key: "深夜代表", who: "阿凱", role: "夜間長文型", val: "58%",   unit: "在午夜後", note: "平均每則 46 字的深夜長文" },
    { key: "群組軍師", who: "宜蓁", role: "思考回覆型", val: "88%",   unit: "為回覆", note: "話題收尾交給她準沒錯" },
    { key: "情報量",   who: "大文", role: "資訊轉譯型", val: "40%",   unit: "帶連結", note: "詞彙多樣度全群最高" },
  ];

  // 觀察重點（取代空的 warnings）
  const observations = [
    { tone: "good",  text: "沒有人扛超過一半的對話，發言分布相對平均。" },
    { tone: "good",  text: "8 種角色幾乎都齊了，群組互補性高。" },
    { tone: "watch", text: "白天的對話偏少，多數熱度集中在傍晚到深夜。" },
  ];

  // 分群（PCA 散佈座標，已正規化 0–1）
  const clusterMeta = {
    best_k: 4,
    silhouette: 0.54,
    clusters: [
      { id: 0, name: "核心穩定群", role: "高頻核心型", cvar: "--r-core" },
      { id: 1, name: "話題情報群", role: "話題啟動型", cvar: "--r-topic" },
      { id: 2, name: "視覺表情群", role: "表情回應型", cvar: "--r-emoji" },
      { id: 3, name: "深夜長文群", role: "夜間長文型", cvar: "--r-night" },
    ],
  };
  const scatter = [
    { id: "ziry",    x: 0.74, y: 0.34, c: 0 },
    { id: "wang",    x: 0.82, y: 0.50, c: 0 },
    { id: "tingwei", x: 0.70, y: 0.58, c: 0 },
    { id: "ache",    x: 0.30, y: 0.28, c: 1 },
    { id: "dawen",   x: 0.22, y: 0.46, c: 1 },
    { id: "mei",     x: 0.40, y: 0.78, c: 2 },
    { id: "vivi",    x: 0.26, y: 0.84, c: 2 },
    { id: "akai",    x: 0.78, y: 0.84, c: 3 },
    { id: "yichen",  x: 0.62, y: 0.74, c: 3 },
  ];

  window.APP_DATA = {
    group: {
      name: "永康街吃貨團",
      emoji: "🍜",
      range: "2024.03.18 — 2025.05.30",
      days: 438,
      messageCount: totalMessages,
      userCount: M.length,
      health, dependency, diversity, ghost,
    },
    members: M,
    ROLES, AXES, FEATURES,
    roleDist, superlatives, observations,
    heatmap, scatter, clusterMeta,
  };
})();
