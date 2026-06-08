import json

import pytest

from src import clustering, features, parser, pipeline, report, roles


def test_pipeline_outputs_valid_payloads(tmp_path):
    records = parser.to_dataframe(parser.parse_file("tests/fixtures/sample_chat.txt"))
    feature_frame = features.extract_features(records, tmp_path / "features.csv")
    clustered, metadata = clustering.cluster_users(feature_frame, tmp_path / "clusters.csv")
    role_table = roles.assign_roles(clustered)
    user_roles = roles.roles_by_user(clustered, role_table)
    personas = report.build_personas(user_roles, tmp_path / "personas.json")
    health = report.build_group_health(user_roles, metadata, tmp_path / "group_health.json")

    assert not feature_frame.empty
    assert "cluster" in clustered.columns
    assert len(personas) == len(feature_frame)
    assert 0 <= health["group_health_score"] <= 100
    assert sum(health["role_distribution"].values()) == len(feature_frame)
    assert json.loads((tmp_path / "personas.json").read_text(encoding="utf-8"))


def test_cluster_users_accepts_requested_cluster_count():
    records = parser.to_dataframe(parser.parse_file("tests/fixtures/sample_chat.txt"))
    feature_frame = features.extract_features(records)

    clustered, metadata = clustering.cluster_users(feature_frame, cluster_count=4)

    assert metadata["best_k"] == 4
    assert len(set(clustered["cluster"])) == 4


def test_cluster_users_rejects_impossible_cluster_count():
    records = parser.to_dataframe(parser.parse_file("tests/fixtures/sample_chat.txt"))
    feature_frame = features.extract_features(records)

    with pytest.raises(ValueError, match="分群數"):
        clustering.cluster_users(feature_frame, cluster_count=99)


def test_analyze_text_rule_mode_has_analysis_metadata():
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()
    result = pipeline.analyze_text(text, mode="rule")

    assert result["app_data"]["analysisMode"] == "rule"
    assert result["app_data"]["clusterInterpretations"] == []


def test_analyze_text_accepts_requested_cluster_count():
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()
    result = pipeline.analyze_text(text, mode="rule", cluster_count=4)

    assert result["app_data"]["clusterMeta"]["best_k"] == 4
    assert len(result["app_data"]["clusterMeta"]["clusters"]) == 4
    assert result["app_data"]["clusterSelection"] == "4"


def test_analyze_text_rejects_invalid_mode():
    text = open("tests/fixtures/sample_chat.txt", encoding="utf-8").read()

    with pytest.raises(ValueError, match="analysis mode"):
        pipeline.analyze_text(text, mode="bad")

