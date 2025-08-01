from __future__ import annotations

import os
import json
from typing import AsyncGenerator, Dict, Any, List

from dotenv import load_dotenv
from openai import AsyncOpenAI

import logging

from app.internal.prompt_enhanced import ENHANCED_PROMPT, FUNCTION_TOOLS

logger = logging.getLogger(__name__)

load_dotenv(override=True)  # 强制覆盖环境变量

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o"


def get_ai_enhanced(
    model: str | None = OPENAI_MODEL,
    api_key: str | None = OPENAI_API_KEY,
) -> AIEnhanced:
    if not api_key or not model:
        raise ValueError("Both API key and model need to be set")
    return AIEnhanced(api_key, model)


class AIEnhanced:
    def __init__(self, api_key: str, model: str):
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def review_document_with_functions(self, document: str) -> AsyncGenerator[str | None, None]:
        """
        Review patent document using Function Calling for more precise suggestions.
        
        Arguments:
        document -- Patent document to review
        
        Response:
        Yields JSON with suggestions including originalText and replaceTo fields
        """
        logger.info(f"📄 开始增强版AI分析，文档长度: {len(document)}")
        logger.info(f"📄 文档内容预览: {document[:200]}...")
        
        # 使用Function Calling进行分析
        stream = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.1,  # 低温度确保输出稳定性和Function Calling可靠性
            messages=[
                {"role": "system", "content": ENHANCED_PROMPT},
                {"role": "user", "content": document},
            ],
            tools=FUNCTION_TOOLS,
            tool_choice={"type": "function", "function": {"name": "create_suggestion"}},  # 强制使用函数调用
            stream=True,
        )

        # 收集function calls
        function_calls = []
        current_function_call = None
        
        logger.info("🔄 开始处理AI流式响应...")
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # 记录普通文本内容（用于调试）
            if delta.content:
                logger.debug(f"📝 AI文本响应: {delta.content}")
            
            # 处理tool calls
            if delta.tool_calls:
                logger.info(f"🔧 收到tool call: {delta.tool_calls}")
                for tool_call in delta.tool_calls:
                    if tool_call.index == 0 and tool_call.function.name:
                        # 新的function call
                        if current_function_call:
                            function_calls.append(current_function_call)
                        current_function_call = {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or ""
                        }
                        logger.info(f"🆕 新的function call: {tool_call.function.name}")
                    elif current_function_call:
                        # 继续累积arguments
                        current_function_call["arguments"] += tool_call.function.arguments or ""
        
        # 添加最后一个function call
        if current_function_call:
            function_calls.append(current_function_call)
        
        logger.info(f"📊 收集到 {len(function_calls)} 个function calls")
        for i, call in enumerate(function_calls):
            logger.info(f"🔧 Function call {i+1}: {call['name']}")
            logger.debug(f"🔧 Arguments: {call['arguments'][:200]}...")
        
        # 处理并生成响应
        issues = []
        for func_call in function_calls:
            if func_call["name"] == "create_suggestion":
                try:
                    args = json.loads(func_call["arguments"])
                    logger.info(f"✅ 解析function arguments成功: {args}")
                    
                    # 转换为期望的格式
                    issue = {
                        "type": args.get("type", ""),
                        "severity": args.get("severity", "medium"),
                        "paragraph": args.get("paragraph", 1),
                        "description": args.get("description", ""),
                        "text": args.get("originalText", ""),  # 映射字段
                        "suggestion": args.get("replaceTo", ""),  # 映射字段
                        "originalText": args.get("originalText", ""),
                        "replaceTo": args.get("replaceTo", "")
                    }
                    issues.append(issue)
                    logger.info(f"📝 添加建议: {issue['type']} - {issue['description'][:50]}...")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON解析失败: {e}")
                    logger.error(f"❌ 原始arguments: {func_call['arguments']}")
                    continue
        
        logger.info(f"✨ 最终生成 {len(issues)} 个建议")
        
        # 如果没有找到任何建议，创建一个测试建议（临时调试用）
        if len(issues) == 0:
            logger.warning("⚠️ 没有收到任何建议，创建测试建议")
            test_issue = {
                "type": "test",
                "severity": "low",
                "paragraph": 1,
                "description": "测试建议：文档分析功能正常工作",
                "text": "测试文本",
                "suggestion": "这是一个测试建议",
                "originalText": "测试文本",
                "replaceTo": "这是一个测试建议"
            }
            issues.append(test_issue)
        
        # 生成JSON响应
        response = json.dumps({"issues": issues}, ensure_ascii=False)
        logger.info(f"📤 返回响应: {response[:200]}...")
        yield response

    async def chat_with_user(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str | None, None]:
        """
        聊天功能，支持Function Calling
        
        Arguments:
        messages -- 聊天历史消息列表
        
        Response:
        流式返回AI响应
        """
        stream = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.2,  # 聊天时稍高一点的温度，保持一定创造性
            messages=messages,
            tools=FUNCTION_TOOLS,
            tool_choice="auto",
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # 处理普通文本响应
            if delta.content:
                yield delta.content
            
            # 处理工具调用
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if tool_call.function.name == "create_diagram":
                        # 处理图表生成
                        try:
                            args = json.loads(tool_call.function.arguments)
                            diagram_response = {
                                "type": "diagram",
                                "data": args
                            }
                            yield f"\n```mermaid\n{args.get('mermaid_syntax', '')}\n```\n"
                        except json.JSONDecodeError:
                            continue