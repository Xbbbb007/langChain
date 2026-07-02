import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.auth import hash_password
from backend.app.models import User, ChatSession, ChatMessage, KnowledgeDocument

# Setup temporary file SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup: Create tables
    Base.metadata.create_all(bind=engine)
    
    # Pre-populate default admin user
    db = TestingSessionLocal()
    admin = User(
        username="admin",
        password_hash=hash_password("123456"),
        role="admin"
    )
    db.add(admin)
    db.commit()
    db.close()
    
    yield
    
    # Teardown: Drop tables and remove file
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_temp.db"):
        try:
            os.remove("test_temp.db")
        except Exception:
            pass


def test_user_registration_and_login():
    # 1. Register a normal user
    reg_response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "password123"}
    )
    assert reg_response.status_code == 201
    assert reg_response.json()["username"] == "testuser"
    assert reg_response.json()["role"] == "user"
    
    # 2. Duplicate registration should fail
    dup_response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "password123"}
    )
    assert dup_response.status_code == 400
    
    # 3. Login with registered user
    login_response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "password123"}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    assert login_response.json()["token_type"] == "bearer"

def test_role_based_access_control():
    # 1. Create a normal user token
    client.post("/api/auth/register", json={"username": "normaluser", "password": "password123"})
    login_user = client.post("/api/auth/login", data={"username": "normaluser", "password": "password123"})
    user_token = login_user.json()["access_token"]
    
    # 2. Login admin and get admin token
    login_admin = client.post("/api/auth/login", data={"username": "admin", "password": "123456"})
    admin_token = login_admin.json()["access_token"]
    
    # 3. Normal user attempts to list documents (should be 403 Forbidden)
    headers_user = {"Authorization": f"Bearer {user_token}"}
    doc_res_user = client.get("/api/knowledge/documents", headers=headers_user)
    assert doc_res_user.status_code == 403
    
    # 4. Admin attempts to list documents (should be 200 OK)
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    doc_res_admin = client.get("/api/knowledge/documents", headers=headers_admin)
    assert doc_res_admin.status_code == 200
    assert isinstance(doc_res_admin.json(), list)

def test_chat_session_endpoints():
    # Register and login user
    client.post("/api/auth/register", json={"username": "chatuser", "password": "password123"})
    login_res = client.post("/api/auth/login", data={"username": "chatuser", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create chat session
    create_res = client.post("/api/chat/sessions", json={"title": "我的新会话"}, headers=headers)
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]
    assert create_res.json()["title"] == "我的新会话"
    
    # 2. List chat sessions
    list_res = client.get("/api/chat/sessions", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == session_id
    
    # 3. Delete session
    del_res = client.delete(f"/api/chat/sessions/{session_id}", headers=headers)
    assert del_res.status_code == 200
    
    # 4. List chat sessions again (should be empty)
    list_res_empty = client.get("/api/chat/sessions", headers=headers)
    assert len(list_res_empty.json()) == 0
