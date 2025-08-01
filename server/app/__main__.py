from contextlib import asynccontextmanager
from datetime import datetime
import json
import logging

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import insert, select, update, func
from sqlalchemy.orm import Session

from app.internal.ai import AI, get_ai
from app.internal.data import DOCUMENT_1, DOCUMENT_2
from app.internal.db import Base, SessionLocal, engine, get_db
from app.internal.text_utils import html_to_plain_text, validate_text_for_ai, StreamingJSONParser

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    # 创建新版本（空文档）
    new_version = models.DocumentVersion(
        document_id=document_id,
        version_number=new_version_number,
        content="",  # 新版本从空文档开始
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


@app.delete("/api/documents/{document_id}/versions/{version_number}")
def delete_version(
    document_id: int,
    version_number: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    删除指定版本
    
    删除逻辑：
    1. 验证文档存在
    2. 检查是否至少有2个版本（不能删除最后一个版本）
    3. 验证要删除的版本存在
    4. 检查要删除的版本是否为当前激活版本
    5. 如果是激活版本，先切换到最新的其他版本
    6. 删除指定版本
    """
    # 查找文档
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 检查版本总数
    version_count = db.scalar(
        select(func.count(models.DocumentVersion.id))
        .where(models.DocumentVersion.document_id == document_id)
    )
    
    if version_count <= 1:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete the last remaining version"
        )
    
    # 查找要删除的版本
    target_version = db.scalar(
        select(models.DocumentVersion)
        .where(
            models.DocumentVersion.document_id == document_id,
            models.DocumentVersion.version_number == version_number
        )
    )
    
    if not target_version:
        raise HTTPException(
            status_code=404, 
            detail=f"Version {version_number} not found"
        )
    
    # 如果删除的是当前激活版本，需要先切换到其他版本
    if target_version.is_active:
        # 找到最新的其他版本
        alternative_version = db.scalar(
            select(models.DocumentVersion)
            .where(
                models.DocumentVersion.document_id == document_id,
                models.DocumentVersion.id != target_version.id
            )
            .order_by(models.DocumentVersion.version_number.desc())
        )
        
        if alternative_version:
            # 激活替代版本
            alternative_version.is_active = True
            # 更新文档的当前版本指针
            document.current_version_id = alternative_version.id
            document.updated_at = datetime.utcnow()
    
    # 删除目标版本
    db.delete(target_version)
    db.commit()
    
    return {"message": f"Version {version_number} deleted successfully"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点：实时AI建议系统
    
    工作流程：
    1. 接收来自前端的HTML内容
    2. 转换为纯文本格式
    3. 调用AI服务进行流式分析
    4. 解析AI响应的JSON数据
    5. 发送完整建议给前端
    
    消息格式：
    - 接收：HTML字符串 (来自TipTap编辑器)
    - 发送：JSON对象 {"type": "ai_suggestions", "data": {...}}
    """
    await websocket.accept()
    logger.info("WebSocket连接已建立")
    
    # 尝试初始化AI服务
    try:
        ai = get_ai()
        logger.info("✅ AI服务初始化成功")
        # 发送连接成功消息
        success_msg = {
            "type": "connection_success",
            "message": "AI服务已就绪",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(success_msg))
    except ValueError as e:
        logger.error(f"❌ AI服务初始化失败: {str(e)}")
        error_response = {
            "type": "server_error",
            "message": "AI服务未配置：请确保在 server/.env 文件中设置了 OPENAI_API_KEY",
            "details": str(e)
        }
        await websocket.send_text(json.dumps(error_response))
        await websocket.close()
        return
    except Exception as e:
        logger.error(f"❌ 未预期的AI初始化错误: {str(e)}")
        error_response = {
            "type": "server_error",
            "message": "AI服务初始化失败",
            "details": str(e)
        }
        await websocket.send_text(json.dumps(error_response))
        await websocket.close()
        return
    
    # 为每个连接创建JSON解析器
    json_parser = StreamingJSONParser()
    
    while True:
        try:
            # 接收HTML内容
            html_content = await websocket.receive_text()
            logger.info(f"接收到HTML内容，长度: {len(html_content)}")
            
            # 第一步：转换HTML为纯文本
            plain_text = html_to_plain_text(html_content)
            
            # 第二步：验证文本是否适合AI处理
            is_valid, error_message = validate_text_for_ai(plain_text)
            
            if not is_valid:
                # 发送验证错误给客户端
                error_response = {
                    "type": "validation_error",
                    "message": error_message,
                    "details": f"HTML长度: {len(html_content)}, 文本长度: {len(plain_text)}"
                }
                await websocket.send_text(json.dumps(error_response))
                logger.warning(f"文本验证失败: {error_message}")
                continue
            
            # 第三步：发送处理开始通知
            start_response = {
                "type": "processing_start",
                "message": "AI正在分析文档...",
                "text_length": len(plain_text)
            }
            await websocket.send_text(json.dumps(start_response))
            logger.info("开始AI分析...")
            
            # 第四步：重置JSON解析器为新的分析
            json_parser.reset()
            
            # 第五步：调用AI进行流式分析
            try:
                async for chunk in ai.review_document(plain_text):
                    if chunk:
                        # 尝试解析JSON块
                        parsed_result = json_parser.add_chunk(chunk)
                        
                        if parsed_result:
                            # 成功解析完整JSON，发送给客户端
                            success_response = {
                                "type": "ai_suggestions",
                                "data": parsed_result,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            await websocket.send_text(json.dumps(success_response))
                            logger.info(f"AI分析完成，发现 {len(parsed_result.get('issues', []))} 个问题")
                            break  # 完成一次分析
                            
                # 如果流结束但没有完整的JSON，尝试最后一次解析
                if json_parser.buffer:
                    logger.warning("AI流结束但JSON不完整，尝试最后解析...")
                    final_result = json_parser.add_chunk("")  # 触发最终解析尝试
                    if final_result:
                        success_response = {
                            "type": "ai_suggestions",
                            "data": final_result,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(success_response))
                        logger.info("最终解析成功")
                    else:
                        # 解析失败，发送错误
                        error_response = {
                            "type": "parsing_error",
                            "message": "AI响应解析失败",
                            "buffer_info": json_parser.get_buffer_info()
                        }
                        await websocket.send_text(json.dumps(error_response))
                        logger.error("AI响应解析最终失败")
                        
            except Exception as ai_error:
                # AI调用出错
                logger.error(f"AI服务错误: {ai_error}")
                error_response = {
                    "type": "ai_error", 
                    "message": f"AI服务出错: {str(ai_error)}",
                    "details": "请检查API密钥配置和网络连接"
                }
                await websocket.send_text(json.dumps(error_response))
                
        except WebSocketDisconnect:
            logger.info("客户端断开WebSocket连接")
            break
            
        except json.JSONEncodeError as json_error:
            logger.error(f"JSON编码错误: {json_error}")
            error_response = {
                "type": "json_error",
                "message": "服务器响应编码错误"
            }
            # 尝试发送简单错误消息
            try:
                await websocket.send_text('{"type":"error","message":"JSON encoding error"}')
            except:
                pass
                
        except Exception as e:
            logger.error(f"WebSocket处理错误: {e}")
            try:
                error_response = {
                    "type": "server_error",
                    "message": f"服务器内部错误: {str(e)}"
                }
                await websocket.send_text(json.dumps(error_response))
            except:
                # 如果连接已断开，忽略发送错误
                break


# 尝试导入增强版端点（如果可用）
try:
    from app.enhanced_endpoints import websocket_enhanced_endpoint, chat_with_ai, ChatRequest
    
    # 注册增强版WebSocket端点
    @app.websocket("/ws/enhanced")
    async def enhanced_websocket_route(websocket: WebSocket):
        await websocket_enhanced_endpoint(websocket)
    
    # 注册聊天API端点
    @app.post("/api/chat")
    async def chat_endpoint(request: ChatRequest):
        return await chat_with_ai(request)
    
    logger.info("✅ 增强版端点已注册")
except ImportError as e:
    logger.warning(f"⚠️ 增强版端点不可用: {e}")
