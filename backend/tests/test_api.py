from .conftest import login


def _register(client, username, password="Passw0rd1"):
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _role_id(client, admin, code):
    return next(r["id"] for r in client.get("/api/roles", headers=admin).json() if r["code"] == code)


def test_health_and_public_content(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    stats = client.get("/api/stats/public").json()
    assert stats["documents"] >= 30 and stats["cases"] > 1000
    cats = client.get("/api/documents/categories").json()
    assert cats[0]["name"] == "伤寒金匮"
    doc = client.get("/api/documents/shanghan-taiyang").json()
    assert doc["chapters"]
    ch = client.get(f"/api/documents/shanghan-taiyang/chapters/{doc['chapters'][0]['id']}").json()
    assert ch["content"] and ch["prev_id"] is None


def test_me_has_all_permissions(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert me["is_superuser"] and "role:manage" in me["permissions"]


def test_register_gets_member_role_and_rbac(client):
    h = _register(client, "zhangsan")
    me = client.get("/api/auth/me", headers=h).json()
    assert [r["code"] for r in me["roles"]] == ["member"]
    assert set(me["permissions"]) == {"case:read", "ai:chat"}
    assert client.get("/api/users", headers=h).status_code == 403
    assert client.get("/api/cases?keyword=肝癌", headers=h).json()["total"] > 0
    # guests cannot read cases
    assert client.get("/api/cases").status_code == 401


def test_weak_password_and_duplicate(client):
    r = client.post("/api/auth/register", json={"username": "weakpw", "password": "abcdefgh"})
    assert r.status_code == 422
    _register(client, "dupuser")
    r = client.post("/api/auth/register", json={"username": "DupUser", "password": "Passw0rd1"})
    assert r.status_code == 409


def test_admin_privilege_boundaries(client, admin):
    admin_role = _role_id(client, admin, "admin")
    super_role = _role_id(client, admin, "super_admin")
    r = client.post("/api/users", headers=admin, json={
        "username": "ops", "password": "Passw0rd1", "role_ids": [admin_role], "must_change_password": False})
    assert r.status_code == 201
    ops = login(client, "ops", "Passw0rd1")
    assert client.get("/api/users", headers=ops).status_code == 200
    # cannot manage roles
    assert client.post("/api/roles", headers=ops, json={"code": "x1", "name": "x"}).status_code == 403
    # cannot grant super_admin
    r = client.post("/api/users", headers=ops, json={"username": "evil", "password": "Passw0rd1", "role_ids": [super_role]})
    assert r.status_code == 403
    # cannot modify the super admin
    admin_id = client.get("/api/auth/me", headers=admin).json()["id"]
    assert client.put(f"/api/users/{admin_id}", headers=ops, json={"nickname": "x"}).status_code == 403
    # cannot delete (no user:delete)
    assert client.delete(f"/api/users/{admin_id}", headers=ops).status_code == 403


def test_must_change_password_flow(client, admin):
    member = _role_id(client, admin, "member")
    r = client.post("/api/users", headers=admin, json={"username": "newbie", "password": "Passw0rd1", "role_ids": [member]})
    assert r.json()["must_change_password"] is True
    h = login(client, "newbie", "Passw0rd1")
    assert client.get("/api/cases", headers=h).status_code == 403
    r = client.post("/api/auth/change-password", headers=h, json={"old_password": "Passw0rd1", "new_password": "N3wPassword"})
    assert r.status_code == 200
    # old token invalidated
    assert client.get("/api/auth/me", headers=h).status_code == 401
    h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/cases", headers=h2).status_code == 200


def test_role_crud_and_permission_effect(client, admin):
    r = client.post("/api/roles", headers=admin, json={"code": "auditor", "name": "审计员", "permissions": ["audit:read"]})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert client.post("/api/roles", headers=admin, json={"code": "bad", "name": "b", "permissions": ["nope"]}).status_code == 400
    client.post("/api/users", headers=admin, json={
        "username": "aud", "password": "Passw0rd1", "role_ids": [rid], "must_change_password": False})
    h = login(client, "aud", "Passw0rd1")
    assert client.get("/api/audit-logs", headers=h).status_code == 200
    assert client.get("/api/cases", headers=h).status_code == 403
    # grant case:read at runtime -> effective immediately
    client.put(f"/api/roles/{rid}", headers=admin, json={"permissions": ["audit:read", "case:read"]})
    assert client.get("/api/cases", headers=h).status_code == 200
    # can't delete role in use; can't delete builtin
    assert client.delete(f"/api/roles/{rid}", headers=admin).status_code == 400
    assert client.delete(f"/api/roles/{_role_id(client, admin, 'member')}", headers=admin).status_code == 400
    # super_admin permissions immutable
    sid = _role_id(client, admin, "super_admin")
    assert client.put(f"/api/roles/{sid}", headers=admin, json={"permissions": []}).status_code == 400


def test_disable_user_kills_session(client, admin):
    h = _register(client, "tobedisabled")
    uid = client.get("/api/auth/me", headers=h).json()["id"]
    assert client.put(f"/api/users/{uid}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401
    r = client.post("/api/auth/login", json={"username": "tobedisabled", "password": "Passw0rd1"})
    assert r.status_code == 403


def test_lockout(client):
    _register(client, "locky")
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "locky", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "locky", "password": "Passw0rd1"})
    assert r.status_code == 423


def test_refresh_token(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin12345"}).json()
    r2 = client.post("/api/auth/refresh", json={"refresh_token": r["refresh_token"]})
    assert r2.status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": r["access_token"]}).status_code == 401


def test_cannot_delete_self_or_last_superadmin(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.delete(f"/api/users/{me['id']}", headers=admin).status_code == 400


def test_document_editing(client, admin):
    r = client.post("/api/documents", headers=admin, json={"slug": "test-doc", "title": "测试", "category": "研究资料"})
    did = r.json()["id"]
    # unpublished -> hidden from public
    assert client.get("/api/documents/test-doc").status_code == 404
    assert client.get("/api/documents/test-doc", headers=admin).status_code == 200
    ch = client.post(f"/api/documents/{did}/chapters", headers=admin, json={"title": "第一章", "content": "## 第一章\n桂枝汤"}).json()
    client.put(f"/api/documents/{did}", headers=admin, json={"is_published": True})
    doc = client.get("/api/documents/test-doc").json()
    assert doc["word_count"] == 6 and doc["chapters"][0]["id"] == ch["id"]
    h = _register(client, "editor_wannabe")
    assert client.put(f"/api/chapters/{ch['id']}", headers=h, json={"title": "x", "content": "y"}).status_code == 403


def test_search_and_favorites(client):
    h = _register(client, "reader")
    hits = client.get("/api/search", params={"q": "桂枝汤"}, headers=h).json()
    assert any(x["type"] == "chapter" for x in hits) and any(x["type"] == "case" for x in hits)
    # guests see no cases
    assert all(x["type"] == "chapter" for x in client.get("/api/search", params={"q": "桂枝汤"}).json())
    doc_id = client.get("/api/documents/jingui").json()["id"]
    assert client.post("/api/favorites", headers=h, json={"target_type": "document", "target_id": doc_id}).status_code == 200
    client.post("/api/favorites", headers=h, json={"target_type": "document", "target_id": doc_id})  # idempotent
    favs = client.get("/api/favorites", headers=h).json()
    assert len(favs) == 1 and favs[0]["title"].startswith("金匮")
    client.delete("/api/favorites", headers=h, params={"target_type": "document", "target_id": doc_id})
    assert client.get("/api/favorites", headers=h).json() == []


def test_audit_and_dashboard(client, admin):
    logs = client.get("/api/audit-logs", headers=admin, params={"action": "login"}).json()
    assert logs["total"] > 0
    d = client.get("/api/stats/dashboard", headers=admin).json()
    assert d["users"] > 1 and len(d["trend"]["days"]) == 7


def test_ai_disabled(client):
    h = _register(client, "aiuser")
    r = client.post("/api/ai/chat", headers=h, json={"messages": [{"role": "user", "content": "头痛怎么办"}]})
    assert r.status_code == 503


def test_retrieval():
    from app.db import SessionLocal
    from app.services import ai

    with SessionLocal() as db:
        refs = ai.retrieve(db, "小建中汤治什么病")
    assert refs and any("建中" in r["excerpt"] for r in refs)


def test_ai_stream_and_quota(client, monkeypatch):
    from app.config import get_settings
    from app.services import ai

    s = get_settings()
    monkeypatch.setattr(s, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(s, "ai_daily_limit", 2)

    def fake_stream(messages, usage):
        assert "<知识库检索片段>" in messages[-1]["content"]
        yield "我跟你说，"
        yield "这很简单嘛。"
        usage.update(input_tokens=10, output_tokens=5, stop_reason="end_turn")

    monkeypatch.setattr(ai, "stream_answer", fake_stream)
    h = _register(client, "aistream")
    body = {"messages": [{"role": "user", "content": "桂枝汤怎么用"}]}
    for _ in range(2):
        r = client.post("/api/ai/chat", headers=h, json=body)
        assert r.status_code == 200
        assert "event: refs" in r.text and "这很简单嘛" in r.text and "event: done" in r.text
    assert client.post("/api/ai/chat", headers=h, json=body).status_code == 429
    q = client.get("/api/ai/quota", headers=h).json()
    assert q == {"enabled": True, "used": 2, "limit": 2}
