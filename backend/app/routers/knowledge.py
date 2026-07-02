import os
import shutil
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import KnowledgeDocument
from backend.app.schemas import KnowledgeDocumentOut
from backend.app.auth import get_current_admin
from backend.app.rag.document_loader import load_and_split_document
from backend.app.rag.pipeline import get_rag_pipeline

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])

# Upload directory
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"

@router.post("/upload", response_model=KnowledgeDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    # Check if duplicate filename
    existing = db.query(KnowledgeDocument).filter(KnowledgeDocument.filename == file.filename).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件 '{file.filename}' 已存在，请删除后再重新上传。"
        )

    # Save uploaded file temporarily
    temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size_bytes = os.path.getsize(temp_file_path)
        file_size_str = format_file_size(file_size_bytes)
        
        # 1. Generate document ID first
        import uuid
        document_id = str(uuid.uuid4())
        
        # 2. Parse and chunk document
        try:
            lc_docs = load_and_split_document(temp_file_path, file.filename, document_id)
        except ValueError as val_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(val_err)
            )
            
        if not lc_docs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未能解析到任何有效文本内容，请检查文件是否为空或格式不正确。"
            )
            
        # 3. Add to Chroma vector database
        rag = get_rag_pipeline()
        rag.add_documents(lc_docs)
        
        # 4. Save to SQLAlchemy DB
        db_doc = KnowledgeDocument(
            id=document_id,
            filename=file.filename,
            file_size=file_size_str,
            chunk_count=len(lc_docs)
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        return db_doc
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传处理失败: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.get("/documents", response_model=List[KnowledgeDocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    return db.query(KnowledgeDocument).order_by(KnowledgeDocument.uploaded_at.desc()).all()

@router.delete("/documents/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到指定的文档"
        )
        
    # 1. Delete from Chroma vector database
    rag = get_rag_pipeline()
    delete_success = rag.delete_document(document_id)
    
    # 2. Delete from relational database
    db.delete(doc)
    db.commit()
    
    return {"message": "文档已成功从知识库及向量库中删除。"}
