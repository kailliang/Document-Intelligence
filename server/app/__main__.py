from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from app.internal.ai import AI, get_ai
from app.internal.data import DOCUMENT_1, DOCUMENT_2
from app.internal.db import Base, SessionLocal, engine, get_db

import app.models as models
import app.schemas as schemas


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    应用生命周期管理 - 启动时初始化数据库和种子数据
    
    为什么要修改种子数据初始化？
    - 现在需要创建Document和DocumentVersion两张表的数据
    - 需要正确设置文档和版本之间的关系
    """
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Insert seed data with versioning support
    with SessionLocal() as db:
        # 检查是否已经初始化过数据（避免重复初始化）
        existing_doc = db.scalar(select(models.Document).where(models.Document.id == 1))
        if not existing_doc:
            # 创建第一个文档
            doc1 = models.Document(
                id=1,
                title="无线光遗传学设备",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(doc1)
            db.flush()  # 确保doc1有ID
            
            # 为第一个文档创建初始版本
            version1 = models.DocumentVersion(
                document_id=doc1.id,
                version_number=1,
                content=DOCUMENT_1,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(version1)
            db.flush()  # 确保version1有ID
            
            # 设置文档的当前版本
            doc1.current_version_id = version1.id
            
            # 创建第二个文档
            doc2 = models.Document(
                id=2,
                title="微流控血液充氧设备",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(doc2)
            db.flush()
            
            # 为第二个文档创建初始版本
            version2 = models.DocumentVersion(
                document_id=doc2.id,
                version_number=1,
                content=DOCUMENT_2,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(version2)
            db.flush()
            
            # 设置文档的当前版本
            doc2.current_version_id = version2.id
            
            db.commit()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================================================================
# 保持向后兼容的旧API端点
# ===================================================================

@app.get("/document/{document_id}")
def get_document(
    document_id: int, db: Session = Depends(get_db)
) -> schemas.DocumentWithCurrentVersion:
    """
    获取文档及其当前版本内容（向后兼容）
    
    为什么保留这个端点？
    - 前端目前使用这个端点获取文档
    - 保持向后兼容，避免破坏现有功能
    - 现在返回当前版本的内容而不是直接的content字段
    """
    # 查询文档及其当前版本
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 获取当前版本
    current_version = None
    if document.current_version_id:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.id == document.current_version_id)
        )
    
    # 如果没有当前版本，获取最新版本
    if not current_version:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.document_id == document_id)
            .order_by(models.DocumentVersion.version_number.desc())
        )
    
    if not current_version:
        raise HTTPException(status_code=404, detail="No version found for document")
    
    return schemas.DocumentWithCurrentVersion(
        id=document.id,
        title=document.title,
        content=current_version.content,
        version_number=current_version.version_number,
        last_modified=current_version.created_at
    )


@app.post("/save/{document_id}")
def save(
    document_id: int, request: schemas.CreateVersionRequest, db: Session = Depends(get_db)
):
    """
    保存文档内容（向后兼容）
    
    为什么修改这个端点？
    - 现在需要更新版本表而不是直接更新文档表
    - 保存时更新当前激活版本的内容
    - 不创建新版本，只更新现有版本
    
    修复变量名冲突：
    - 参数名从 document 改为 request，避免与数据库对象冲突
    """
    # 查找文档
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 查找当前激活版本
    current_version = None
    if document.current_version_id:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.id == document.current_version_id)
        )
    
    # 如果没有当前版本，获取最新版本
    if not current_version:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.document_id == document_id)
            .order_by(models.DocumentVersion.version_number.desc())
        )
    
    if not current_version:
        raise HTTPException(status_code=404, detail="No version found for document")
    
    # 更新版本内容
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.id == current_version.id)
        .values(content=request.content)
    )
    
    # 更新文档的updated_at时间戳
    db.execute(
        update(models.Document)
        .where(models.Document.id == document_id)
        .values(updated_at=datetime.utcnow())
    )
    
    db.commit()
    return {"document_id": document_id, "version_number": current_version.version_number, "content": request.content}


# ===================================================================
# 新的版本管理API端点
# ===================================================================

@app.get("/api/documents/{document_id}")
def get_document_with_versions(
    document_id: int, db: Session = Depends(get_db)
) -> schemas.DocumentRead:
    """
    获取文档及其所有版本历史
    
    这个端点专门用于版本管理功能：
    - 返回文档的完整信息
    - 包含所有版本的列表
    - 标明当前激活的版本
    """
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 获取所有版本（按版本号排序）
    versions = db.scalars(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number.desc())
    ).all()
    
    # 获取当前版本
    current_version = None
    if document.current_version_id:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.id == document.current_version_id)
        )
    
    return schemas.DocumentRead(
        id=document.id,
        title=document.title,
        current_version_id=document.current_version_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[schemas.DocumentVersionRead.model_validate(v) for v in versions],
        current_version=schemas.DocumentVersionRead.model_validate(current_version) if current_version else None
    )


@app.post("/api/documents/{document_id}/versions")
def create_version(
    document_id: int, 
    request: schemas.CreateVersionRequest, 
    db: Session = Depends(get_db)
) -> schemas.DocumentVersionRead:
    """
    为文档创建新版本
    
    创建新版本的逻辑：
    1. 查找文档
    2. 计算新版本号（最大版本号+1）
    3. 将所有现有版本设为非激活
    4. 创建新版本并设为激活
    5. 更新文档的当前版本指针
    """
    # 查找文档
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 获取最大版本号
    max_version = db.scalar(
        select(models.DocumentVersion.version_number)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number.desc())
    ) or 0
    
    new_version_number = max_version + 1
    
    # 将所有现有版本设为非激活
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .values(is_active=False)
    )
    
    # 创建新版本
    new_version = models.DocumentVersion(
        document_id=document_id,
        version_number=new_version_number,
        content=request.content,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(new_version)
    db.flush()  # 获取新版本的ID
    
    # 更新文档的当前版本指针
    db.execute(
        update(models.Document)
        .where(models.Document.id == document_id)
        .values(
            current_version_id=new_version.id,
            updated_at=datetime.utcnow()
        )
    )
    
    db.commit()
    db.refresh(new_version)
    
    return schemas.DocumentVersionRead.model_validate(new_version)


@app.post("/api/documents/{document_id}/switch-version")
def switch_version(
    document_id: int,
    request: schemas.SwitchVersionRequest,
    db: Session = Depends(get_db)
) -> schemas.DocumentWithCurrentVersion:
    """
    切换到指定版本
    
    切换版本的逻辑：
    1. 验证文档和版本存在
    2. 将所有版本设为非激活
    3. 激活指定版本
    4. 更新文档的当前版本指针
    5. 返回切换后的文档信息
    """
    # 查找文档
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 查找指定版本
    target_version = db.scalar(
        select(models.DocumentVersion)
        .where(
            models.DocumentVersion.document_id == document_id,
            models.DocumentVersion.version_number == request.version_number
        )
    )
    
    if not target_version:
        raise HTTPException(status_code=404, detail=f"Version {request.version_number} not found")
    
    # 将所有版本设为非激活
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .values(is_active=False)
    )
    
    # 激活目标版本
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.id == target_version.id)
        .values(is_active=True)
    )
    
    # 更新文档的当前版本指针
    db.execute(
        update(models.Document)
        .where(models.Document.id == document_id)
        .values(
            current_version_id=target_version.id,
            updated_at=datetime.utcnow()
        )
    )
    
    db.commit()
    
    return schemas.DocumentWithCurrentVersion(
        id=document.id,
        title=document.title,
        content=target_version.content,
        version_number=target_version.version_number,
        last_modified=target_version.created_at
    )


@app.get("/api/documents/{document_id}/versions")
def get_versions(
    document_id: int, db: Session = Depends(get_db)
) -> list[schemas.DocumentVersionRead]:
    """
    获取文档的所有版本列表
    
    这个端点专门用于版本历史显示：
    - 只返回版本信息，不包含文档信息
    - 按版本号降序排序（最新版本在前）
    """
    # 验证文档存在
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 获取所有版本
    versions = db.scalars(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number.desc())
    ).all()
    
    return [schemas.DocumentVersionRead.model_validate(v) for v in versions]


@app.websocket("/ws")
async def websocket(websocket: WebSocket, ai: AI = Depends(get_ai)):
    await websocket.accept()
    while True:
        try:
            """
            The AI doesn't expect to receive any HTML.
            You can call ai.review_document to receive suggestions from the LLM.
            Remember, the output from the LLM will not be deterministic, so you may want to validate the output before sending it to the client.
            """
            document = await websocket.receive_text()
            print("Received data via websocket")
        except WebSocketDisconnect:
            break
        except Exception as e:
            print(f"Error occurred: {e}")
            continue
