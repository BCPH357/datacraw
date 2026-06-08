from src import clustering, cluster_interpreter, features, parser, report, roles, webreport


def _build(analysis_mode="rule", cluster_interpretations=None):
    records = parser.to_dataframe(parser.parse_file("tests/fixtures/sample_chat.txt"))
    summary = parser.summarize(parser.parse_file("tests/fixtures/sample_chat.txt"))
    feature_frame = features.extract_features(records)
    clustered, metadata = clustering.cluster_users(feature_frame)
    role_table = roles.assign_roles(clustered)
    user_roles = roles.roles_by_user(clustered, role_table)
    group_health = report.build_group_health(user_roles, metadata)
    app_data = webreport.build_app_data(
        records,
        feature_frame,
        clustered,
        user_roles,
        group_health,
        metadata,
        summary,
        analysis_mode=analysis_mode,
        cluster_interpretations=cluster_interpretations,
    )
    return app_data, feature_frame, metadata


def test_app_data_top_level_keys():
    app_data, _, _ = _build()
    for key in ("group", "members", "ROLES", "AXES", "FEATURES", "roleDist",
                "superlatives", "observations", "heatmap", "scatter", "clusterMeta",
                "analysisMode", "clusterSelection", "clusterInterpretations"):
        assert key in app_data
    assert app_data["__embedded"] is True


def test_app_data_analysis_metadata_defaults():
    app_data, _, _ = _build()

    assert app_data["analysisMode"] == "rule"
    assert app_data["clusterSelection"] == "auto"
    assert app_data["clusterInterpretations"] == []


def test_app_data_includes_cluster_interpretations():
    base, _, _ = _build()
    interpretations = [
        {
            "cluster": c["id"],
            "roleName": f"AI 角色 {c['id']}",
            "tagline": f"摘要 {c['id']}",
            "description": f"解釋 {c['id']}",
            "evidence": ["訊息數高", "活躍天數高"],
            "members": [],
        }
        for c in base["clusterMeta"]["clusters"]
    ]

    app_data, _, _ = _build("ai_cluster", interpretations)

    assert app_data["analysisMode"] == "ai_cluster"
    assert app_data["clusterInterpretations"] == interpretations


def test_app_data_includes_dynamic_ai_role_metadata():
    records = parser.to_dataframe(parser.parse_file("tests/fixtures/sample_chat.txt"))
    summary = parser.summarize(parser.parse_file("tests/fixtures/sample_chat.txt"))
    feature_frame = features.extract_features(records)
    clustered, metadata = clustering.cluster_users(feature_frame)
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
    user_roles = cluster_interpreter.apply_cluster_interpretations(clustered, interpretations)
    group_health = report.build_group_health(user_roles, metadata)

    app_data = webreport.build_app_data(
        records,
        feature_frame,
        clustered,
        user_roles,
        group_health,
        metadata,
        summary,
        analysis_mode="ai_cluster",
        cluster_interpretations=interpretations,
    )

    for item in interpretations:
        role_name = item["roleName"]
        assert role_name in app_data["ROLES"]
        assert app_data["ROLES"][role_name]["title"] == role_name
        assert app_data["ROLES"][role_name]["cvar"]


def test_members_shape_and_stats():
    app_data, feature_frame, _ = _build()
    members = app_data["members"]
    assert len(members) == len(feature_frame)
    user_count = app_data["group"]["userCount"]
    assert user_count == len(feature_frame)

    ids = [m["id"] for m in members]
    assert len(set(ids)) == len(ids)  # ids are unique

    for member in members:
        assert set(member["stats"].keys()) == set(webreport.AXES)
        for value in member["stats"].values():
            assert 0 <= value <= 100
        for key in webreport.FEATURE_KEYS:
            assert key in member["f"]
        assert member["role"] in webreport.ROLES
        assert isinstance(member["tagline"], str) and member["tagline"]


def test_scatter_normalized_and_valid_clusters():
    app_data, feature_frame, _ = _build()
    valid_ids = {m["id"] for m in app_data["members"]}
    cluster_ids = {c["id"] for c in app_data["clusterMeta"]["clusters"]}
    assert len(app_data["scatter"]) == len(feature_frame)
    for point in app_data["scatter"]:
        assert point["id"] in valid_ids
        assert 0.0 <= point["x"] <= 1.0
        assert 0.0 <= point["y"] <= 1.0
        assert point["c"] in cluster_ids


def test_heatmap_rows_normalized():
    app_data, feature_frame, _ = _build()
    assert len(app_data["heatmap"]) == len(feature_frame)
    for row in app_data["heatmap"]:
        assert len(row["hours"]) == 24
        assert max(row["hours"]) <= 1.0 + 1e-6
        assert abs(max(row["hours"]) - 1.0) < 1e-6  # at least one peak hour


def test_role_dist_and_cluster_meta():
    app_data, feature_frame, metadata = _build()
    assert sum(app_data["roleDist"].values()) == len(feature_frame)
    clusters = app_data["clusterMeta"]["clusters"]
    assert app_data["clusterMeta"]["best_k"] == metadata["best_k"]
    assert len(clusters) == metadata["best_k"]
    assert [c["id"] for c in clusters] == list(range(len(clusters)))  # contiguous ids


def test_render_html_self_contained():
    app_data, _, _ = _build()
    html = webreport.render_html(app_data)
    assert "window.APP_DATA" in html
    assert "unpkg.com/react@" in html and "babel" in html.lower()
    # the demo data.js and external jsx/css refs are fully inlined
    assert 'src="app/data.js"' not in html
    assert 'src="app/charts.jsx"' not in html
    assert 'href="app/styles.css"' not in html
    # all five front-end scripts are inlined
    for marker in ("App", "PersonaCard", "Radar", "OverviewView", "MembersView"):
        assert marker in html
