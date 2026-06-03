import json

from src import clustering, features, parser, report, roles


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

