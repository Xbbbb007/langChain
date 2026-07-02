from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Any

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[str] = None

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str

class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str

class UserOut(BaseModel):
    id: str
    username: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Message schemas
class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageOut(BaseModel):
    id: str
    sender: str
    content: str
    sources: Optional[str] = None  # JSON string of sources
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Session schemas
class ChatSessionCreate(BaseModel):
    title: str

class ChatSessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Knowledge Document schemas
class KnowledgeDocumentOut(BaseModel):
    id: str
    filename: str
    file_size: str
    chunk_count: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

