from app import app


def test_home_returns_app_name():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert response.get_json()["application"] == "GitOps CI/CD Demo"


def test_health_endpoint():
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_ready_endpoint():
    response = app.test_client().get("/ready")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}
