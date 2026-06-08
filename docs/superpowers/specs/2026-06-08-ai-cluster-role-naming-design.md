# AI Cluster Role Naming Design

## Purpose

This feature adds an optional AI analysis mode for the LINE Chat Persona Analyzer. The goal is to make the project better aligned with a data mining final project: discover user behavior groups through clustering first, then use AI to name and explain those clusters.

The existing rule-based persona assignment remains available as a baseline.

## Current Pipeline

The current backend flow is:

```text
parser
-> features.extract_features
-> clustering.cluster_users
-> roles.assign_roles / roles.roles_by_user
-> report.build_personas / report.build_group_health
-> webreport.build_app_data
-> React UI
```

The current role names are defined ahead of time in `src/roles.py`, then each user is scored against those predefined roles.

## Target User Flow

The upload screen will let the user choose the analysis mode before uploading a LINE `.txt` export:

```text
規則角色分析
使用預先定義角色規則，作為 baseline。

AI 分群命名
先分群，再由 AI 解釋各群角色。
```

After upload, the selected mode is sent to the backend as `mode=rule` or `mode=ai_cluster`.

## Analysis Modes

### Rule Mode

Rule mode preserves the existing behavior:

```text
features
-> clustering
-> roles.py predefined role scoring
-> report / webreport
```

This mode is useful as a stable baseline for comparing with the AI cluster interpretation mode.

### AI Cluster Mode

AI cluster mode changes the role interpretation layer:

```text
features
-> clustering
-> build cluster summaries
-> OpenAI cluster interpretation
-> apply cluster roles to users
-> report / webreport
```

KMeans remains responsible for discovering behavior groups. AI is responsible only for naming and explaining each cluster.

## Privacy Boundary

AI must never receive raw LINE chat messages.

The OpenAI request may include:

- cluster id
- member count
- anonymized member ids or member counts
- feature means
- feature percentile summaries
- high/low representative features
- cluster size and basic metadata

The OpenAI request must not include:

- raw message text
- full chat records
- original LINE export content
- message examples

This keeps the AI feature aligned with the project's privacy stance while still allowing meaningful cluster interpretation.

## Backend Design

Add a new module:

```text
src/cluster_interpreter.py
```

Responsibilities:

```text
build_cluster_summaries(clustered_features, feature_frame)
-> create one statistical summary per cluster

interpret_clusters_with_openai(cluster_summaries, model)
-> call OpenAI with structured output

apply_cluster_interpretations(clustered_features, interpretations)
-> attach AI role names and explanations to each user
```

`src/pipeline.py` will accept an analysis mode:

```python
analyze_text(text: str, mode: str = "rule") -> dict
```

Mode behavior:

```text
mode == "rule"
-> use existing roles.assign_roles and roles.roles_by_user

mode == "ai_cluster"
-> use cluster_interpreter for cluster summaries and AI naming
```

Invalid modes should return a clear validation error.

## OpenAI Integration

Use OpenAI from the Flask backend only.

Configuration:

```text
OPENAI_API_KEY=<local secret>
OPENAI_MODEL=<optional model override>
```

The real API key must not be committed to GitHub and must not appear in client-side code. The project should include:

```text
.env.example
```

with placeholders only:

```text
OPENAI_API_KEY=
OPENAI_MODEL=
```

The project should ignore local secret files:

```text
.env
.env.*
!.env.example
```

The implementation should use structured output so the AI response conforms to the schema the frontend expects. OpenAI's documentation recommends loading API keys from server-side environment variables and not exposing them in browser code. Structured Outputs are appropriate here because the UI needs predictable fields.

References:

- https://platform.openai.com/docs/api-reference/authentication/keys
- https://platform.openai.com/docs/guides/structured-outputs
- https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety

## AI Output Shape

The OpenAI response should contain one interpretation per cluster:

```json
{
  "clusters": [
    {
      "cluster": 0,
      "roleName": "討論推進核心",
      "tagline": "穩定推動群組互動的高活躍成員",
      "description": "這群成員在訊息量與活躍天數上明顯較高，通常扮演延續討論與維持互動熱度的角色。",
      "evidence": ["訊息數高", "活躍天數高", "每日平均訊息高"],
      "members": ["A", "B", "C"]
    }
  ]
}
```

The schema should require every cluster from the KMeans result to have exactly one interpretation.

## APP_DATA Changes

`webreport.build_app_data` should include:

```json
{
  "analysisMode": "ai_cluster",
  "clusterInterpretations": [
    {
      "cluster": 0,
      "roleName": "討論推進核心",
      "tagline": "穩定推動群組互動的高活躍成員",
      "description": "...",
      "evidence": ["訊息數高", "活躍天數高"],
      "members": ["A", "B"]
    }
  ]
}
```

For AI mode:

```text
member.role = cluster roleName
member.top = cluster evidence
member.cluster = existing cluster id
```

For rule mode:

```text
analysisMode = "rule"
clusterInterpretations = []
```

This keeps the existing member cards, role distribution, and charts mostly compatible.

## Frontend Design

Upload screen:

- Add a segmented mode control before upload.
- Labels:
  - `規則角色分析`
  - `AI 分群命名`
- Short descriptions:
  - `使用預先定義角色規則`
  - `先分群，再由 AI 解釋各群角色`

Report screen:

- Keep the existing overview, member cards, and chart views.
- Add an AI cluster interpretation block near the overview, before the member cards.
- Only show this block when `analysisMode === "ai_cluster"` and `clusterInterpretations` has content.

Each cluster card should show:

1. AI role name
2. one-sentence tagline
3. detailed explanation
4. representative features
5. member list

Colors should be based on cluster id or generated palette slots, not fixed predefined role names, because AI role names are dynamic.

## Error Handling

If the user chooses AI mode and the backend cannot complete AI interpretation:

- missing `OPENAI_API_KEY`
- OpenAI API error
- timeout
- rate limit
- invalid structured output
- model refusal

then the backend should return a clear error response. The frontend should show an error message such as:

```text
AI 分析目前無法使用，請確認後端 OPENAI_API_KEY 或網路狀態。
```

The system should not silently fall back to rule mode. Silent fallback would make users believe they are seeing AI-generated cluster interpretations when they are not.

## Testing Strategy

Tests that do not call OpenAI:

- rule mode preserves existing pipeline behavior
- invalid mode is rejected
- cluster summaries contain only statistical fields, not raw message text
- `apply_cluster_interpretations` assigns cluster role names to all users in each cluster
- `APP_DATA` contains `analysisMode` and `clusterInterpretations`
- missing API key in AI mode returns a clear error

Tests with mocked OpenAI:

- mocked structured response is applied to users correctly
- AI mode returns member cards using cluster role names
- AI cluster interpretation block data is present
- malformed AI response is treated as an error

No automated test should call the real OpenAI API.

## Non-Goals

This feature will not:

- send raw LINE messages to AI
- ask end users to enter their own API key
- remove the existing rule-based role system
- switch to another provider such as Gemini or Claude in this iteration
- implement local LLM support in this iteration

## Implementation Decisions

- `OPENAI_MODEL` is optional. If it is unset, implementation will use a low-cost OpenAI text model selected during implementation from current OpenAI documentation.
- Member names will not be sent to OpenAI. Cluster summaries will use anonymized member ids or counts, and the backend will map real display names back into `clusterInterpretations.members` after the AI response.
- No cross-request caching is required in this iteration. Each upload runs one analysis request. The frontend can navigate within the returned report without re-calling the backend.
