"""
Google Gemini AI provider implementation for patent review system
"""

import os
import json
import logging
from typing import AsyncGenerator, Dict, List, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.internal.ai_base import AIProvider
from app.internal.prompt_enhanced import ENHANCED_PROMPT, FUNCTION_TOOLS
from app.internal.patent_chat_prompt import format_patent_chat_prompt
from app.internal.text_utils import html_to_plain_text

logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    """Gemini AI provider implementation"""
    
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        
        # Safety settings to allow patent review content
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        logger.info(f"Initialized Gemini provider with model: {model}")
    
    def _convert_openai_tools_to_gemini(self, openai_tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI function tools format to Gemini format"""
        gemini_functions = []
        
        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool["function"]
                # Convert OpenAI schema to Gemini schema
                gemini_function = {
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {})
                }
                gemini_functions.append(gemini_function)
        
        return gemini_functions
    
    def _convert_gemini_function_call_to_openai_format(self, function_call) -> Dict:
        """Convert Gemini function call to OpenAI format for compatibility"""
        return {
            "name": function_call.name,
            "arguments": json.dumps(function_call.args)
        }
    
    async def review_document_with_functions(self, document: str) -> AsyncGenerator[str | None, None]:
        """
        Review patent document using Gemini's Function Calling
        """
        logger.info(f"Starting Gemini AI analysis, document length: {len(document)}")
        
        try:
            # Convert OpenAI tools to Gemini format
            gemini_functions = self._convert_openai_tools_to_gemini(FUNCTION_TOOLS)
            
            # Create the model with function declarations
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                },
                safety_settings=self.safety_settings,
                tools=gemini_functions
            )
            
            # Build the prompt
            messages = [
                {"role": "user", "parts": [ENHANCED_PROMPT]},
                {"role": "model", "parts": ["I understand. I will review the patent document and identify issues according to the rules provided."]},
                {"role": "user", "parts": [document]}
            ]
            
            # Start chat session for function calling
            chat = model.start_chat(history=messages[:-1])
            
            # Send the document for analysis
            response = await chat.send_message_async(
                messages[-1]["parts"][0],
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_output_tokens": 8192,
                }
            )
            
            # Process function calls
            function_calls = []
            
            # Extract function calls from response
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call'):
                                func_call = self._convert_gemini_function_call_to_openai_format(part.function_call)
                                function_calls.append(func_call)
                                logger.info(f"Gemini function call: {func_call['name']}")
            
            # Process function calls similar to OpenAI implementation
            suggestions_dict = {}
            diagram_insertions = []
            
            for func_call in function_calls:
                if func_call["name"] == "create_suggestion":
                    try:
                        args = json.loads(func_call["arguments"])
                        logger.info(f"Processing suggestion: {args}")
                        
                        # Handle suggestion similar to OpenAI implementation
                        text_issues = args.get("issues", [])
                        
                        # If old format (backward compatible)
                        if not text_issues and args.get("type"):
                            text_issues = [{
                                "type": args.get("type", ""),
                                "severity": args.get("severity", "medium"),
                                "description": args.get("description", "")
                            }]
                        
                        if text_issues:
                            original_text = args.get("originalText", "").strip()
                            
                            if original_text in suggestions_dict:
                                # Merge duplicate suggestions
                                existing_suggestion = suggestions_dict[original_text]
                                existing_suggestion["issues"].extend(text_issues)
                                
                                # Recalculate merged fields
                                all_issues = existing_suggestion["issues"]
                                types = [issue.get("type", "") for issue in all_issues]
                                descriptions = [issue.get("description", "") for issue in all_issues]
                                severities = [issue.get("severity", "medium") for issue in all_issues]
                                
                                # Deduplicate and merge
                                unique_types = list(dict.fromkeys(types))
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
                            else:
                                # Create new suggestion
                                types = [issue.get("type", "") for issue in text_issues]
                                descriptions = [issue.get("description", "") for issue in text_issues]
                                severities = [issue.get("severity", "medium") for issue in text_issues]
                                
                                severity_order = {"high": 3, "medium": 2, "low": 1}
                                max_severity = max(severities, key=lambda x: severity_order.get(x, 2))
                                
                                suggestion = {
                                    "type": " & ".join(types),
                                    "severity": max_severity,
                                    "paragraph": args.get("paragraph", 1),
                                    "description": " | ".join(descriptions),
                                    "text": original_text,
                                    "suggestion": args.get("replaceTo", ""),
                                    "originalText": original_text,
                                    "replaceTo": args.get("replaceTo", ""),
                                    "issues": text_issues.copy(),
                                    "confidence": args.get("confidence", 0.75),
                                    "confidence_factors": {
                                        "text_length": len(original_text),
                                        "issue_type": " & ".join(types),
                                        "has_detailed_replacement": bool(args.get("replaceTo", "").strip())
                                    }
                                }
                                suggestions_dict[original_text] = suggestion
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parsing failed: {e}")
                        continue
                        
                elif func_call["name"] == "insert_diagram":
                    try:
                        args = json.loads(func_call["arguments"])
                        diagram_insertion = {
                            "insert_after_text": args.get("insert_after_text", ""),
                            "mermaid_syntax": args.get("mermaid_syntax", ""),
                            "diagram_type": args.get("diagram_type", "flowchart"),
                            "title": args.get("title", "")
                        }
                        diagram_insertions.append(diagram_insertion)
                    except json.JSONDecodeError as e:
                        logger.error(f"Diagram JSON parsing failed: {e}")
            
            # Convert to list and return
            issues = list(suggestions_dict.values())
            logger.info(f"Gemini generated {len(issues)} suggestions")
            
            response = {
                "issues": issues,
                "diagram_insertions": diagram_insertions
            }
            
            yield json.dumps(response, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Gemini document review error: {e}")
            # Return empty result on error
            yield json.dumps({"issues": [], "diagram_insertions": []})
    
    async def chat_with_user(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str | None, None]:
        """
        Chat functionality using Gemini
        """
        try:
            # Create model for chat
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                },
                safety_settings=self.safety_settings
            )
            
            # Convert messages to Gemini format
            gemini_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_messages.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
            
            # Start chat
            chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            
            # Send message and stream response
            response = await chat.send_message_async(
                gemini_messages[-1]["parts"][0] if gemini_messages else "",
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            yield f"I apologize, but I encountered an error: {str(e)}"
    
    async def chat_with_document_context(self, messages: List[Dict[str, str]], document_content: str = "") -> AsyncGenerator[str | None, None]:
        """
        Chat with document context using Gemini
        """
        try:
            # Convert HTML to plain text if provided
            plain_text_content = ""
            if document_content.strip():
                plain_text_content = html_to_plain_text(document_content)
                logger.info(f"Document content length: {len(plain_text_content)}")
            
            # Build enhanced messages with document context
            enhanced_messages = []
            
            if messages and len(messages) > 0:
                last_user_message = messages[-1].get("content", "")
                
                # Create patent assistant system prompt
                system_prompt = format_patent_chat_prompt(plain_text_content, last_user_message)
                
                # For Gemini, we'll include the system prompt as the first user message
                enhanced_messages.append({
                    "role": "user",
                    "content": system_prompt
                })
                enhanced_messages.append({
                    "role": "assistant",
                    "content": "I understand. I'm ready to help with your patent document."
                })
                
                # Add message history (exclude last one)
                enhanced_messages.extend(messages[:-1])
                
                # Add current user message
                enhanced_messages.append({
                    "role": "user",
                    "content": last_user_message
                })
            else:
                enhanced_messages = messages
            
            # Convert tools for function calling
            gemini_functions = self._convert_openai_tools_to_gemini(FUNCTION_TOOLS)
            
            # Create model with functions
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                },
                safety_settings=self.safety_settings,
                tools=gemini_functions
            )
            
            # Convert messages to Gemini format
            gemini_messages = []
            for msg in enhanced_messages:
                role = "user" if msg["role"] in ["user", "system"] else "model"
                gemini_messages.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
            
            # Start chat session
            chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            
            # Send message
            response = await chat.send_message_async(
                gemini_messages[-1]["parts"][0] if gemini_messages else "",
                stream=True
            )
            
            # Process streaming response
            function_calls = []
            
            async for chunk in response:
                # Handle text response
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text
                
                # Handle function calls
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'function_call'):
                                    func_call = self._convert_gemini_function_call_to_openai_format(part.function_call)
                                    function_calls.append(func_call)
            
            # Process function calls for diagrams
            for func_call in function_calls:
                if func_call["name"] == "create_diagram":
                    try:
                        args = json.loads(func_call["arguments"])
                        yield f"\n```mermaid\n{args.get('mermaid_syntax', '')}\n```\n"
                    except json.JSONDecodeError:
                        continue
                        
                elif func_call["name"] == "insert_diagram":
                    try:
                        args = json.loads(func_call["arguments"])
                        logger.info(f"Gemini requests diagram insertion: {args}")
                        
                        mermaid_syntax = args.get('mermaid_syntax', '')
                        title = args.get('title', '')
                        
                        if mermaid_syntax:
                            if title:
                                yield f"\n**{title}**\n\n"
                            yield f"\n```mermaid\n{mermaid_syntax}\n```\n"
                        
                        # Send diagram insertion instruction
                        insert_command = json.dumps({
                            "insert_after_text": args.get("insert_after_text", ""),
                            "mermaid_syntax": mermaid_syntax,
                            "diagram_type": args.get("diagram_type", "flowchart"),
                            "title": title
                        })
                        yield f"DIAGRAM_INSERT:{insert_command}"
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Diagram insertion parsing failed: {e}")
                        
        except Exception as e:
            logger.error(f"Gemini chat with context error: {e}")
            yield f"I apologize, but I encountered an error: {str(e)}"