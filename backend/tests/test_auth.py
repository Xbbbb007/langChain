import pytest
from backend.app.auth import hash_password, verify_password, create_access_token
from jose import jwt
from backend.app.config import settings

def test_password_hashing():
    password = "mysecretpassword123"
    hashed = hash_password(password)
    
    # 1. Hashed password should not be plain text
    assert hashed != password
    
    # 2. Verification should succeed with correct password
    assert verify_password(password, hashed) is True
    
    # 3. Verification should fail with incorrect password
    assert verify_password("wrongpassword", hashed) is False

def test_access_token_creation():
    data = {"sub": "testuser", "role": "user", "user_id": "test-uuid-123"}
    token = create_access_token(data)
    
    # 1. Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0
    
    # 2. We should be able to decode it and find our payload
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert payload.get("sub") == "testuser"
    assert payload.get("role") == "user"
    assert payload.get("user_id") == "test-uuid-123"
    assert "exp" in payload
