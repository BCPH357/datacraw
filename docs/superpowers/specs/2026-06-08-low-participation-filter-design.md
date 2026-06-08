# 低度參與成員過濾 + Token 顯示 — 設計文件

- 日期：2026-06-08
- 分支：`feature/ai-cluster-role-naming`
- 狀態：設計已核准，待實作

## 背景與問題

新加入的 AI 分析功能會把「短暫加入群組、只發言幾次就退出」的成員一併納入分群計算。
這類成員的行為特徵多為雜訊（例如 2 則訊息全是貼圖 → 貼圖比例 100%），會嚴重扭曲分群結果。

需要區分兩種低度參與：

1. **短暫加入又退出**（雜訊）：在幾萬則訊息的群組裡只發了不到十則 → 應排除於計算之外。
2. **真正的潛水員**：發言不多但仍屬於群組成員 → 應保留並正常分群。

門檻的職責是清掉第 1 類，不動第 2 類。

## 核心決策（已與使用者確認）

- **過濾規則**：發言數佔群組總訊息量 **≤ 門檻%（預設 1%）** 的成員，排除於分群計算之外。
  - `share = 成員 message_count / 全員 message_count 總和`
  - 門檻 = `min_share_pct / 100`；`share <= 門檻` 即排除。
- **可設定**：上傳頁新增一個百分比輸入框，使用者可改門檻；填 `0` 等於不過濾。
- **套用範圍**：規則角色（`rule`）與 AI 分群（`ai_cluster`）兩種模式都過濾。
- **被排除者**：報告中另開「未列入分析」區塊，列出名字、發言數、佔比。
- **Token**：AI 模式下顯示總 token 數（input / output / total）。

## 資料流

過濾只在 pipeline 層做一次，因為要算「佔總訊息量」需要全員資料，且報告需顯示被排除者。

```
parse → extract_features(全員，含 message_count)
      → _split_by_participation(features, min_share_pct)
            included = share > 門檻  → 進入 cluster_users
            excluded = share ≤ 門檻  → 只留 name / message_count / share，供報告顯示
      → cluster_users(included) → roles / AI 解釋（只算 included）
      → build_app_data(..., excluded_members, token_usage)
```

## 各檔案改動

| 檔案 | 改動 |
|---|---|
| `src/pipeline.py` | `analyze_text` 新增 `min_share_pct: float = 1.0` 參數；新增 `_split_by_participation()` 切出 included / excluded；只把 included 丟進 clustering 與後續 roles / AI 解釋。AI 模式取回 token usage 並往下傳。 |
| `src/cluster_interpreter.py` | `interpret_clusters_with_openai` 回傳型別由 `list` 改為 tuple `(interpretations: list, usage: dict)`，`usage` 從 `response.usage` 取 `input_tokens` / `output_tokens` / `total_tokens`（缺欄位時各以 0 容錯）。pipeline 端解構使用。 |
| `src/webreport.py` | `build_app_data` 新增 `excluded_members`、`token_usage`、`exclude_threshold_pct` 參數 → 輸出 `app_data["excludedMembers"]`、`app_data["tokenUsage"]`、`app_data["excludeThresholdPct"]`。`_empty_app_data` 也補上對應預設值。 |
| `app/server.py` | `/analyze`、`/sample` 讀 `min_share_pct` 表單 / query 參數（預設 `"1"`），解析為 float 後傳入 `pipeline.analyze_text`。 |
| `app/app.jsx` | 新增 `excludeThreshold` state（預設 `"1"`）；`analyze` 的表單與 query 帶 `min_share_pct`；傳遞 state 給 `UploadView`。 |
| `app/views.jsx` | `UploadView` 加百分比輸入框（label：排除低度參與門檻，佔總訊息 % 以下）；`OverviewView`（或 `AIClusterInterpretations` 附近）加「未列入分析」區塊與 token 顯示。 |

## 資料結構

`app_data` 新增欄位：

```js
excludedMembers: [
  { name: "小明", messageCount: 4, sharePct: 0.03 },  // sharePct 為百分比數值
  ...
]
excludeThresholdPct: 1.0
tokenUsage: { input: 1234, output: 567, total: 1801 } | null  // 非 AI 模式為 null
```

## 邊界處理

- **過濾後剩 < 2 人**：無法分群 → 丟出友善 `ValueError`「排除門檻過高，剩餘可分析成員不足，請調低門檻」，讓使用者調整。
- **門檻 = 0**：不過濾，`excludedMembers` 為空陣列，前端區塊不顯示。
- **`min_share_pct` 非法輸入**（負數 / 非數字）：後端視為 0（不過濾）或丟出友善錯誤；以 `0` 容錯為主。
- **潛水員**：佔比高於門檻的低發言者仍正常進入分群，門檻只清掉「短暫加入又退出」的雜訊。
- **空 `excludedMembers`**：前端不渲染「未列入分析」區塊。
- **`tokenUsage` 為 null**：前端不渲染 token 區塊。

## 測試策略（TDD）

先寫測試再實作：

- `_split_by_participation`：
  - 高佔比成員全部保留、低佔比成員被排除。
  - 門檻 = 0 時不排除任何人。
  - 邊界：`share == 門檻` 視為排除（「以下」含邊界）。
  - 過濾後剩 < 2 人時 `analyze_text` 丟出友善錯誤。
- token usage 擷取：mock OpenAI 回應的 `usage`，驗證回傳結構正確；無 usage 欄位時容錯。
- `build_app_data`：驗證 `excludedMembers` / `tokenUsage` / `excludeThresholdPct` 正確帶出；空值情境。
- `pipeline.analyze_text`：兩種模式都會過濾；被排除者不出現在 `members`，出現在 `excludedMembers`。

## 已考慮但未採用

- **在 `extract_features` 階段就丟掉低發言者**：不可行，因為要算「佔總訊息量」需要全員資料，且報告要顯示被排除者。pipeline 層切分最乾淨，且讓 features 維持單一職責（只抽特徵，不做政策過濾）。
