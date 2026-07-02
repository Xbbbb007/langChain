from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User
from backend.app.auth import hash_password
from backend.app.routers import auth, chat, knowledge

# Create database tables (SQLite will create the rag_system.db file automatically)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI App
app = FastAPI(
    title="电商 RAG 企业级知识库问答系统",
    description="基于 LangChain + FastAPI + SQLite 的企业级商品知识库智能问答系统",
    version="1.0.0"
)

# Configure CORS for Frontend Integration
# In production, origins should be loaded from environment variables
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event: Create default admin user if not exists
@app.on_event("startup")
def create_default_admin():
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_pw = hash_password("123456")
            default_admin = User(
                username="admin",
                password_hash=hashed_pw,
                role="admin"
            )
            db.add(default_admin)
            db.commit()
            print("Successfully created default admin user (admin/123456).")
    except Exception as e:
        print(f"Error creating default admin user: {e}")
    finally:
        db.close()

# Register Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(knowledge.router)

@app.get("/")
def read_root():
    return {"message": "电商 RAG 知识库问答系统 API 已正常启动！"}
