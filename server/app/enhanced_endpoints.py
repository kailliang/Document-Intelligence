# Enhanced endpoints for the application

from datetime import datetime
import json
import logging
from typing import List, Dict

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.internal.ai_enhanced import get_ai_enhanced
from app.internal.text_utils import html_to_plain_text, validate_text_for_ai

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


async def websocket_enhanced_endpoint(websocket: WebSocket):
    """
    增强版WebSocket端点：支持Function Calling的AI建议系统
    
    特性：
    - 使用Function Calling获取更精确的文本匹配
    - 支持originalText和replaceTo字段
    - 更准确的建议内容
    """
    await websocket.accept()
    logger.info("Enhanced WebSocket连接已建立")
    
    # 尝试初始化增强版AI服务
    try:
        ai = get_ai_enhanced()
        logger.info("✅ Enhanced AI服务初始化成功")
        # 发送连接成功消息
        success_msg = {
            "type": "connection_success",
            "message": "Enhanced AI服务已就绪",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(success_msg))
    except ValueError as e:
        logger.error(f"Enhanced AI服务初始化失败: {e}")
        error_msg = {
            "type": "ai_error",
            "message": f"AI服务初始化失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_msg))
        await websocket.close()
        return
    
    try:
        while True:
            # 接收HTML内容
            html_content = await websocket.receive_text()
            logger.info(f"收到HTML内容，长度: {len(html_content)}")
            
            # 通知前端开始处理
            processing_msg = {
                "type": "processing_start",
                "message": "正在分析文档...",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(processing_msg))
            
            try:
                # HTML转换为纯文本
                plain_text = html_to_plain_text(html_content)
                logger.info(f"转换后纯文本长度: {len(plain_text)}")
                
                # 验证文本内容
                is_valid, error_message = validate_text_for_ai(plain_text)
                if not is_valid:
                    logger.warning(f"文本验证失败: {error_message}")
                    validation_error = {
                        "type": "validation_error",
                        "message": error_message,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(validation_error))
                    continue
                
                # 使用增强版AI分析（支持Function Calling）
                logger.info("开始增强版AI文档分析...")
                response_chunks = []
                
                async for chunk in ai.review_document_with_functions(plain_text):
                    if chunk:
                        response_chunks.append(chunk)
                
                # 合并所有响应
                full_response = "".join(response_chunks)
                
                try:
                    # 解析JSON响应
                    parsed_result = json.loads(full_response)
                    
                    # 发送完整的建议结果
                    success_response = {
                        "type": "ai_suggestions",
                        "data": parsed_result,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(success_response))
                    logger.info(f"Enhanced AI分析完成，发现 {len(parsed_result.get('issues', []))} 个问题")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                    error_response = {
                        "type": "parsing_error",
                        "message": "AI响应解析失败",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(error_response))
                    
            except Exception as e:
                logger.error(f"处理分析时出错: {e}")
                error_response = {
                    "type": "ai_error",
                    "message": f"AI分析失败: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_response))
                
    except WebSocketDisconnect:
        logger.info("Enhanced WebSocket连接已断开")
    except Exception as e:
        logger.error(f"Enhanced WebSocket处理错误: {e}")
        try:
            error_response = {
                "type": "server_error",
                "message": f"服务器内部错误: {str(e)}"
            }
            await websocket.send_text(json.dumps(error_response))
        except:
            pass


async def chat_with_ai(request: ChatRequest):
    """
    AI聊天功能端点
    
    支持与AI进行对话，包括：
    - 提问专利相关问题
    - 请求生成图表
    - 获取专利撰写建议
    """
    try:
        ai = get_ai_enhanced()
        
        # 构建消息历史
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # 获取AI响应
        response_chunks = []
        async for chunk in ai.chat_with_user(messages):
            if chunk:
                response_chunks.append(chunk)
        
        full_response = "".join(response_chunks)
        
        return {"response": full_response}
        
    except Exception as e:
        logger.error(f"聊天处理错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))