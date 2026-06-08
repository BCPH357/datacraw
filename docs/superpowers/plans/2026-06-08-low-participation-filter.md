# Low-Participation Member Filter + Token Usage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exclude transient/low-participation members (≤ a configurable % share of total messages) from clustering, surface them transparently in the report, let users tune the threshold, and display AI-mode token usage.

**Architecture:** Filtering happens once, in `pipeline.analyze_text`, right after feature extraction — it's the only place that has both the full per-user `message_count` (needed to compute each user's share of the group total) and the responsibility to decide what enters clustering. A new pure helper `_split_by_participation` returns `(included_features, excluded_members)`; only `included_features` flows into clustering/roles/AI interpretation, while `excluded_members` rides along to the front end for display. AI-mode token usage is read off the OpenAI response's `usage` object and threaded through the same path.

**Tech Stack:** Python (pandas, Flask, pytest), React (Babel-in-browser JSX, no build step, no JS test runner — frontend behavior is verified via string assertions on server-served assets, matching existing tests).

---

## Spec reference

Design doc: `docs/superpowers/specs/2026-06-08-low-participation-filter-design.md`

Key decisions baked into this plan:
- Threshold is a **% share of total group messages**; default `1.0`; `share <= threshold` is excluded ("以下" is inclusive).
- Applies to **both** `rule` and `ai_cluster` modes.
- Excluded members are listed (name, message count, share %) in a dedicated "未列入分析" UI section — never silently dropped.
- AI-mode token usage (`input`/`output`/`total`) is read from the OpenAI response and shown in the report.
- Threshold ≤ 0 or unparsable input means "no filtering" (treated as `0`).
- If filtering leaves fewer than 2 members, raise a friendly `ValueError` telling the user to lower the threshold.

---

### Task 1: `_split_by_participation` helper in the pipeline

**Files:**
- Modify: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

This is a pure function: given a feature frame with a `message_count` column and a threshold percentage, it returns `(included_features, excluded_members)`. Testing it directly with a synthetic frame is faster and more precise than going through the full `analyze_text` pipeline (the bundled sample fixture only has 5 users / 9 messages, too small to exercise a 1% threshold meaningfully).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_pipeline.py` (near the top, after the existing imports — note you'll need `pandas`):

```python
import pandas as pd
import pytest

from src import clustering, features, parser, pipeline, report, roles
```

Then add these test functions (anywhere after the imports, e.g. right before `test_pipeline_outputs_valid_payloads`):

```python
def test_split_by_participation_excludes_low_share_members():
    feature_frame = pd.DataFrame(
        {"message_count": [970, 20, 5, 5]},
        index=["Alice", "Bob", "Carol", "Dave"],
    )

    included, excluded = pipeline._split_by_participation(feature_frame, min_share_pct=1.0)

    assert list(included.index) == ["Alice", "Bob"]
    assert excluded == [
        {"name": "Carol", "messageCount": 5, "sharePct": 0.5},
        {"name": "Dave", "messageCount": 5, "sharePct": 0.5},
    ]


def test_split_by_participation_keeps_everyone_when_threshold_is_zero():
    feature_frame = pd.DataFrame(
        {"message_count": [970, 20, 5, 5]},
        index=["Alice", "Bob", "Carol", "Dave"],
    )

    included, excluded = pipeline._split_by_participation(feature_frame, min_share_pct=0)

    assert list(included.index) == ["Alice", "Bob", "Carol", "Dave"]
    assert excluded == []


def test_split_by_participation_treats_share_at_threshold_as_excluded():
    feature_frame = pd.DataFrame(
        {"message_count": [970, 20, 5, 5]},
        index=["Alice", "Bob", "Carol", "Dave"],
    )

    included, excluded = pipeline._split_by_participation(feature_frame, min_share_pct=2.0)

    assert list(included.index) == ["Alice"]
    assert [item["name"] for item in excluded] == ["Bob", "Carol", "Dave"]
```

(`Bob` is exactly 20/1000 = 2.0% — the third test confirms "at or below" the threshold is excluded, matching "以下" being inclusive.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_pipeline.py -k split_by_participation -v`
Expected: FAIL with `AttributeError: module 'src.pipeline' has no attribute '_split_by_participation'` (or `module has no attribute`).

- [ ] **Step 3: Add the `pandas` import to `src/pipeline.py`**

`src/pipeline.py` currently has no `pandas` import (it only imports submodules). Modify the import block at the top:

```python
from __future__ import annotations

from typing import Any

import pandas as pd

from . import cluster_interpreter, clustering, features, parser, report, roles, webreport
```

- [ ] **Step 4: Implement `_split_by_participation`**

Add this function at the end of `src/pipeline.py` (after `analyze_text`):

```python
def _split_by_participation(
    feature_frame: pd.DataFrame,
    min_share_pct: float,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Split users by their share of the group's total messages.

    Users whose ``message_count`` makes up at most ``min_share_pct`` percent of
    the group total are treated as transient members (joined and left quickly)
    and excluded from clustering. They are still reported back as a separate
    list — name, message count, share — so the UI can show who was left out and
    why, instead of silently dropping them.
    """

    if feature_frame.empty or min_share_pct <= 0:
        return feature_frame, []

    total_messages = feature_frame["message_count"].sum()
    if total_messages <= 0:
        return feature_frame, []

    threshold = min_share_pct / 100.0
    share = feature_frame["message_count"] / total_messages
    excluded_mask = share <= threshold

    excluded = [
        {
            "name": str(user),
            "messageCount": int(feature_frame.loc[user, "message_count"]),
            "sharePct": round(float(share.loc[user]) * 100, 2),
        }
        for user in feature_frame.index[excluded_mask]
    ]
    return feature_frame.loc[~excluded_mask], excluded
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -k split_by_participation -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: split low-participation members out of clustering input"
```

---

### Task 2: Token usage from the OpenAI response

**Files:**
- Modify: `src/cluster_interpreter.py`
- Test: `tests/test_cluster_interpreter.py`

Change `interpret_clusters_with_openai` to return `(interpretations, usage)` where `usage` is `{"input": int, "output": int, "total": int}`, read off `response.usage`. Missing/`None` usage degrades to all-zeros rather than raising — token reporting is a nice-to-have, never a reason to fail the analysis.

- [ ] **Step 1: Write the failing tests**

Add `import json` to the top of `tests/test_cluster_interpreter.py` (it currently only imports `pytest` and the `src` modules):

```python
import json

import pytest

from src import clustering, cluster_interpreter, features, parser
```

Then add these tests (e.g. after `test_openai_interpreter_requires_api_key`):

```python
def test_interpret_clusters_with_openai_returns_token_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeUsage:
        input_tokens = 120
        output_tokens = 45
        total_tokens = 165

    class FakeResponse:
        output_text = json.dumps({
            "clusters": [
                {"cluster": 0, "roleName": "A", "tagline": "B", "description": "C", "evidence": []},
            ]
        })
        usage = FakeUsage()

    class FakeResponses:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr("openai.OpenAI", FakeClient)

    interpretations, usage = cluster_interpreter.interpret_clusters_with_openai(
        [{"cluster": 0, "member_count": 1}]
    )

    assert interpretations[0]["roleName"] == "A"
    assert usage == {"input": 120, "output": 45, "total": 165}


def test_interpret_clusters_with_openai_handles_missing_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeResponse:
        output_text = json.dumps({
            "clusters": [
                {"cluster": 0, "roleName": "A", "tagline": "B", "description": "C", "evidence": []},
            ]
        })
        usage = None

    class FakeResponses:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr("openai.OpenAI", FakeClient)

    _, usage = cluster_interpreter.interpret_clusters_with_openai(
        [{"cluster": 0, "member_count": 1}]
    )

    assert usage == {"input": 0, "output": 0, "total": 0}
```

Note: `interpret_clusters_with_openai` does `from openai import OpenAI` *inside* the function body, so monkeypatching `openai.OpenAI` (the attribute on the real `openai` module) is what takes effect — the `openai` package is already a project dependency (used at runtime), so `monkeypatch.setattr("openai.OpenAI", FakeClient)` works without any import-time gymnastics.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cluster_interpreter.py -k token_usage -v`
Expected: FAIL — `ValueError: too many values to unpack` (the function currently returns a plain list, not a tuple).

- [ ] **Step 3: Add `_extract_usage` and change the return value**

In `src/cluster_interpreter.py`, add this helper near the other module-level helpers (e.g. directly above `interpret_clusters_with_openai`):

```python
def _extract_usage(response: Any) -> dict[str, int]:
    """Read input/output/total token counts off an OpenAI response, if present.

    Token reporting is informational only — a response without a populated
    ``usage`` (older SDKs, mocked clients, provider quirks) degrades to zeros
    rather than failing the whole analysis.
    """

    usage = getattr(response, "usage", None)
    return {
        "input": int(getattr(usage, "input_tokens", 0) or 0),
        "output": int(getattr(usage, "output_tokens", 0) or 0),
        "total": int(getattr(usage, "total_tokens", 0) or 0),
    }
```

Then update the end of `interpret_clusters_with_openai` (currently the final `try/except` block that parses `response.output_text`):

```python
    try:
        interpretations = normalize_interpretations(json.loads(response.output_text), summaries)
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise ClusterInterpretationError(f"AI 回傳格式無法解析：{error}") from error
    return interpretations, _extract_usage(response)
```

And update the function's return type annotation:

```python
def interpret_clusters_with_openai(
    summaries: list[dict[str, Any]],
    model: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_cluster_interpreter.py -v`
Expected: all pass (including the pre-existing `test_openai_interpreter_requires_api_key`, which raises before reaching the return so it's unaffected by the signature change).

- [ ] **Step 5: Commit**

```bash
git add src/cluster_interpreter.py tests/test_cluster_interpreter.py
git commit -m "feat: surface OpenAI token usage from cluster interpretation"
```

---

### Task 3: `build_app_data` carries excluded members, token usage, and the threshold

**Files:**
- Modify: `src/webreport.py`
- Test: `tests/test_webreport.py`

Add three new (optional, defaulted) parameters to `build_app_data` and matching keys in its output dict and in `_empty_app_data`. Doing this *before* wiring up `analyze_text` (Task 4) means `analyze_text` can pass the new arguments without ever calling a `build_app_data` that doesn't understand them.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webreport.py` (e.g. after `test_app_data_analysis_metadata_defaults`):

```python
def test_app_data_excluded_members_and_token_usage_default_to_empty():
    app_data, _, _ = _build()

    assert app_data["excludedMembers"] == []
    assert app_data["excludeThresholdPct"] == 1.0
    assert app_data["tokenUsage"] is None


def test_app_data_carries_excluded_members_and_token_usage_when_provided():
    records = parser.to_dataframe(parser.parse_file("tests/fixtures/sample_chat.txt"))
    summary = parser.summarize(parser.parse_file("tests/fixtures/sample_chat.txt"))
    feature_frame = features.extract_features(records)
    clustered, metadata = clustering.cluster_users(feature_frame)
    role_table = roles.assign_roles(clustered)
    user_roles = roles.roles_by_user(clustered, role_table)
    group_health = report.build_group_health(user_roles, metadata)

    excluded = [{"name": "小明", "messageCount": 4, "sharePct": 0.4}]
    usage = {"input": 100, "output": 50, "total": 150}

    app_data = webreport.build_app_data(
        records, feature_frame, clustered, user_roles, group_health, metadata, summary,
        excluded_members=excluded,
        token_usage=usage,
        exclude_threshold_pct=2.5,
    )

    assert app_data["excludedMembers"] == excluded
    assert app_data["excludeThresholdPct"] == 2.5
    assert app_data["tokenUsage"] == usage
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_webreport.py -k "excluded_members" -v`
Expected: FAIL with `KeyError: 'excludedMembers'`.

- [ ] **Step 3: Extend `build_app_data`'s signature and return dict**

In `src/webreport.py`, modify the `build_app_data` signature (currently ending with `cluster_interpretations: list[dict[str, Any]] | None = None,`):

```python
def build_app_data(
    records: pd.DataFrame,
    features: pd.DataFrame,
    clustered: pd.DataFrame,
    user_roles: pd.DataFrame,
    group_health: dict[str, Any],
    metadata: dict[str, Any],
    summary: dict[str, Any],
    analysis_mode: str = "rule",
    cluster_selection: str = "auto",
    cluster_interpretations: list[dict[str, Any]] | None = None,
    excluded_members: list[dict[str, Any]] | None = None,
    token_usage: dict[str, int] | None = None,
    exclude_threshold_pct: float = 1.0,
) -> dict[str, Any]:
```

Then modify the returned dict (currently ending with `"clusterInterpretations": cluster_interpretations or [],` followed by `"__embedded": True,`):

```python
        "clusterInterpretations": cluster_interpretations or [],
        "excludedMembers": excluded_members or [],
        "excludeThresholdPct": float(exclude_threshold_pct),
        "tokenUsage": token_usage,
        "__embedded": True,
```

- [ ] **Step 4: Add matching defaults to `_empty_app_data`**

In `_empty_app_data`, add the three keys (e.g. right after `"clusterInterpretations": [],`):

```python
        "clusterInterpretations": [],
        "excludedMembers": [],
        "excludeThresholdPct": 1.0,
        "tokenUsage": None,
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_webreport.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/webreport.py tests/test_webreport.py
git commit -m "feat: carry excluded members and token usage through APP_DATA"
```

---

### Task 4: Wire filtering and token usage into `analyze_text`

**Files:**
- Modify: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

Now connect the pieces from Tasks 1–3: `analyze_text` gains a `min_share_pct` parameter (default `1.0`), splits the feature frame before clustering, raises a friendly error if filtering leaves too few members, and threads `excluded_members` / `token_usage` through to `build_app_data`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_pipeline.py` (e.g. after `test_analyze_text_rejects_invalid_mode`):

```python
def test_analyze_text_excludes_low_share_members():
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()

    result = pipeline.analyze_text(text, mode="rule", min_share_pct=15)

    app_data = result["app_data"]
    excluded_names = {item["name"] for item in app_data["excludedMembers"]}
    member_names = {member["name"] for member in app_data["members"]}
    assert excluded_names
    assert excluded_names.isdisjoint(member_names)
    assert app_data["excludeThresholdPct"] == 15


def test_analyze_text_raises_friendly_error_when_threshold_too_high():
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()

    with pytest.raises(ValueError, match="排除門檻過高"):
        pipeline.analyze_text(text, mode="rule", min_share_pct=25)


def test_analyze_text_ai_cluster_mode_carries_token_usage(monkeypatch):
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()

    def fake_interpret(summaries, model=None):
        interpretations = [
            {
                "cluster": summary["cluster"],
                "roleName": f"AI 角色 {summary['cluster']}",
                "tagline": "t",
                "description": "d",
                "evidence": [],
            }
            for summary in summaries
        ]
        return interpretations, {"input": 10, "output": 5, "total": 15}

    monkeypatch.setattr(pipeline.cluster_interpreter, "interpret_clusters_with_openai", fake_interpret)

    result = pipeline.analyze_text(text, mode="ai_cluster")

    assert result["app_data"]["tokenUsage"] == {"input": 10, "output": 5, "total": 15}
```

(The sample fixture has 5 users with message-share percentages of roughly 22.2 / 22.2 / 11.1 / 33.3 / 11.1. A 15% threshold excludes the two ~11.1% members, leaving 3 — enough to cluster. A 25% threshold excludes four of five, leaving 1 — too few, triggering the friendly error.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_pipeline.py -k "excludes_low_share or threshold_too_high or carries_token_usage" -v`
Expected: FAIL — the first two with `KeyError: 'excludedMembers'` (or `TypeError: analyze_text() got an unexpected keyword argument 'min_share_pct'`), the third with `ValueError: too many values to unpack` (pipeline still expects a single return value from `interpret_clusters_with_openai`).

- [ ] **Step 3: Rewrite `analyze_text`**

Replace the entire `analyze_text` function body in `src/pipeline.py` with:

```python
def analyze_text(
    text: str,
    mode: str = "rule",
    cluster_count: int | str | None = "auto",
    min_share_pct: float = 1.0,
) -> dict[str, Any]:
    """Run the full pipeline on raw LINE export text.

    Returns a dict with ``app_data`` (for the React UI), ``personas``,
    ``group_health`` and ``summary``. Raises ``ValueError`` when the text has no
    analyzable user messages.
    """

    if mode not in VALID_ANALYSIS_MODES:
        raise ValueError(f"Unsupported analysis mode: {mode}")

    parsed = parser.parse_text(text)
    records = parser.to_dataframe(parsed)
    summary = parser.summarize(parsed)
    if records.empty or records[~records["is_system"]].empty:
        raise ValueError("找不到任何可分析的使用者訊息，請確認這是 LINE 匯出的 .txt 檔。")

    feature_frame = features.extract_features(records)
    included_features, excluded_members = _split_by_participation(feature_frame, min_share_pct)
    if excluded_members and len(included_features) < 2:
        raise ValueError("排除門檻過高，剩餘可分析成員不足，請調低門檻。")

    clustered, metadata = clustering.cluster_users(included_features, cluster_count=cluster_count)
    token_usage: dict[str, int] | None = None
    if mode == "rule":
        role_table = roles.assign_roles(clustered)
        user_roles = roles.roles_by_user(clustered, role_table)
        cluster_interpretations: list[dict[str, Any]] = []
    else:
        cluster_summaries = cluster_interpreter.build_cluster_summaries(clustered, included_features)
        cluster_interpretations, token_usage = cluster_interpreter.interpret_clusters_with_openai(cluster_summaries)
        cluster_interpretations = cluster_interpreter.attach_members_to_interpretations(
            clustered,
            cluster_interpretations,
        )
        user_roles = cluster_interpreter.apply_cluster_interpretations(clustered, cluster_interpretations)
    personas = report.build_personas(user_roles)
    group_health = report.build_group_health(user_roles, metadata)
    app_data = webreport.build_app_data(
        records,
        included_features,
        clustered,
        user_roles,
        group_health,
        metadata,
        summary,
        analysis_mode=mode,
        cluster_selection=str(cluster_count or "auto"),
        cluster_interpretations=cluster_interpretations,
        excluded_members=excluded_members,
        token_usage=token_usage,
        exclude_threshold_pct=min_share_pct,
    )
    return {
        "app_data": app_data,
        "personas": personas,
        "group_health": group_health,
        "summary": summary,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: all pass, including the pre-existing tests (the default `min_share_pct=1.0` excludes nobody in the sample fixture — its smallest share is ~11%, well above 1%).

- [ ] **Step 5: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: filter low-participation members out of analysis pipeline"
```

---

### Task 5: Server accepts and forwards the threshold

**Files:**
- Modify: `app/server.py`
- Test: `tests/test_server.py`

Add a `_parse_min_share_pct` helper that turns the raw form/query string into a float, defaulting unparsable or non-positive input to `0` (i.e. "no filtering") per the spec, and thread it through `_app_data_from_text`, `/analyze`, and `/sample`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_server.py` (e.g. after `test_analyze_accepts_requested_cluster_count`):

```python
def test_analyze_accepts_min_share_pct(client):
    raw = (ROOT / "tests" / "fixtures" / "sample_chat.txt").read_bytes()
    res = client.post(
        "/analyze",
        data={"mode": "rule", "min_share_pct": "15", "file": (io.BytesIO(raw), "chat.txt")},
        content_type="multipart/form-data",
    )

    data = res.get_json()
    assert res.status_code == 200
    assert data["excludeThresholdPct"] == 15
    assert data["excludedMembers"]


def test_analyze_treats_invalid_min_share_pct_as_no_filter(client):
    raw = (ROOT / "tests" / "fixtures" / "sample_chat.txt").read_bytes()
    res = client.post(
        "/analyze",
        data={"mode": "rule", "min_share_pct": "not-a-number", "file": (io.BytesIO(raw), "chat.txt")},
        content_type="multipart/form-data",
    )

    data = res.get_json()
    assert res.status_code == 200
    assert data["excludeThresholdPct"] == 0
    assert data["excludedMembers"] == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_server.py -k min_share_pct -v`
Expected: FAIL — `assert 1.0 == 15` (the server doesn't read `min_share_pct` yet, so the pipeline default `1.0` is used and nobody gets excluded at that scale).

- [ ] **Step 3: Add `_parse_min_share_pct` and wire it through**

In `app/server.py`, add this helper right after the imports/module constants (e.g. directly above `_app_data_from_text`):

```python
def _parse_min_share_pct(raw: str | None) -> float:
    """Parse the user-supplied exclusion threshold.

    Unparsable or non-positive input means "no filtering" — the threshold is a
    convenience knob, not something that should ever turn a bad value into a
    confusing failure.
    """

    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return value if value > 0 else 0.0
```

Then modify `_app_data_from_text` to accept and forward the threshold:

```python
def _app_data_from_text(
    text: str,
    mode: str = "rule",
    cluster_count: str = "auto",
    min_share_pct: float = 1.0,
) -> dict:
    """Run the pipeline and return APP_DATA flagged for the live (upload) flow."""

    result = pipeline.analyze_text(text, mode=mode, cluster_count=cluster_count, min_share_pct=min_share_pct)
    app_data = result["app_data"]
    # In the live flow data arrives *after* upload, so keep the upload/re-analyze
    # affordances available (do not auto-skip the upload screen).
    app_data["__embedded"] = False
    return app_data
```

Then in `/analyze`, add the parameter read and pass it through (the function currently reads `mode` and `cluster_count` from `request.form` then calls `_app_data_from_text`):

```python
    mode = request.form.get("mode", "rule")
    cluster_count = request.form.get("cluster_count", "auto")
    min_share_pct = _parse_min_share_pct(request.form.get("min_share_pct", "1"))
    text = uploaded.read().decode("utf-8-sig", errors="replace")
    try:
        return jsonify(_app_data_from_text(text, mode=mode, cluster_count=cluster_count, min_share_pct=min_share_pct))
```

And in `/sample` (mirrors `/analyze` but reads `request.args`):

```python
    mode = request.args.get("mode", "rule")
    cluster_count = request.args.get("cluster_count", "auto")
    min_share_pct = _parse_min_share_pct(request.args.get("min_share_pct", "1"))
    try:
        return jsonify(_app_data_from_text(text, mode=mode, cluster_count=cluster_count, min_share_pct=min_share_pct))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_server.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/server.py tests/test_server.py
git commit -m "feat: accept exclusion threshold on analyze/sample endpoints"
```

---

### Task 6: Frontend state — threshold travels with every analysis request

**Files:**
- Modify: `claude_design/app/app.jsx`
- Test: `tests/test_server.py`

Add `excludeThreshold` state (default `"1"`, a string like `clusterCount` already is), send it as `min_share_pct` on both the upload (`FormData`) and sample (`URLSearchParams`) paths, and pass the state down to `UploadView`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_server.py` (e.g. after `test_frontend_assets_include_analysis_mode_ui`):

```python
def test_frontend_assets_include_exclude_threshold_state(client):
    app_js = client.get("/app/app.jsx").get_data(as_text=True)

    assert "excludeThreshold" in app_js
    assert "min_share_pct" in app_js
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_server.py -k exclude_threshold_state -v`
Expected: FAIL — `assert 'excludeThreshold' in app_js` is False.

- [ ] **Step 3: Add the state and wire it into both request paths**

In `claude_design/app/app.jsx`, modify the state declarations (currently `const [clusterCount, setClusterCount] = useState("auto");`):

```jsx
  const [clusterCount, setClusterCount] = useState("auto");
  const [excludeThreshold, setExcludeThreshold] = useState("1");
```

Then modify the `analyze` function's request-building (currently builds `params`/`form` with just `mode` and `cluster_count`):

```jsx
      if (arg === "sample") {
        const params = new URLSearchParams({ mode: analysisMode, cluster_count: clusterCount, min_share_pct: excludeThreshold });
        res = await fetch(`/sample?${params.toString()}`);
      } else {
        const form = new FormData();
        form.append("file", arg);
        form.append("mode", analysisMode);
        form.append("cluster_count", clusterCount);
        form.append("min_share_pct", excludeThreshold);
        res = await fetch("/analyze", { method: "POST", body: form });
      }
```

Then modify the `UploadView` render call (currently passes `analysisMode`/`setAnalysisMode`/`clusterCount`/`setClusterCount`):

```jsx
  if (stage === "upload") return <UploadView onStart={analyze} error={error}
    analysisMode={analysisMode} setAnalysisMode={setAnalysisMode}
    clusterCount={clusterCount} setClusterCount={setClusterCount}
    excludeThreshold={excludeThreshold} setExcludeThreshold={setExcludeThreshold} />;
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_server.py -k exclude_threshold_state -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add claude_design/app/app.jsx tests/test_server.py
git commit -m "feat: send exclusion threshold with every analysis request"
```

---

### Task 7: Upload screen — threshold input

**Files:**
- Modify: `claude_design/app/views.jsx`
- Modify: `claude_design/app/styles.css`
- Test: `tests/test_server.py`

Add a numeric input to `UploadView`, right below the existing cluster-count picker, following the same `picker-label` convention already used there.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_server.py` (e.g. right after `test_frontend_assets_include_exclude_threshold_state` from Task 6):

```python
def test_frontend_assets_include_threshold_input(client):
    views_js = client.get("/app/views.jsx").get_data(as_text=True)

    assert "excludeThreshold" in views_js
    assert "排除低度參與門檻" in views_js
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_server.py -k threshold_input -v`
Expected: FAIL — `assert 'excludeThreshold' in views_js` is False.

- [ ] **Step 3: Add the input to `UploadView`**

In `claude_design/app/views.jsx`, modify the `UploadView` function signature (currently `function UploadView({ onStart, error, analysisMode, setAnalysisMode, clusterCount, setClusterCount }) {`):

```jsx
function UploadView({ onStart, error, analysisMode, setAnalysisMode, clusterCount, setClusterCount, excludeThreshold, setExcludeThreshold }) {
```

Then add the input block right after the existing cluster-picker `</div>` (the block that renders `clusterOptions.map(...)`, ending at line 95 in the current file — the closing `</div>` right before `<div onDragOver={...}` which starts the drop zone):

```jsx
      <div className="picker-label">排除低度參與門檻</div>
      <div className="threshold-row">
        <input type="number" className="threshold-input" min="0" step="0.5"
          value={excludeThreshold} onChange={(e) => setExcludeThreshold(e.target.value)} />
        <span className="threshold-note">% 以下的成員不納入分群計算（設為 0 表示不過濾）。用來排除「短暫加入又退出」的成員，避免他們扭曲分群結果。</span>
      </div>
```

- [ ] **Step 4: Add matching CSS**

In `claude_design/app/styles.css`, add these rules right after `.ai-members { ... }` (just before the `/* 手機版 RWD ... */` comment block):

```css
/* exclusion threshold input */
.threshold-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.threshold-input {
  width: 84px;
  border: 1px solid var(--line-2);
  background: var(--surface);
  color: var(--ink);
  padding: 10px 12px;
  font-family: var(--mono);
  font-size: 15px;
  text-align: right;
}
.threshold-input:focus {
  outline: none;
  border-color: var(--ink);
}
.threshold-note {
  color: var(--ink-3);
  font-size: 13px;
  line-height: 1.5;
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_server.py -k threshold_input -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add claude_design/app/views.jsx claude_design/app/styles.css tests/test_server.py
git commit -m "feat: add exclusion-threshold input to upload screen"
```

---

### Task 8: Report — "未列入分析" panel and AI token usage display

**Files:**
- Modify: `claude_design/app/views.jsx`
- Modify: `claude_design/app/styles.css`
- Test: `tests/test_server.py`

Add an `ExcludedMembersPanel` component (rendered in `OverviewView`, right after `AIClusterInterpretations`, hidden when there's nothing excluded) and extend `AIClusterInterpretations` to show token usage in its section header when available.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_server.py` (e.g. right after `test_frontend_assets_include_threshold_input` from Task 7):

```python
def test_frontend_assets_include_excluded_members_and_token_usage_ui(client):
    views_js = client.get("/app/views.jsx").get_data(as_text=True)

    assert "ExcludedMembersPanel" in views_js
    assert "未列入分析" in views_js
    assert "excludedMembers" in views_js
    assert "tokenUsage" in views_js
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_server.py -k excluded_members_and_token_usage -v`
Expected: FAIL — `assert 'ExcludedMembersPanel' in views_js` is False.

- [ ] **Step 3: Add `ExcludedMembersPanel` and extend `AIClusterInterpretations`**

In `claude_design/app/views.jsx`, replace the existing `AIClusterInterpretations` function:

```jsx
function AIClusterInterpretations({ mobile }) {
  const D = window.APP_DATA;
  if (D.analysisMode !== "ai_cluster" || !D.clusterInterpretations || !D.clusterInterpretations.length) return null;
  const usage = D.tokenUsage;
  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead kicker="AI CLUSTER INTERPRETATION" title="AI 分群解釋" note="AI 只根據分群統計摘要命名，不讀取原始聊天內容。"
        right={usage ? (
          <div style={{ textAlign: "right" }}>
            <div className="kicker">TOKEN 用量</div>
            <div className="num" style={{ fontSize: 22 }}>{usage.total.toLocaleString("en-US")}</div>
            <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 2 }}>
              輸入 {usage.input.toLocaleString("en-US")} · 輸出 {usage.output.toLocaleString("en-US")}
            </div>
          </div>
        ) : null} />
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

function ExcludedMembersPanel() {
  const D = window.APP_DATA;
  const excluded = D.excludedMembers || [];
  if (!excluded.length) return null;
  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead kicker="EXCLUDED FROM ANALYSIS" title="未列入分析"
        note={`發言量佔群組總訊息 ${D.excludeThresholdPct}% 以下，視為短暫加入又退出，不參與分群計算。`} />
      <div className="excluded-list">
        {excluded.map((item) => (
          <div className="excluded-item" key={item.name}>
            <span className="excluded-name">{item.name}</span>
            <span className="excluded-meta mono">{item.messageCount} 則訊息 · 佔比 {item.sharePct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Then in `OverviewView`, modify the line that renders `<AIClusterInterpretations mobile={mobile} />` to also render the new panel right after it:

```jsx
      <AIClusterInterpretations mobile={mobile} />
      <ExcludedMembersPanel />
```

- [ ] **Step 4: Add matching CSS**

In `claude_design/app/styles.css`, add these rules right after the `.threshold-note { ... }` block added in Task 7:

```css
/* excluded members */
.excluded-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
}
.excluded-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  background: var(--surface);
  padding: 12px 16px;
}
.excluded-name {
  font-weight: 600;
  font-size: 14px;
}
.excluded-meta {
  color: var(--ink-3);
  font-size: 12px;
  white-space: nowrap;
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_server.py -k excluded_members_and_token_usage -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add claude_design/app/views.jsx claude_design/app/styles.css tests/test_server.py
git commit -m "feat: show excluded members and AI token usage in the report"
```

---

### Task 9: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `python -m pytest -v`
Expected: all tests pass (no failures, no errors). This confirms Tasks 1–8 compose correctly — in particular that the default `min_share_pct=1.0` doesn't change any pre-existing test's expectations (the bundled sample fixture's smallest member share is ~11%, comfortably above 1%).

- [ ] **Step 2: Manually exercise the upload flow in a browser**

Run: `python app/server.py` (defaults to `http://127.0.0.1:8000`)

Then in a browser:
1. Open `http://127.0.0.1:8000`, pick "AI 分群命名" mode, set "排除低度參與門檻" to `15`, click "使用範例資料".
2. Confirm the report renders, the overview shows a "未列入分析" section listing the excluded members with their message counts and share percentages, and the AI 分群解釋 section's header shows a token-usage figure (requires `OPENAI_API_KEY` to be set — without it, AI mode returns a friendly error, which is expected and unrelated to this change).
3. Re-run with the threshold set to `0` and confirm the "未列入分析" section disappears (nobody excluded).
4. Try an extreme threshold (e.g. `90`) and confirm the friendly error "排除門檻過高，剩餘可分析成員不足，請調低門檻。" appears instead of a crash.

This is a UI feature, so running it for real (not just unit tests) is required before calling it done.

- [ ] **Step 3: Clean up stray log files** (only if they're a result of this work; otherwise skip)

The working tree has `server.stderr.log` / `server.stdout.log` as untracked files from a prior manual run — if your manual verification in Step 2 created or refreshed them and they shouldn't be committed, remove them:

```bash
rm -f server.stderr.log server.stdout.log
```

(Do not commit them — they're not part of this feature.)
