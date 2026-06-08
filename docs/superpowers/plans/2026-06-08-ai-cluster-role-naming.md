# AI Cluster Role Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a selectable AI cluster naming mode that interprets KMeans clusters with OpenAI using statistical summaries only, while preserving the existing rule-based mode.

**Architecture:** Keep `roles.py` as the rule-based baseline. Add `src/cluster_interpreter.py` for cluster summaries, OpenAI structured output, and applying cluster interpretations to users. Thread `mode=rule|ai_cluster` from React upload controls through Flask into `pipeline.analyze_text`.

**Tech Stack:** Python, Flask, pandas, scikit-learn, pytest, React JSX, OpenAI Python SDK, OpenAI Responses API structured output.

---

## File Structure

- Create `src/cluster_interpreter.py`: cluster summary construction, OpenAI interpretation, applying AI roles to user rows.
- Modify `src/pipeline.py`: accept `mode`, route rule vs AI cluster mode, return `analysis_mode` and `cluster_interpretations`.
- Modify `app/server.py`: read `mode` from upload form and sample query string; return validation/API errors clearly.
- Modify `src/webreport.py`: include `analysisMode` and `clusterInterpretations`; support dynamic AI role styles.
- Modify `claude_design/app/app.jsx`: keep selected analysis mode in state; submit it with uploads/sample.
- Modify `claude_design/app/views.jsx`: upload mode segmented control, loading copy, overview AI cluster explanation block.
- Modify `claude_design/app/styles.css`: styling for mode selector and AI cluster cards.
- Modify `.gitignore`: ignore local `.env` secrets while allowing `.env.example`.
- Add `.env.example`: document `OPENAI_API_KEY` and `OPENAI_MODEL`.
- Modify `requirements.txt`: add `openai`.
- Add/modify tests in `tests/test_cluster_interpreter.py`, `tests/test_pipeline.py`, `tests/test_server.py`, and `tests/test_webreport.py`.

---

### Task 1: Cluster Interpreter Unit Tests

**Files:**
- Create: `tests/test_cluster_interpreter.py`
- Create later: `src/cluster_interpreter.py`

- [ ] **Step 1: Write failing tests**

Add tests that create the existing fixture feature frame and verify:

```python
from src import clustering, cluster_interpreter, features, parser


def _clustered_fixture():
    records = parser.to_dataframe(parser.parse_file("tests/fixtures/sample_chat.txt"))
    feature_frame = features.extract_features(records)
    clustered, metadata = clustering.cluster_users(feature_frame)
    return feature_frame, clustered, metadata


def test_cluster_summaries_do_not_include_raw_messages():
    feature_frame, clustered, _ = _clustered_fixture()
    summaries = cluster_interpreter.build_cluster_summaries(clustered, feature_frame)

    assert summaries
    for summary in summaries:
        assert "cluster" in summary
        assert "member_count" in summary
        assert "feature_means" in summary
        assert "top_high_features" in summary
        assert "top_low_features" in summary
        assert "messages" not in summary
        assert "raw_messages" not in summary
        assert "message_examples" not in summary
        assert "members" not in summary


def test_apply_cluster_interpretations_assigns_cluster_roles():
    _, clustered, _ = _clustered_fixture()
    cluster_ids = sorted(int(c) for c in clustered["cluster"].unique())
    interpretations = [
        {
            "cluster": cluster_id,
            "roleName": f"AI 角色 {cluster_id}",
            "tagline": f"摘要 {cluster_id}",
            "description": f"解釋 {cluster_id}",
            "evidence": ["訊息數高", "活躍天數高"],
        }
        for cluster_id in cluster_ids
    ]

    user_roles = cluster_interpreter.apply_cluster_interpretations(clustered, interpretations)

    assert len(user_roles) == len(clustered)
    for _, row in user_roles.iterrows():
        assert row["role_name"] == f"AI 角色 {int(row['cluster'])}"
        assert row["description"] == f"解釋 {int(row['cluster'])}"
        assert row["top_features"] == ["訊息數高", "活躍天數高"]
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_cluster_interpreter.py -v`

Expected: FAIL because `src.cluster_interpreter` does not exist.

- [ ] **Step 3: Implement `build_cluster_summaries` and `apply_cluster_interpretations`**

Create `src/cluster_interpreter.py` with:

```python
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


SUMMARY_FEATURE_LIMIT = 4


def _numeric(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.select_dtypes(include=[np.number]).drop(columns=["cluster"], errors="ignore").replace([np.inf, -np.inf], 0).fillna(0)


def build_cluster_summaries(clustered_features: pd.DataFrame, feature_frame: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    numeric = _numeric(clustered_features)
    global_mean = numeric.mean() if not numeric.empty else pd.Series(dtype=float)
    global_std = numeric.std(ddof=0).replace(0, 1) if not numeric.empty else pd.Series(dtype=float)
    summaries: list[dict[str, Any]] = []

    for cluster_id, rows in clustered_features.groupby("cluster", sort=True):
        cluster_numeric = numeric.loc[rows.index]
        means = cluster_numeric.mean() if not cluster_numeric.empty else pd.Series(dtype=float)
        z_scores = ((means - global_mean) / global_std).replace([np.inf, -np.inf], 0).fillna(0)
        high = [str(key) for key in z_scores.sort_values(ascending=False).head(SUMMARY_FEATURE_LIMIT).index]
        low = [str(key) for key in z_scores.sort_values(ascending=True).head(SUMMARY_FEATURE_LIMIT).index]
        summaries.append(
            {
                "cluster": int(cluster_id),
                "member_count": int(len(rows)),
                "feature_means": {str(key): float(value) for key, value in means.round(4).items()},
                "top_high_features": high,
                "top_low_features": low,
            }
        )
    return summaries


def apply_cluster_interpretations(
    clustered_features: pd.DataFrame,
    interpretations: list[dict[str, Any]],
) -> pd.DataFrame:
    by_cluster = {int(item["cluster"]): item for item in interpretations}
    rows = []
    for user, row in clustered_features.iterrows():
        cluster_id = int(row["cluster"])
        interpretation = by_cluster[cluster_id]
        payload = row.to_dict()
        payload.update(
            {
                "user": user,
                "role_name": str(interpretation["roleName"]),
                "top_features": [str(item) for item in interpretation.get("evidence", [])][:3],
                "description": str(interpretation.get("description") or interpretation.get("tagline") or ""),
                "tagline": str(interpretation.get("tagline") or ""),
            }
        )
        rows.append(payload)
    return pd.DataFrame(rows).set_index("user")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_cluster_interpreter.py -v`

Expected: PASS.

---

### Task 2: OpenAI Interpretation Contract

**Files:**
- Modify: `src/cluster_interpreter.py`
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Create: `.env.example`
- Add tests: `tests/test_cluster_interpreter.py`

- [ ] **Step 1: Write failing tests for API key and mocked client**

Append tests:

```python
import pytest


def test_openai_interpreter_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(cluster_interpreter.ClusterInterpretationError, match="OPENAI_API_KEY"):
        cluster_interpreter.interpret_clusters_with_openai([{"cluster": 0, "member_count": 1}])


def test_normalize_interpretations_requires_all_clusters():
    summaries = [{"cluster": 0, "member_count": 1}, {"cluster": 1, "member_count": 1}]
    payload = {"clusters": [{"cluster": 0, "roleName": "A", "tagline": "B", "description": "C", "evidence": ["D"]}]}
    with pytest.raises(cluster_interpreter.ClusterInterpretationError, match="missing"):
        cluster_interpreter.normalize_interpretations(payload, summaries)
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_cluster_interpreter.py -v`

Expected: FAIL because the new functions/classes do not exist.

- [ ] **Step 3: Add OpenAI dependency and env files**

Update `requirements.txt` to include:

```text
openai
```

Update `.gitignore` to include:

```text
.env
.env.*
!.env.example
```

Create `.env.example`:

```text
OPENAI_API_KEY=
OPENAI_MODEL=
```

- [ ] **Step 4: Implement OpenAI contract**

Add to `src/cluster_interpreter.py`:

```python
import json
import os


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class ClusterInterpretationError(RuntimeError):
    pass


def normalize_interpretations(payload: dict[str, Any], summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = {int(summary["cluster"]) for summary in summaries}
    clusters = payload.get("clusters")
    if not isinstance(clusters, list):
        raise ClusterInterpretationError("AI 回傳格式缺少 clusters。")
    normalized = []
    seen: set[int] = set()
    for item in clusters:
        cluster_id = int(item["cluster"])
        seen.add(cluster_id)
        evidence = item.get("evidence") or []
        normalized.append(
            {
                "cluster": cluster_id,
                "roleName": str(item["roleName"]),
                "tagline": str(item["tagline"]),
                "description": str(item["description"]),
                "evidence": [str(value) for value in evidence][:5],
            }
        )
    missing = expected - seen
    if missing:
        raise ClusterInterpretationError(f"AI 回傳缺少 cluster: {sorted(missing)}")
    return sorted(normalized, key=lambda item: item["cluster"])


def _response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "clusters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "cluster": {"type": "integer"},
                        "roleName": {"type": "string"},
                        "tagline": {"type": "string"},
                        "description": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["cluster", "roleName", "tagline", "description", "evidence"],
                },
            }
        },
        "required": ["clusters"],
    }


def interpret_clusters_with_openai(
    summaries: list[dict[str, Any]],
    model: str | None = None,
) -> list[dict[str, Any]]:
    if not os.getenv("OPENAI_API_KEY"):
        raise ClusterInterpretationError("AI 分析需要後端設定 OPENAI_API_KEY。")
    try:
        from openai import OpenAI
    except ImportError as error:
        raise ClusterInterpretationError("AI 分析需要安裝 openai 套件。") from error

    client = OpenAI()
    selected_model = model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    prompt = {
        "instruction": "根據分群統計摘要，為每個 cluster 產生繁體中文角色名稱與解釋。不要要求或推測原始聊天內容。",
        "clusters": summaries,
    }
    try:
        response = client.responses.create(
            model=selected_model,
            input=[
                {"role": "system", "content": "你是資料探勘報告助教，只根據統計摘要解釋分群。請輸出 JSON。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "cluster_interpretations",
                    "strict": True,
                    "schema": _response_schema(),
                }
            },
        )
    except Exception as error:
        raise ClusterInterpretationError(f"OpenAI 分析失敗：{error}") from error

    try:
        return normalize_interpretations(json.loads(response.output_text), summaries)
    except (AttributeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ClusterInterpretationError(f"AI 回傳格式無法解析：{error}") from error
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_cluster_interpreter.py -v`

Expected: PASS.

---

### Task 3: Pipeline and Server Mode Routing

**Files:**
- Modify: `src/pipeline.py`
- Modify: `app/server.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing tests**

Add pipeline tests:

```python
import pytest
from src import pipeline


def test_analyze_text_rule_mode_has_analysis_metadata():
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()
    result = pipeline.analyze_text(text, mode="rule")
    assert result["app_data"]["analysisMode"] == "rule"
    assert result["app_data"]["clusterInterpretations"] == []


def test_analyze_text_rejects_invalid_mode():
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()
    with pytest.raises(ValueError, match="analysis mode"):
        pipeline.analyze_text(text, mode="bad")
```

Add server tests:

```python
def test_analyze_accepts_rule_mode(client):
    raw = (ROOT / "tests" / "fixtures" / "sample_chat.txt").read_bytes()
    res = client.post(
        "/analyze",
        data={"mode": "rule", "file": (io.BytesIO(raw), "chat.txt")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    assert res.get_json()["analysisMode"] == "rule"


def test_analyze_ai_mode_without_key_returns_error(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    raw = (ROOT / "tests" / "fixtures" / "sample_chat.txt").read_bytes()
    res = client.post(
        "/analyze",
        data={"mode": "ai_cluster", "file": (io.BytesIO(raw), "chat.txt")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "OPENAI_API_KEY" in res.get_json()["error"]
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_pipeline.py tests/test_server.py -v`

Expected: FAIL until pipeline/server accept mode and webreport emits metadata.

- [ ] **Step 3: Implement pipeline routing**

Modify `src/pipeline.py`:

```python
from . import cluster_interpreter, clustering, features, parser, report, roles, webreport

VALID_ANALYSIS_MODES = {"rule", "ai_cluster"}

def analyze_text(text: str, mode: str = "rule") -> dict[str, Any]:
    if mode not in VALID_ANALYSIS_MODES:
        raise ValueError(f"Unsupported analysis mode: {mode}")
    ...
    if mode == "rule":
        role_table = roles.assign_roles(clustered)
        user_roles = roles.roles_by_user(clustered, role_table)
        cluster_interpretations = []
    else:
        summaries = cluster_interpreter.build_cluster_summaries(clustered, feature_frame)
        cluster_interpretations = cluster_interpreter.interpret_clusters_with_openai(summaries)
        user_roles = cluster_interpreter.apply_cluster_interpretations(clustered, cluster_interpretations)
```

Pass `analysis_mode=mode` and `cluster_interpretations=cluster_interpretations` to `webreport.build_app_data`.

- [ ] **Step 4: Implement server mode parsing**

Modify `app/server.py`:

```python
def _app_data_from_text(text: str, mode: str = "rule") -> dict:
    result = pipeline.analyze_text(text, mode=mode)
    ...

@app.post("/analyze")
def analyze():
    mode = request.form.get("mode", "rule")
    ...
    return jsonify(_app_data_from_text(text, mode=mode))

@app.get("/sample")
def sample():
    mode = request.args.get("mode", "rule")
    ...
    return jsonify(_app_data_from_text(text, mode=mode))
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_pipeline.py tests/test_server.py -v`

Expected: PASS.

---

### Task 4: Webreport Schema Support

**Files:**
- Modify: `src/webreport.py`
- Modify: `tests/test_webreport.py`

- [ ] **Step 1: Write failing webreport test**

Add:

```python
def test_app_data_analysis_metadata_defaults():
    app_data, _, _ = _build()
    assert app_data["analysisMode"] == "rule"
    assert app_data["clusterInterpretations"] == []


def test_app_data_includes_cluster_interpretations():
    app_data, feature_frame, metadata = _build()
    interpretations = [
        {
            "cluster": c["id"],
            "roleName": f"AI 角色 {c['id']}",
            "tagline": f"摘要 {c['id']}",
            "description": f"解釋 {c['id']}",
            "evidence": ["訊息數高", "活躍天數高"],
            "members": [],
        }
        for c in app_data["clusterMeta"]["clusters"]
    ]
    rebuilt, _, _ = _build_with_mode("ai_cluster", interpretations)
    assert rebuilt["analysisMode"] == "ai_cluster"
    assert rebuilt["clusterInterpretations"]
```

Implement `_build_with_mode` in the test helper by calling `webreport.build_app_data(..., analysis_mode=..., cluster_interpretations=...)`.

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_webreport.py -v`

Expected: FAIL until `build_app_data` signature and output include new fields.

- [ ] **Step 3: Modify `build_app_data`**

Update signature:

```python
def build_app_data(..., analysis_mode: str = "rule", cluster_interpretations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
```

Add to returned data:

```python
"analysisMode": analysis_mode,
"clusterInterpretations": cluster_interpretations or [],
```

In `_empty_app_data`, include:

```python
"analysisMode": "rule",
"clusterInterpretations": [],
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_webreport.py -v`

Expected: PASS.

---

### Task 5: Frontend Mode Selector and AI Cluster Block

**Files:**
- Modify: `claude_design/app/app.jsx`
- Modify: `claude_design/app/views.jsx`
- Modify: `claude_design/app/styles.css`
- Modify: `tests/test_server.py` or add smoke assertions in existing tests if needed

- [ ] **Step 1: Modify `App` mode state**

In `claude_design/app/app.jsx`, add:

```jsx
const [analysisMode, setAnalysisMode] = useState("rule");
```

Change `analyze` to append mode:

```jsx
if (arg === "sample") {
  res = await fetch(`/sample?mode=${encodeURIComponent(analysisMode)}`);
} else {
  const form = new FormData();
  form.append("file", arg);
  form.append("mode", analysisMode);
  res = await fetch("/analyze", { method: "POST", body: form });
}
```

Pass props:

```jsx
<UploadView onStart={analyze} error={error} analysisMode={analysisMode} setAnalysisMode={setAnalysisMode} />
```

- [ ] **Step 2: Modify `UploadView`**

Update signature:

```jsx
function UploadView({ onStart, error, analysisMode, setAnalysisMode }) {
```

Add a segmented control before the drop zone:

```jsx
<div className="mode-picker" role="group" aria-label="分析模式">
  {[
    ["rule", "規則角色分析", "使用預先定義角色規則"],
    ["ai_cluster", "AI 分群命名", "先分群，再由 AI 解釋各群角色"],
  ].map(([id, title, desc]) => (
    <button key={id} className={"mode-option" + (analysisMode === id ? " active" : "")}
      onClick={() => setAnalysisMode(id)} type="button">
      <span>{title}</span>
      <small>{desc}</small>
    </button>
  ))}
</div>
```

- [ ] **Step 3: Add `AIClusterInterpretations` component**

In `views.jsx`, define:

```jsx
function AIClusterInterpretations({ mobile }) {
  const D = window.APP_DATA;
  if (D.analysisMode !== "ai_cluster" || !D.clusterInterpretations || !D.clusterInterpretations.length) return null;
  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead kicker="AI CLUSTER INTERPRETATION" title="AI 分群解釋" note="AI 只根據分群統計摘要命名，不讀取原始聊天內容。" />
      <div className="ai-cluster-grid">
        {D.clusterInterpretations.map((item) => (
          <div className="ai-cluster-card" key={item.cluster}>
            <div className="ai-cluster-meta">Cluster {item.cluster}</div>
            <h3>{item.roleName}</h3>
            <p className="ai-cluster-tagline">{item.tagline}</p>
            <p className="ai-cluster-description">{item.description}</p>
            <div className="ai-evidence">
              {(item.evidence || []).map((e) => <span key={e}>{e}</span>)}
            </div>
            <div className="ai-members">{(item.members || []).join("、")}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Render after the metric panels and before hall of fame:

```jsx
<AIClusterInterpretations mobile={mobile} />
```

Export it:

```jsx
Object.assign(window, { ..., AIClusterInterpretations });
```

- [ ] **Step 4: Add styles**

Add to `styles.css`:

```css
.mode-picker { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 30px; }
.mode-option { border: 1px solid var(--line-2); background: var(--surface); padding: 14px 16px; text-align: left; cursor: pointer; }
.mode-option.active { border-color: var(--ink); box-shadow: inset 0 0 0 1px var(--ink); }
.mode-option span { display: block; font-weight: 700; font-size: 15px; }
.mode-option small { display: block; color: var(--ink-3); margin-top: 4px; line-height: 1.4; }
.ai-cluster-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.ai-cluster-card { border: 1px solid var(--line); background: var(--surface); padding: 18px 20px; }
.ai-cluster-meta { font-family: var(--mono); color: var(--ink-3); font-size: 11px; letter-spacing: .08em; }
.ai-cluster-card h3 { margin-top: 8px; font-size: 22px; }
.ai-cluster-tagline { font-weight: 700; margin: 8px 0; }
.ai-cluster-description { color: var(--ink-2); line-height: 1.6; font-size: 14px; }
.ai-evidence { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.ai-evidence span { border: 1px solid var(--line); padding: 5px 8px; font-size: 12px; background: var(--paper); }
.ai-members { margin-top: 14px; color: var(--ink-3); font-size: 13px; line-height: 1.5; }
@media (max-width: 760px) {
  .mode-picker, .ai-cluster-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 5: Run frontend smoke via server tests**

Run: `python -m pytest tests/test_server.py tests/test_webreport.py -v`

Expected: PASS.

---

### Task 6: Full Verification

**Files:**
- All changed files

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v`

Expected: `14+ passed`; warnings are acceptable if unchanged.

- [ ] **Step 2: Run server**

Run: `python app/server.py --port 8000`

Expected: server starts at `http://127.0.0.1:8000`.

- [ ] **Step 3: Browser verify**

Open `http://127.0.0.1:8000`.

Check:

- upload screen shows mode selector
- rule mode sample analysis succeeds
- AI mode without `OPENAI_API_KEY` shows clear error
- no API key appears in page source or frontend JS

- [ ] **Step 4: Final status**

Run: `git status --short`

Expected: only intended files changed; local server logs remain untracked and are not committed.
