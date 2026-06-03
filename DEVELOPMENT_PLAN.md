# LINE Chat Persona Analyzer — 開發計畫（給 Claude Code 的實作指令）

> **閱讀對象：Claude Code**
> 本文件是逐步實作指令。請**嚴格依照階段順序**執行：每個階段都有「驗收標準」，
> **必須全部通過後，才能進入下一階段**。每通過一個階段，依指定方式 **git commit / tag**。
> 任何驗收項目失敗時，**停下來修正，不要往下做**。
>
> 功能需求來源：`LINE_Chat_Persona_Analyzer_開發功能規格.md`
> 真實資料樣本：`_LINE__MIAT_2025的聊天.txt`（群組 `MIAT_2025`，7 位成員，2025/09/01–2026/06/03）

---

## ⚠️ 開工前必讀：三個關鍵事實（會影響整體設計）

實作者過去常在這三點踩雷，請先記住：

### 事實 1 — 真實的 LINE 匯出格式與規格書的範例**不一樣**
規格書 §2 的範例是 `14:03 陳品豪 今天晚上要開會嗎`（空白分隔、24 小時制）。
**真實檔案不是這樣。** 真實格式是 **Tab 分隔、中文 12 小時制**，而且有多種特例（見 Phase 1）。
**Parser 必須以真實格式為準，規格書的範例僅供理解概念，不可照抄。**

### 事實 2 — 這個群組只有 7 位成員（小樣本）
分群（KMeans）只有 **7 個樣本點**。這在統計上非常少。因此：
- K 的搜尋範圍限制在 `2 ≤ K ≤ 4`（不可超過 `n_users - 1`）。
- Silhouette Score 在小樣本下波動大，需固定 `random_state`，結果僅作「展示性分群」，
  報告中要誠實說明樣本數限制，不可宣稱統計顯著。
- UMAP 在 7 點下幾乎無意義 → 列為選配，預設用 PCA。

### 事實 3 — 原始聊天檔含敏感資訊，且中文繪圖會踩字型雷
- 檔案內含**共用帳號/密碼**與個人連結等 PII。
  → **原始 `.txt` 與所有分析輸出一律不可進入 git 版控、不可上傳遠端。**（`.gitignore` 處理，見 Phase 0）
- matplotlib 預設無中文字型，中文會變成方框「□□□」。
  → 必須在繪圖前設定 CJK 字型（見 Phase 6），否則所有圖表驗收失敗。

---

## 技術選型（固定，不要自行更換）

| 項目 | 選擇 | 理由 |
|---|---|---|
| 語言 | Python 3.11+ | 規格書 §11 第一階段即指定 Python |
| 資料處理 | pandas, numpy | 標準 |
| 分群 | scikit-learn（StandardScaler / KMeans / silhouette / PCA） | 規格書 §4 指定 |
| 中文斷詞 | jieba（繁中） | 語言特徵需要 |
| 繪圖 | matplotlib（+ 指定 CJK 字型） | 產生靜態圖表 |
| 網絡特徵（進階） | networkx | 規格書 §3E |
| Web UI | **Streamlit** | 課程 demo 最務實：單檔可跑、可上傳、可下載報告 |
| 測試 | pytest | 驗收自動化 |

**核心分析邏輯必須與 UI 解耦**：所有解析/特徵/分群/命名/報告寫成可被 import 的純函式模組，
Streamlit 只負責呼叫與顯示。這樣 CLI 與 Web 共用同一套核心。

---

## Git 工作流程（每階段共用，務必遵守）

```bash
# 一次性：初始化（Phase 0 內做）
git init
git add .
git commit -m "chore: phase0 scaffolding"
git branch dev
git checkout dev

# 每個 Phase N 的流程：
git checkout dev
git checkout -b feature/phaseN-<簡短名稱>     # 例：feature/phase1-parser
# ... 實作 + 寫測試 ...
pytest tests/                                  # 跑驗收
# 全部通過後：
git checkout dev
git merge --no-ff feature/phaseN-<名稱>
git tag phase-N-done                           # 標記里程碑
git commit --allow-empty -m "milestone: phase N passed"  # 若 merge 已產生 commit 可省略
```

**規則：**
1. 每個 Phase 一條 `feature/*` 分支。
2. 驗收（`pytest`）**全綠**才能 merge 回 `dev`。
3. merge 後打 tag `phase-N-done`。
4. commit message 用 Conventional Commits（`feat:` / `fix:` / `test:` / `chore:` / `docs:`）。
5. **絕不 commit** `data/raw/`、`outputs/`、`*.txt` 原始聊天檔（由 `.gitignore` 保證）。

---

## 專案目錄結構（Phase 0 建立）

```text
line-persona-analyzer/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/                  # 放原始 .txt（被 gitignore）
│   └── fixtures/             # 測試用小樣本（可進版控，需去識別化）
├── src/
│   ├── __init__.py
│   ├── parser.py            # Phase 1
│   ├── features.py          # Phase 2
│   ├── clustering.py        # Phase 3
│   ├── roles.py             # Phase 4
│   ├── report.py            # Phase 5
│   ├── viz.py               # Phase 6
│   └── cli.py               # 串接 1→5 的命令列入口
├── app/
│   └── streamlit_app.py     # Phase 7
├── outputs/                  # 圖表/報告輸出（被 gitignore）
└── tests/
    ├── test_parser.py
    ├── test_features.py
    ├── test_clustering.py
    ├── test_roles.py
    └── fixtures/
        └── sample_chat.txt   # 人工構造的小樣本（涵蓋所有特例）
```

---

# Phase 0 — 專案骨架與環境

**目標：** 可安裝、可匯入、git 就緒，且確保敏感資料不會被版控。

### 工作項目
1. 建立上方目錄結構與空模組檔（每個 `.py` 先放 `def placeholder(): ...` 或 module docstring）。
2. `requirements.txt`：
   ```
   pandas
   numpy
   scikit-learn
   jieba
   matplotlib
   networkx
   streamlit
   pytest
   ```
3. `.gitignore`（**關鍵**，至少包含）：
   ```
   data/raw/
   outputs/
   *.txt
   !data/fixtures/*.txt
   !tests/fixtures/*.txt
   __pycache__/
   .venv/
   *.pyc
   ```
4. 將使用者提供的 `_LINE__MIAT_2025的聊天.txt` 複製到 `data/raw/`（**不進版控**）。
5. `README.md`：寫專案簡介、安裝步驟、執行方式（先寫骨架，後續補）。
6. 建立虛擬環境並安裝；確認可 `import src`。
7. 依「Git 工作流程」做 `git init` 與首次 commit，建立並切到 `dev`。

### ✅ 驗收標準（全部通過才進 Phase 1）
- [ ] `pip install -r requirements.txt` 無錯誤完成。
- [ ] `python -c "import src.parser, src.features, src.clustering, src.roles, src.report, src.viz"` 不報錯。
- [ ] `git status` 顯示 **clean**，且 `git check-ignore data/raw/_LINE__MIAT_2025的聊天.txt` **有輸出**（證明原始資料被忽略）。
- [ ] `git log --oneline` 至少一筆 commit；`git branch` 顯示 `main`/`master` 與 `dev`。

---

# Phase 1 — 解析器（Parser）★最重要★

**目標：** 把真實 `.txt` 解析成結構化記錄。此階段做不對，後面全錯。

### 真實格式規格（以此為準，務必逐條實作）

**檔頭（前兩行 + 空行，需略過）：**
```
[LINE] MIAT_2025的聊天記錄
儲存日期： 2026/06/03 15:58
<空行>
```

**日期分隔行**（設定「目前日期」上下文）：
```
2025/09/01（一）
```
- 格式：`YYYY/MM/DD（週幾）`，週幾為中文（一二三四五六日）。

**一般訊息行**（Tab 分隔，3 欄）：
```
時間<TAB>發話者<TAB>訊息內容
```
- 例：`下午05:20<TAB>豪<TAB>[貼圖]`
- **時間是中文 12 小時制**：`上午HH:MM` 或 `下午HH:MM`。轉 24 小時規則：
  | 原始 | 轉換後 |
  |---|---|
  | `上午12:MM` | `00:MM`（午夜） |
  | `上午01–11` | 不變 |
  | `下午12:MM` | `12:MM`（中午） |
  | `下午01–11` | 小時 +12 |
  （真實檔案 `上午12` 與 `下午12` **都存在**，務必測這兩個邊界。）
- **發話者可含空白**（例：`段 Duan`）。切欄時請以「第一個 Tab」「第二個 Tab」定位，
  訊息內容（第 3 欄之後）若含 Tab 要 rejoin，不可用 `split('\t')` 後只取 `[2]`。

**系統訊息行**（**雙 Tab**，發話者欄為空）：
```
時間<TAB><TAB>內容
```
辨識方式：時間後緊接兩個 Tab。內容型態：
- `⁨⁨X⁩⁩已新增⁨⁨Y⁩⁩至群組。` → 加入群組
- `⁨⁨X⁩⁩已退出群組。` → 離開群組
- `您已收回訊息` / `{name}已收回訊息` → 收回訊息（unsent）

**Bidi 隔離字元**：系統訊息中的人名被 `U+2068`（⁨）與 `U+2069`（⁩）包住，
解析時**必須移除這兩個字元**（可一併移除 `U+200E/U+200F/U+202A-202E/U+2066-2069` 等方向控制字元）。

**多行訊息**（重要）：一則訊息的內容可能跨多個實體行（內含換行）。
真實例子：foodpanda 團購訊息、一段 Google 帳號/密碼、一份考題清單。
**判定規則：** 凡是「不符合日期行、也不符合 `^(上午|下午)HH:MM<TAB>` 開頭」的非空行，
視為**上一則訊息的續行**，以換行接在上一則內容之後（**不可當成新訊息**）。

**媒體型態對應**（依訊息內容的方括號標記分類 `type`）：
| 標記 | type |
|---|---|
| `[貼圖]` | sticker |
| `[照片]` | image |
| `[影片]` | video |
| `[檔案]` | file |
| `[記事本]` | note |
| 其他純 `[xxx]` | media（保留原標記） |
| 含實際文字 | text |
| 含 `http(s)://` | 額外標記 `has_url=True` |

### 輸出資料結構
每則訊息一個 dict（或 DataFrame 一列）：
```python
{
  "date": "2025-09-02",      # ISO，由日期行 + 時間決定
  "time": "10:06",           # 已轉 24h
  "datetime": "2025-09-02T10:06:00",
  "user": "林可姍",          # 系統訊息為 None 或 "SYSTEM"
  "message": "學長說今天沒有meeting",
  "type": "text",            # text / sticker / image / video / file / note / media / system
  "is_system": False,
  "has_url": False
}
```
另提供 `summarize(records) -> dict`，回傳規格書 §1 的摘要：
```json
{ "group_name": "MIAT_2025", "message_count": ..., "user_count": 7,
  "date_range": {"start": "2025-09-01", "end": "2026-06-03"} }
```
（`message_count` 定義：使用者訊息數，**不含**系統訊息；請在 README 註明此定義。）

### 測試夾具
在 `tests/fixtures/sample_chat.txt` 人工構造一個小檔，**至少涵蓋**：
正常文字、`段 Duan` 這種含空白的發話者、`上午12`/`下午12` 邊界、各種媒體標記、
雙 Tab 系統訊息（加入/退出/收回）、含 bidi 字元的人名、一則跨兩行的多行訊息、含 URL 的訊息。

### ✅ 驗收標準
針對 `tests/fixtures/sample_chat.txt`（單元測試，精確值由你構造的夾具決定）：
- [ ] `上午12:30` → `00:30`；`下午12:30` → `12:30`；`下午01:00` → `13:00`。
- [ ] `段 Duan` 被正確當成單一發話者（名字不被截斷、不被當系統訊息）。
- [ ] 雙 Tab 行 `is_system=True`、`user` 非真實成員；bidi 字元已被清除。
- [ ] 跨兩行的多行訊息合併成**一則**記錄，內含換行。
- [ ] 各媒體標記對應到正確 `type`；含 URL 的訊息 `has_url=True`。

針對真實檔 `data/raw/_LINE__MIAT_2025的聊天.txt`（整合測試，硬性參考值）：
- [ ] `user_count == 7`，且使用者集合恰為：`{Young, 段 Duan, 黃木龍生, 豪, 黃偉哲, 妤, 林可姍}`。
- [ ] `date_range == {start: 2025-09-01, end: 2026-06-03}`。
- [ ] 媒體計數：`sticker==105`、`image==62`、`file==11`、`note==2`、`video==1`。
- [ ] 各使用者一般訊息數（起始於行首的記錄）：
      `Young 352、段 Duan 244、黃木龍生 234、豪 142、黃偉哲 128、妤 25、林可姍 18`。
      （若你的多行合併把續行併入，這些數字應**等於或略小於**上述physical值；
       測試請斷言「使用者訊息總數 ≤ 1143 且每人 ≥ 1」，並把 7 人集合與媒體計數設為硬條件。）
- [ ] 系統訊息（雙 Tab）共 15 則，含「加入/退出/收回」三類皆有被分類到。

---

# Phase 2 — 特徵抽取（Feature Extraction）

**目標：** 每位使用者一列數值特徵向量，供分群使用。先做 MVP 的 15–20 個特徵。

### MVP 特徵清單（必做，依規格書 §3）
- **時間（A）**：`message_count`, `active_days`, `avg_messages_per_day`,
  `night_ratio`(00–06), `morning_ratio`(06–12), `afternoon_ratio`(12–18), `evening_ratio`(18–24)
- **內容（B）**：`avg_message_length`, `median_message_length`, `text_ratio`,
  `sticker_ratio`, `image_ratio`, `url_ratio`, `emoji_ratio`
- **互動（C）**：`reply_like_ratio`（接在他人訊息後發言比例）, `topic_start_count`
  （與前一則間隔 > 門檻，預設 30 分鐘，視為開新話題）, `avg_response_time_min`
- **語言（D）**：`question_ratio`（含 `？`/`?`/`嗎`/`呢`/疑問詞）, `unique_word_ratio`（jieba 斷詞後）

> 進階特徵（C 的 `silence_gap_avg`、D 的 `sentiment_score`、E 網絡特徵）留待 Phase 8。

### 實作要點
- 統計**只計使用者訊息**（`is_system==False`）。
- 長度用「字元數」（中文）；`text_ratio` 等比例的分母是該使用者總訊息數。
- emoji 偵測用 Unicode emoji 範圍；URL 用 `has_url`。
- 時段比例（4 個 ratio）**每位使用者應相加 ≈ 1.0**。
- jieba 首次載入較慢可接受；繁中可載入 `jieba.set_dictionary` 或用預設。
- 輸出 `outputs/features.csv`（index = user）。

### ✅ 驗收標準
- [ ] 特徵表列數 == 使用者數（7），每位皆有值，**無 NaN**（無資料時補 0 並註明）。
- [ ] 所有 `*_ratio` 欄位值域在 `[0, 1]`；所有 `*_count` ≥ 0。
- [ ] 每位使用者 `night+morning+afternoon+evening` 四個 ratio 相加在 `1.0 ± 0.001`。
- [ ] `pytest tests/test_features.py` 全綠（在 fixtures 上驗算手算可得的小例子）。
- [ ] `outputs/features.csv` 成功產生且可被 pandas 讀回。

---

# Phase 3 — 分群（Clustering）

**目標：** 標準化 → KMeans → 自動選 K → 產生 cluster label。

### 實作要點（**注意 7 樣本限制**）
- 流程：`StandardScaler.fit_transform(X)` → 對 `K in range(2, 5)` 跑 `KMeans(random_state=42, n_init=10)`。
- 用 `silhouette_score` 選最佳 K；**K 上限 = min(4, n_users - 1)**。
- 輸出每位使用者 `cluster` label，存 `outputs/clusters.csv`，並保存 scaler 與最佳 K、各 K 的 silhouette 分數。
- 因樣本極少：固定 `random_state`，確保結果可重現；在輸出中附上「樣本數 = 7，分群僅供展示」字串。

### ✅ 驗收標準
- [ ] 對全部 7 位使用者都產生整數 `cluster` label，無遺漏。
- [ ] 回傳物件含：`best_k`（2≤best_k≤4）、`silhouette_scores`（每個 K 一個分數）。
- [ ] 重跑兩次結果**完全一致**（random_state 生效，可重現）。
- [ ] `K` 不會超過 `n_users - 1`（用一個 3-樣本的 fixture 測邊界，不該崩潰）。
- [ ] `pytest tests/test_clustering.py` 全綠。

---

# Phase 4 — 角色命名（Role Assignment）

**目標：** 依每個 cluster 的突出特徵自動命名角色。

### 實作要點（依規格書 §5）
1. 計算每群平均特徵 − 全體平均特徵（z-score 後的偏差），取每群 top 3–5 突出特徵。
2. Rule-based 命名（門檻用「全體分位數」如上四分位，避免寫死絕對值）：
   - `night_ratio` 高 且 `avg_message_length` 高 → 午夜哲學家
   - `sticker_ratio` 或 `emoji_ratio` 高 → 氣氛組
   - `image_ratio` 高 且 `text_ratio` 低 → 長輩圖專員
   - `message_count` 低（下四分位）→ 潛水艇
   - `topic_start_count` 高 → 話題發起人
   - `avg_message_length` 高 且 `reply_like_ratio` 高 → 深度回應者
   - `url_ratio` 高 → 資訊分享者
   - 皆不符 → 以最突出特徵給通用名（如「核心活躍者」）
3. 每群輸出：`role_name`、`top_features`（list）、`description`（中文一句話）。
4. 名稱衝突處理：兩群命中同名時，以第二突出特徵或後綴區分。

### ✅ 驗收標準
- [ ] 每個 cluster 都有 `role_name`、`top_features`（長度 3–5）、`description`。
- [ ] 命名為**確定性**（同輸入同輸出，可重現）。
- [ ] 門檻用分位數計算，不得出現寫死的魔術數字（code review 檢查）。
- [ ] `pytest tests/test_roles.py` 全綠（用構造的極端 cluster 驗證每條規則都打得到）。

---

# Phase 5 — 個人角色卡 + 群組健康報告（資料層）

**目標：** 產生規格書 §6、§7 的 JSON（先做資料，圖在 Phase 6）。

### 實作要點
- **個人角色卡**（每位使用者一張，依 §6 schema）：`user`, `role`, `description`,
  `top_features`（含實際數值）, `rankings`（該使用者在各關鍵特徵的群內排名）。
- **群組健康報告**（依 §7）：`group_health_score`(0–100), `summary`(中文),
  `role_distribution`(各角色人數), `warnings`(list)。
  指標範例：`ghost_ratio`（潛水艇比例）、`dependency_score`（發言是否集中少數人，用前 1–2 名發言佔比）、
  `diversity_score`（角色種類數 / 群人數）。`health_score` 用上述指標加權合成（權重寫在 config，附註說明）。
- 全部輸出為 `outputs/personas.json` 與 `outputs/group_health.json`。
- **誠實性要求**：summary 不可誇大；因 n=7，warnings 內若觸發須加註「樣本數小，僅供參考」。

### ✅ 驗收標準
- [ ] `personas.json` 為長度 7 的陣列，每張卡欄位齊全且 `top_features` 數值與 `features.csv` 一致。
- [ ] `rankings` 排名正確（針對某特徵手動驗證 top 1 確實是該特徵最高者）。
- [ ] `group_health.json` 的 `role_distribution` 人數總和 == 7。
- [ ] `group_health_score` 落在 `[0, 100]`。
- [ ] 兩個 JSON 皆可被 `json.load` 成功解析（schema 驗證測試通過）。

---

# Phase 6 — 視覺化（MVP 四張圖 + 角色卡圖）

**目標：** 規格書 §8 最小可行四圖：發言量 bar、時段 heatmap、分群 scatter、角色分布 pie。

### ⚠️ 中文字型（必處理，否則全部驗收失敗）
繪圖前先設定 CJK 字型，例如：
```python
import matplotlib
from matplotlib import font_manager
# 優先嘗試系統可用的 CJK 字型；找不到就退而提示安裝
for f in ["Noto Sans CJK TC", "Microsoft JhengHei", "PingFang TC", "Heiti TC", "WenQuanYi Zen Hei"]:
    if any(f in fp.name for fp in font_manager.fontManager.ttflist):
        matplotlib.rcParams["font.family"] = f
        break
matplotlib.rcParams["axes.unicode_minus"] = False
```
若環境無任何 CJK 字型，README 須註明安裝方式（如 `apt install fonts-noto-cjk`）。

### 圖表清單
1. `bar_message_count.png` — 各使用者發言量長條圖。
2. `heatmap_active_hours.png` — 使用者 × 24 小時 的發言熱力圖。
3. `scatter_clusters.png` — PCA 降到 2D 的分群散布圖（點上標使用者名與顏色分群）。
4. `pie_role_distribution.png` — 角色分布圓餅圖。
5. （加分）每位使用者一張角色卡圖（雷達圖 + 文字），輸出到 `outputs/cards/`。

### ✅ 驗收標準
- [ ] 四張 PNG 全部成功產生於 `outputs/`，檔案大小 > 0。
- [ ] **目視檢查：中文標籤正常顯示，無方框 □**（在 README 記錄一次目視結果或附縮圖）。
- [ ] scatter 圖點數 == 7，顏色數 == best_k。
- [ ] 繪圖函式在無顯示環境可跑（使用 `matplotlib.use("Agg")`）。

---

# Phase 7 — Web UI（Streamlit，串成產品）

**目標：** Upload → Analyze → Dashboard → Download，呼叫前面所有核心模組。

### 實作要點
- `app/streamlit_app.py`：上傳 `.txt` → 呼叫 `parser → features → clustering → roles → report → viz`。
- 畫面：摘要卡（群名/訊息數/人數/日期範圍）、四張圖、個人角色卡、群組健康分數。
- 提供「下載報告」按鈕（彙整 JSON + 圖打包，或產生單一 HTML/PDF 報告）。
- **不重寫邏輯**：UI 只組裝核心模組的輸出。
- 上傳檔僅存在記憶體/暫存，**不寫進 repo**。

### ✅ 驗收標準
- [ ] `streamlit run app/streamlit_app.py` 可啟動，無 import 錯誤。
- [ ] 上傳真實樣本檔後，完整跑完且頁面顯示：摘要、四圖、7 張角色卡、健康分數。
- [ ] 「下載報告」可下載且內容非空。
- [ ] 上傳格式錯誤的檔案時，顯示友善錯誤訊息（不 crash）。

---

# Phase 8 — 進階功能（有時間再做，依規格書 §9 進階版）

每項仍**獨立分支、獨立驗收、通過才 merge**。建議優先序：

| 子項 | 內容 | 最低驗收 |
|---|---|---|
| 8a 網絡特徵 | networkx：degree/betweenness centrality、mention/被回應次數 | 產生有向互動圖，centrality 值合理（核心人物分數最高） |
| 8b 群組健康強化 | 補 `response_balance`、`initiator_ratio` 等指標 | 指標值域正確、寫入 health.json |
| 8c UMAP 比較 | 與 PCA 並列（註明 7 點下意義有限） | scatter 能畫出，且 README 說明限制 |
| 8d Hierarchical 比較 | 與 KMeans 分群結果比對 | 輸出兩法的 cluster 對照表 |
| 8e 情緒分析 | 簡易中文情緒分數（詞典法即可） | sentiment_score 落在 [-1,1]，併入特徵表 |

---

## 全案完成定義（Definition of Done）

- [ ] Phase 0–7 全部 `phase-N-done` tag 存在。
- [ ] `pytest tests/ -v` 全綠。
- [ ] 對真實檔可一鍵跑完 `python -m src.cli data/raw/_LINE__MIAT_2025的聊天.txt`，
      產生 features.csv / clusters.csv / personas.json / group_health.json / 四張圖。
- [ ] Streamlit app 可上傳同檔得到一致結果。
- [ ] `git log` 顯示清楚的分階段歷史；原始資料與 outputs **從未進入版控**（`git log --all -- data/raw/` 為空）。
- [ ] README 完整：安裝、CJK 字型、執行、各模組說明、**樣本數=7 的限制聲明**、資料隱私聲明。

---

## 附錄：真實檔解析速查表（給 Parser 對照用）

```text
行類型判斷優先序（由上而下）：
1. 第 1 行 "[LINE] ...的聊天記錄"          → 取群名，跳過
2. "儲存日期：..."                          → 跳過
3. 空白行                                   → 跳過
4. ^YYYY/MM/DD（週）                        → 更新目前日期
5. ^(上午|下午)HH:MM\t\t<內容>              → 系統訊息（is_system=True）
6. ^(上午|下午)HH:MM\t<發話者>\t<訊息>      → 一般訊息
7. 其他非空行                               → 上一則訊息的續行（多行訊息）

需清除的方向控制字元：U+2066–U+2069, U+202A–U+202E, U+200E, U+200F
時間轉換：上午12→00 / 下午12→12 / 下午01-11→+12 / 其餘不變
發話者可含空白（例「段 Duan」）→ 以 Tab 定位，勿用空白切
```
