from __future__ import annotations

import os
import json
from typing import AsyncGenerator, Dict, Any, List

from dotenv import load_dotenv
from openai import AsyncOpenAI

import logging

from app.internal.prompt_enhanced import ENHANCED_PROMPT, FUNCTION_TOOLS
from app.internal.patent_chat_prompt import format_patent_chat_prompt
from app.internal.text_utils import html_to_plain_text

logger = logging.getLogger(__name__)

load_dotenv(override=True)  # Force override of environment variables

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
        logger.info(f"📄 Starting enhanced AI analysis, document length: {len(document)}")
        logger.info(f"📄 Document content preview: {document[:200]}...")
        
        # Use Function Calling for analysis
        stream = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.1,  # Low temperature ensures output stability and Function Calling reliability
            messages=[
                {"role": "system", "content": ENHANCED_PROMPT},
                {"role": "user", "content": document},
            ],
            tools=FUNCTION_TOOLS,
            tool_choice="auto",  # Let AI automatically decide how many function calls to make, not forced single call
            stream=True,
        )

        # Collect function calls
        function_calls = []
        current_function_calls = {}  # Use dictionary to track multiple parallel function calls
        
        logger.info("🔄 Starting AI streaming response processing...")
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Log regular text content (for debugging)
            if delta.content:
                logger.debug(f"📝 AI text response: {delta.content}")
            
            # Process tool calls
            if delta.tool_calls:
                logger.info(f"🔧 Received tool call: {delta.tool_calls}")
                for tool_call in delta.tool_calls:
                    call_index = tool_call.index
                    
                    if tool_call.function.name:
                        # New function call starts
                        if call_index in current_function_calls:
                            # If this index already has function call, save previous one first
                            function_calls.append(current_function_calls[call_index])
                        
                        current_function_calls[call_index] = {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or ""
                        }
                        logger.info(f"🆕 New function call {call_index}: {tool_call.function.name}")
                        
                    elif call_index in current_function_calls:
                        # Continue accumulating arguments for this index
                        current_function_calls[call_index]["arguments"] += tool_call.function.arguments or ""
        
        # Add all remaining function calls
        for call_index, func_call in current_function_calls.items():
            function_calls.append(func_call)
        
        logger.info(f"📊 Collected {len(function_calls)} function calls")
        for i, call in enumerate(function_calls):
            logger.info(f"🔧 Function call {i+1}: {call['name']}")
            logger.debug(f"🔧 Arguments: {call['arguments'][:200]}...")
        
        # Process and generate response - use dictionary for deduplication and merging
        suggestions_dict = {}  # key: originalText, value: merged suggestion
        diagram_insertions = []
        duplicate_count = 0  # Count duplicate suggestions
        
        for func_call in function_calls:
            if func_call["name"] == "create_suggestion":
                try:
                    args = json.loads(func_call["arguments"])
                    logger.info(f"✅ Function arguments parsing successful: {args}")
                    
                    # Handle new format: one text segment may have multiple issues
                    text_issues = args.get("issues", [])
                    
                    # If old format (backward compatible)
                    if not text_issues and args.get("type"):
                        text_issues = [{
                            "type": args.get("type", ""),
                            "severity": args.get("severity", "medium"),
                            "description": args.get("description", "")
                        }]
                    
                    # Create or merge suggestions
                    if text_issues:
                        original_text = args.get("originalText", "").strip()
                        
                        if original_text in suggestions_dict:
                            # Found duplicate suggestion, merge
                            duplicate_count += 1
                            existing_suggestion = suggestions_dict[original_text]
                            logger.info(f"🔄 Found duplicate suggestion, merging into existing: '{original_text[:50]}...'")
                            
                            # Merge issues arrays
                            existing_suggestion["issues"].extend(text_issues)
                            
                            # Recalculate merged type, description and severity
                            all_issues = existing_suggestion["issues"]
                            types = [issue.get("type", "") for issue in all_issues]
                            descriptions = [issue.get("description", "") for issue in all_issues]
                            severities = [issue.get("severity", "medium") for issue in all_issues]
                            
                            # Deduplicate type and description
                            unique_types = list(dict.fromkeys(types))  # Maintain order during deduplication
                            unique_descriptions = list(dict.fromkeys(descriptions))
                            
                            # Select highest severity
                            severity_order = {"high": 3, "medium": 2, "low": 1}
                            max_severity = max(severities, key=lambda x: severity_order.get(x, 2))
                            
                            # Update merged suggestion
                            existing_suggestion.update({
                                "type": " & ".join(unique_types),
                                "severity": max_severity,
                                "description": " | ".join(unique_descriptions),
                            })
                            
                            # If new suggestion has better replaceTo, could consider updating (keep first one here)
                            logger.info(f"📝 Merge complete, total {len(all_issues)} issues")
                            
                        else:
                            # New suggestion, add directly
                            types = [issue.get("type", "") for issue in text_issues]
                            descriptions = [issue.get("description", "") for issue in text_issues]
                            severities = [issue.get("severity", "medium") for issue in text_issues]
                            
                            # Select highest severity
                            severity_order = {"high": 3, "medium": 2, "low": 1}
                            max_severity = max(severities, key=lambda x: severity_order.get(x, 2))
                            
                            # Create new suggestion
                            suggestion = {
                                "type": " & ".join(types),  # Merge all issue types
                                "severity": max_severity,
                                "paragraph": args.get("paragraph", 1),
                                "description": " | ".join(descriptions),  # Merge all descriptions
                                "text": original_text,  # Mapping field
                                "suggestion": args.get("replaceTo", ""),  # Mapping field
                                "originalText": original_text,
                                "replaceTo": args.get("replaceTo", ""),
                                "issues": text_issues.copy()  # Retain detailed issues array for UI use
                            }
                            suggestions_dict[original_text] = suggestion
                            logger.info(f"📝 Adding new suggestion: {suggestion['type']} - contains {len(text_issues)} issues")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON parsing failed: {e}")
                    logger.error(f"❌ Original arguments: {func_call['arguments']}")
                    continue
                    
            elif func_call["name"] == "insert_diagram":
                try:
                    args = json.loads(func_call["arguments"])
                    logger.info(f"📊 Parsing diagram insertion request: {args}")
                    
                    diagram_insertion = {
                        "insert_after_text": args.get("insert_after_text", ""),
                        "mermaid_syntax": args.get("mermaid_syntax", ""),
                        "diagram_type": args.get("diagram_type", "flowchart"),
                        "title": args.get("title", "")
                    }
                    diagram_insertions.append(diagram_insertion)
                    logger.info(f"📊 Adding diagram insertion: after '{args.get('insert_after_text', '')[:50]}...'")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Diagram insertion JSON parsing failed: {e}")
                    logger.error(f"❌ Original arguments: {func_call['arguments']}")
                    continue
        
        # Convert dictionary to list
        issues = list(suggestions_dict.values())
        
        # Log deduplication statistics
        total_suggestions = len([call for call in function_calls if call["name"] == "create_suggestion"])
        final_suggestions = len(issues)
        logger.info(f"📊 Suggestion deduplication statistics: original {total_suggestions} suggestions, {final_suggestions} after merging")
        if duplicate_count > 0:
            logger.info(f"🔄 Found and merged {duplicate_count} duplicate suggestions, saved {duplicate_count} duplicate suggestion cards")
        
        logger.info(f"✨ Finally generated {len(issues)} suggestions and {len(diagram_insertions)} diagram insertions")
        
        # Generate JSON response
        response = {
            "issues": issues,
            "diagram_insertions": diagram_insertions
        }
        response_json = json.dumps(response, ensure_ascii=False)
        logger.info(f"📤 Returning response: {response_json[:200]}...")
        yield response_json

    async def chat_with_user(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str | None, None]:
        """
        Chat functionality, supports Function Calling
        
        Arguments:
        messages -- Chat history message list
        
        Response:
        Streaming AI response
        """
        stream = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.2,  # Slightly higher temperature for chat, maintain some creativity
            messages=messages,
            tools=FUNCTION_TOOLS,
            tool_choice="auto",
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Handle regular text response
            if delta.content:
                yield delta.content
            
            # Handle tool calls
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if tool_call.function.name == "create_diagram":
                        # Handle diagram generation
                        try:
                            args = json.loads(tool_call.function.arguments)
                            diagram_response = {
                                "type": "diagram",
                                "data": args
                            }
                            yield f"\n```mermaid\n{args.get('mermaid_syntax', '')}\n```\n"
                        except json.JSONDecodeError:
                            continue

    async def chat_with_document_context(self, messages: List[Dict[str, str]], document_content: str = "") -> AsyncGenerator[str | None, None]:
        """
        Chat functionality with document context, supports diagram insertion
        
        Arguments:
        messages -- Chat history message list
        document_content -- Current document content (HTML format)
        
        Response:
        Streaming AI response, including possible diagram insertion instructions
        """
        # Convert HTML document content to plain text
        plain_text_content = ""
        if document_content.strip():
            plain_text_content = html_to_plain_text(document_content)
            logger.info(f"📄 Document content length: {len(plain_text_content)}")

        # Build enhanced message list, including system prompts and document context
        enhanced_messages = []
        
        if messages and len(messages) > 0:
            last_user_message = messages[-1].get("content", "")
            
            # Create patent assistant system prompt
            system_prompt = format_patent_chat_prompt(plain_text_content, last_user_message)
            enhanced_messages.append({
                "role": "system",
                "content": system_prompt
            })
            
            # Add user message history (exclude last one, as it's already handled in system prompt)
            enhanced_messages.extend(messages[:-1])
            
            # Add current user message
            enhanced_messages.append({
                "role": "user", 
                "content": last_user_message
            })
        else:
            enhanced_messages = messages

        logger.info(f"🤖 Starting AI chat with document context, message count: {len(enhanced_messages)}")

        # Use Function Calling for chat
        stream = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=enhanced_messages,
            tools=FUNCTION_TOOLS,
            tool_choice="auto",
            stream=True,
        )
        
        # Process streaming response and function calls
        function_calls = []
        current_function_calls = {}
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Handle regular text response
            if delta.content:
                yield delta.content
            
            # Process function calls
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    call_index = tool_call.index
                    
                    if tool_call.function.name:
                        # New function call starts
                        if call_index in current_function_calls:
                            function_calls.append(current_function_calls[call_index])
                        
                        current_function_calls[call_index] = {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or ""
                        }
                        
                    elif call_index in current_function_calls:
                        # Continue accumulating arguments
                        current_function_calls[call_index]["arguments"] += tool_call.function.arguments or ""
        
        # Process all collected function calls
        for call_index, func_call in current_function_calls.items():
            function_calls.append(func_call)
        
        # Process function call results
        for func_call in function_calls:
            if func_call["name"] == "create_diagram":
                # Display diagram in chat
                try:
                    args = json.loads(func_call["arguments"])
                    yield f"\n```mermaid\n{args.get('mermaid_syntax', '')}\n```\n"
                except json.JSONDecodeError:
                    continue
                    
            elif func_call["name"] == "insert_diagram":
                # Insert diagram into document AND display in chat
                try:
                    args = json.loads(func_call["arguments"])
                    logger.info(f"📊 AI requests diagram insertion: {args}")
                    
                    # First, display the diagram in chat for user to see
                    mermaid_syntax = args.get('mermaid_syntax', '')
                    title = args.get('title', '')
                    if mermaid_syntax:
                        if title:
                            yield f"\n**{title}**\n\n"
                        yield f"\n```mermaid\n{mermaid_syntax}\n```\n"
                    
                    # Then, send diagram insertion instruction for document
                    insert_command = json.dumps({
                        "insert_after_text": args.get("insert_after_text", ""),
                        "mermaid_syntax": mermaid_syntax,
                        "diagram_type": args.get("diagram_type", "flowchart"),
                        "title": title
                    })
                    yield f"DIAGRAM_INSERT:{insert_command}"
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Diagram insertion parameter parsing failed: {e}")
                    continue