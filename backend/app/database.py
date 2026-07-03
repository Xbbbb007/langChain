from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.config import settings

from sqlalchemy.event import listens_for

# For SQLite, check_same_thread is set to False to allow multiple threads to access it.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_size=50,
    max_overflow=100
)

# Enable WAL (Write-Ahead Logging) mode for SQLite to handle concurrency during load testing
if settings.DATABASE_URL.startswith("sqlite"):
    @listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI 依赖注入连接器：生成并管理当前请求的数据库 Session 会话。
    在处理请求时会创建并生成 Session，并在请求结束（处理完或发生异常）后，
    通过 finally 代码块自动关闭（close）数据库连接，防止连接泄露。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
