import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import User
from backend.app.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    # Hash a password using bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Verify a password against a hash
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成一个基于 JWT 的访问令牌 (Access Token)
    
    参数:
    * `data`: 需要编码存入 Token 的用户关键属性（例如: sub/用户名, role/角色, user_id/用户ID）
    * `expires_delta`: 自定义令牌失效的延续时长，如果不传则采用默认过期时间（系统默认 60 分钟）
    
    返回:
    * 返回加密签名后的 JWT 字符串，前端会在请求头或 URL Query 参数中带上此令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), 
    token_query: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI 依赖注入依赖项：解析并校验当前的 JWT 令牌，获取并返回对应的当前登录用户对象
    
    参数:
    * `token`: 来自请求头 Bearer Auth 中的加密 JWT (HTTP Header 自动注入)
    * `token_query`: 兼容 EventSource 浏览器 SSE 请求，支持从 URL Query 的 ?token=xxx 中注入令牌
    * `db`: SQLAlchemy 数据库会话连接
    
    异常:
    * 若 JWT 签名错误、已过期、用户信息不完整或用户在数据库中不存在，抛出 401 权限校验失败异常
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    active_token = token or token_query
    if not active_token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(active_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: str = payload.get("user_id")
        if username is None or role is None or user_id is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role, user_id=user_id)
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI 依赖注入依赖项：在上一步获取当前登录用户的基础上，二次校验是否为管理员角色 (Role-based access control)
    
    异常:
    * 若当前用户不是管理员，抛出 403 权限被拒绝异常，有效阻断普通用户越权进行知识库管理的操作
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators are allowed to access this resource"
        )
    return current_user
