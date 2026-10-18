def test_health_reports_degraded_when_database_unreachable(client_without_db):
    response = client_without_db.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "db": "error", "version": "0.1.0"}


def test_health_reports_ok_with_database(client_with_db):
    response = client_with_db.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "version": "0.1.0"}
