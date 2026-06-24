from __future__ import annotations

from fastapi.testclient import TestClient


class TestRegister:
    def test_register_success(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "novo", "password": "123", "password_confirm": "123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "novo"
        assert "session_token" in data

    def test_register_password_mismatch(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "outro", "password": "123", "password_confirm": "456"},
        )
        assert response.status_code == 400
        assert "nao conferem" in response.json()["detail"]

    def test_register_duplicate_username(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "dup", "password": "123", "password_confirm": "123"},
        )
        response = client.post(
            "/api/auth/register",
            json={"username": "dup", "password": "456", "password_confirm": "456"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"]


class TestLogin:
    def test_login_success(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "login", "password": "123", "password_confirm": "123"},
        )
        response = client.post(
            "/api/auth/login",
            json={"username": "login", "password": "123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "login"
        assert "session_token" in data
        assert "session_token" in response.cookies

    def test_login_wrong_password(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "senha", "password": "123", "password_confirm": "123"},
        )
        response = client.post(
            "/api/auth/login",
            json={"username": "senha", "password": "errada"},
        )
        assert response.status_code == 401
        assert "incorreta" in response.json()["detail"]

    def test_login_user_not_found(self, client):
        response = client.post(
            "/api/auth/login",
            json={"username": "naoexiste", "password": "123"},
        )
        assert response.status_code == 404
        assert "nao cadastrado" in response.json()["detail"]


class TestMe:
    def test_me_without_session(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["user"] is None

    def test_me_with_session(self, client):
        register_resp = client.post(
            "/api/auth/register",
            json={"username": "meuser", "password": "123", "password_confirm": "123"},
        )
        token = register_resp.json()["session_token"]

        response = client.get("/api/auth/me", cookies={"session_token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["user"] is not None
        assert data["user"]["username"] == "meuser"


class TestLogout:
    def test_logout_success(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"username": "logout", "password": "123", "password_confirm": "123"},
        )
        token = reg.json()["session_token"]

        response = client.post("/api/auth/logout", cookies={"session_token": token})
        assert response.status_code == 200
        assert "realizado com sucesso" in response.json()["message"]

        me = client.get("/api/auth/me", cookies={"session_token": token})
        assert me.json()["user"] is None

    def test_logout_twice(self, client):
        """Logout sem sessao ativa nao deve quebrar."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200