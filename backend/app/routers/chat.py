import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database import get_db, SessionLocal
from backend.app.models import User, ChatSession, ChatMessage
from backend.app.schemas import ChatSessionOut, ChatMessageOut, ChatSessionCreate
from backend.app.auth import get_current_user
from backend.app.rag.pipeline import get_rag_pipeline

router = APIRouter(prefix="/api/chat", tags=["Chat & Q&A"])

@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = ChatSession(
        user_id=current_user.id,
        title=session_data.title
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions", response_model=List[ChatSessionOut])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ChatSession)\
        .filter(ChatSession.user_id == current_user.id)\
        .order_by(ChatSession.updated_at.desc())\
        .all()

@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    db.delete(session)
    db.commit()
    return {"message": "Session deleted successfully"}

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageOut])
def get_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return db.query(ChatMessage)\
        .filter(ChatMessage.session_id == session_id)\
        .order_by(ChatMessage.created_at.ascii() if hasattr(ChatMessage.created_at, 'ascii') else ChatMessage.created_at.asc())\
        .all()

@router.get("/sessions/{session_id}/stream")
def stream_answer(
    session_id: str,
    query: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
):
    # Verify session ownership
    db_verify = SessionLocal()
    try:
        session = db_verify.query(ChatSession).filter(
            ChatSession.id == session_id, 
            ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Retrieve recent message history from database
        db_history = db_verify.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        chat_history = []
        for msg in db_history:
            role = "user" if msg.sender == "user" else "assistant"
            chat_history.append({"role": role, "content": msg.content})
            
    finally:
        db_verify.close()

    # Generator wrapper to handle streaming AND saving to DB
    def sse_generator():
        # Get active RAG pipeline
        rag = get_rag_pipeline()
        
        # Keep track of final assistant response and sources
        final_response = ""
        sources_list = []
        
        # Iterate over stream
        for data_line in rag.generate_rag_stream(query, chat_history):
            yield data_line
            
            # Parse streaming data to capture content and sources
            if data_line.startswith("data: "):
                try:
                    payload = json.loads(data_line[6:].strip())
                    if payload.get("type") == "sources":
                        sources_list = payload.get("sources", [])
                    elif payload.get("type") == "text":
                        final_response += payload.get("content", "")
                except Exception:
                    pass

        # At the end of the stream, save the messages into database
        db_save = SessionLocal()
        try:
            # Re-fetch session
            db_session = db_save.query(ChatSession).filter(ChatSession.id == session_id).first()
            if db_session:
                # 1. Save user question
                user_msg = ChatMessage(
                    session_id=session_id,
                    sender="user",
                    content=query
                )
                db_save.add(user_msg)
                
                # 2. Save assistant answer
                sources_str = json.dumps(sources_list, ensure_ascii=False) if sources_list else None
                assistant_msg = ChatMessage(
                    session_id=session_id,
                    sender="assistant",
                    content=final_response or "对不起，未生成有效答案。",
                    sources=sources_str
                )
                db_save.add(assistant_msg)
                
                # 3. Update session title if it was default
                if db_session.title in ["新会话", "New Chat"] or len(db_session.title) <= 3:
                    # Use the first few chars of user's query as the new session title
                    db_session.title = query[:20] + ("..." if len(query) > 20 else "")
                
                db_session.updated_at = db_save.query(func.now()).scalar() if hasattr(func, 'now') else datetime.utcnow()
                db_save.commit()
        except Exception as e:
            print(f"Error saving chat history to DB: {e}")
        finally:
            db_save.close()

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
