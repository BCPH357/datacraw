import pytest

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


def test_attach_members_to_interpretations_maps_cluster_members_locally():
    _, clustered, _ = _clustered_fixture()
    cluster_ids = sorted(int(c) for c in clustered["cluster"].unique())
    interpretations = [
        {
            "cluster": cluster_id,
            "roleName": f"AI 角色 {cluster_id}",
            "tagline": f"摘要 {cluster_id}",
            "description": f"解釋 {cluster_id}",
            "evidence": ["訊息數高"],
        }
        for cluster_id in cluster_ids
    ]

    enriched = cluster_interpreter.attach_members_to_interpretations(clustered, interpretations)

    for item in enriched:
        expected = [
            str(user)
            for user, row in clustered.iterrows()
            if int(row["cluster"]) == item["cluster"]
        ]
        assert item["members"] == expected
        assert item["roleName"] == f"AI 角色 {item['cluster']}"


def test_openai_interpreter_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(cluster_interpreter.ClusterInterpretationError, match="OPENAI_API_KEY"):
        cluster_interpreter.interpret_clusters_with_openai([{"cluster": 0, "member_count": 1}])


def test_normalize_interpretations_requires_all_clusters():
    summaries = [{"cluster": 0, "member_count": 1}, {"cluster": 1, "member_count": 1}]
    payload = {
        "clusters": [
            {
                "cluster": 0,
                "roleName": "A",
                "tagline": "B",
                "description": "C",
                "evidence": ["D"],
            }
        ]
    }

    with pytest.raises(cluster_interpreter.ClusterInterpretationError, match="缺少 cluster"):
        cluster_interpreter.normalize_interpretations(payload, summaries)
