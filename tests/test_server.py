import importlib.util
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client():
    spec = importlib.util.spec_from_file_location("line_server", ROOT / "app" / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.app.config["TESTING"] = True
    return module.app.test_client()


def test_index_serves_upload_page(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "window.APP_DATA" not in body  # no demo data baked in
    assert 'src="app/app.jsx"' in body  # boots the React app


def test_frontend_assets_include_analysis_mode_ui(client):
    app_js = client.get("/app/app.jsx").get_data(as_text=True)
    views_js = client.get("/app/views.jsx").get_data(as_text=True)

    assert "analysisMode" in app_js
    assert "規則角色分析" in views_js
    assert "AI 分群命名" in views_js
    assert "AIClusterInterpretations" in views_js


def test_analyze_returns_app_data(client):
    raw = (ROOT / "tests" / "fixtures" / "sample_chat.txt").read_bytes()
    res = client.post("/analyze", data={"file": (io.BytesIO(raw), "chat.txt")},
                      content_type="multipart/form-data")
    assert res.status_code == 200
    data = res.get_json()
    assert data["members"]
    assert data["__embedded"] is False
    assert data["group"]["userCount"] == len(data["members"])


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


def test_analyze_rejects_garbage(client):
    res = client.post("/analyze", data={"file": (io.BytesIO(b"not a chat"), "x.txt")},
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_sample_endpoint(client):
    res = client.get("/sample")
    assert res.status_code == 200
    assert res.get_json()["members"]
