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
