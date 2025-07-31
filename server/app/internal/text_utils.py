"""
文本处理工具模块
用于处理HTML到纯文本的转换和其他文本相关操作

为什么需要这个模块？
- TipTap编辑器输出HTML格式内容
- AI服务只接受纯文本输入
- 需要保持文档的逻辑结构（段落、换行等）
"""

from bs4 import BeautifulSoup
import re
import logging
import json
from typing import Optional, Dict, Any

# 配置日志
logger = logging.getLogger(__name__)


def html_to_plain_text(html_content: str) -> str:
    """
    将HTML内容转换为AI可处理的纯文本
    
    转换过程：
    1. 使用BeautifulSoup解析HTML结构
    2. 保留段落结构（<p>标签转换为换行）
    3. 移除所有HTML标签
    4. 清理多余的空白字符
    
    Args:
        html_content (str): 来自TipTap编辑器的HTML内容
        
    Returns:
        str: 清理后的纯文本，保持逻辑结构
        
    Example:
        输入: "<p>第一段内容</p><p>第二段内容</p>"
        输出: "第一段内容\n\n第二段内容"
    """
    if not html_content or not html_content.strip():
        return ""
    
    try:
        # 使用BeautifulSoup解析HTML
        # html.parser是Python内置解析器，速度快且稳定
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 特殊处理：将段落标签转换为双换行符
        # 这样可以保持专利文档的段落结构
        for p_tag in soup.find_all('p'):
            p_tag.insert_after('\n\n')
        
        # 处理其他块级元素（div, h1-h6等）
        for block_tag in soup.find_all(['div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            block_tag.insert_after('\n')
        
        # 处理列表项
        for li_tag in soup.find_all('li'):
            li_tag.insert_before('- ')  # 添加列表标记
            li_tag.insert_after('\n')
        
        # 获取纯文本内容
        text = soup.get_text()
        
        # 清理文本：
        # 1. 移除HTML实体（&nbsp; 等）
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        
        # 2. 统一换行符（Windows/Mac/Linux兼容）
        text = re.sub(r'\r\n|\r', '\n', text)
        
        # 3. 清理多余的空白字符
        # 将多个连续的空格替换为单个空格
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 4. 清理多余的换行符
        # 最多保留两个连续换行符（段落分隔）
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 5. 移除首尾空白
        text = text.strip()
        
        logger.info(f"HTML转换完成：{len(html_content)} -> {len(text)} 字符")
        return text
        
    except Exception as e:
        logger.error(f"HTML转纯文本失败: {e}")
        # 降级处理：简单移除HTML标签
        return re.sub(r'<[^>]+>', '', html_content).strip()


def validate_text_for_ai(text: str) -> tuple[bool, str]:
    """
    验证文本是否适合AI处理
    
    检查项目：
    1. 文本长度是否合理
    2. 是否包含HTML标签（转换失败的标志）
    3. 是否为空或只有空白字符
    
    Args:
        text (str): 待验证的纯文本
        
    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    if not text or not text.strip():
        return False, "文本为空"
    
    # 检查是否仍包含HTML标签
    if re.search(r'<[^>]+>', text):
        return False, "文本仍包含HTML标签，转换可能失败"
    
    # 检查文本长度（AI有token限制）
    if len(text) > 10000:  # 约4000个token的限制
        return False, f"文本过长({len(text)}字符)，可能超出AI处理限制"
    
    if len(text) < 10:
        return False, "文本过短，可能不是有效的专利内容"
    
    return True, "文本有效"


def extract_claims_section(text: str) -> str:
    """
    从专利文档中提取Claims部分
    
    AI提示词专门针对专利Claims部分进行分析，
    因此我们只需要发送Claims部分给AI
    
    Args:
        text (str): 完整的专利文档文本
        
    Returns:
        str: Claims部分的文本，如果找不到则返回全文
    """
    # 查找Claims章节的开始
    claims_patterns = [
        r'(?i)claims?\s*:?\s*\n',  # "Claims:" or "Claim:"
        r'(?i)什么是声明\s*:?\s*\n',  # 中文
        r'(?i)权利要求\s*:?\s*\n',   # 中文专利术语
    ]
    
    for pattern in claims_patterns:
        match = re.search(pattern, text)
        if match:
            # 从Claims开始到文档结尾
            claims_text = text[match.start():]
            logger.info(f"找到Claims部分，长度: {len(claims_text)}")
            return claims_text
    
    # 如果找不到Claims部分，返回全文
    logger.warning("未找到Claims部分，使用全文")
    return text


# 测试函数
def test_html_conversion():
    """
    测试HTML转换功能的简单测试函数
    """
    test_cases = [
        # 简单段落
        ("<p>这是第一段</p><p>这是第二段</p>", "这是第一段\n\n这是第二段"),
        
        # 包含列表
        ("<ul><li>第一项</li><li>第二项</li></ul>", "- 第一项\n- 第二项"),
        
        # 复杂HTML
        ("<div><h1>标题</h1><p>内容<strong>加粗</strong>部分</p></div>", "标题\n内容加粗部分"),
    ]
    
    print("🧪 测试HTML转换功能...")
    for i, (html_input, expected) in enumerate(test_cases, 1):
        result = html_to_plain_text(html_input)
        success = result.strip() == expected.strip()
        print(f"测试 {i}: {'✅' if success else '❌'}")
        if not success:
            print(f"  期望: {repr(expected)}")
            print(f"  实际: {repr(result)}")


class StreamingJSONParser:
    """
    流式JSON解析器
    
    为什么需要这个类？
    - AI服务返回流式响应，JSON数据分多个块发送
    - 需要缓存不完整的JSON数据直到接收完整
    - 处理AI响应中可能出现的格式错误
    
    使用示例:
        parser = StreamingJSONParser()
        for chunk in ai_stream:
            result = parser.add_chunk(chunk)
            if result:
                # 处理完整的JSON对象
                handle_ai_suggestion(result)
    """
    
    def __init__(self):
        """初始化解析器"""
        self.buffer = ""  # 缓存未完成的JSON数据
        self.reset_count = 0  # 重置计数器，用于调试
    
    def add_chunk(self, chunk: str) -> Optional[Dict[Any, Any]]:
        """
        添加新的JSON数据块并尝试解析
        
        Args:
            chunk (str): 来自AI的JSON数据块
            
        Returns:
            Optional[Dict]: 解析成功返回JSON对象，否则返回None
        """
        if not chunk:
            return None
        
        # 将新块添加到缓冲区
        self.buffer += chunk
        
        # 尝试多种方式解析JSON
        return self._try_parse_json()
    
    def _try_parse_json(self) -> Optional[Dict[Any, Any]]:
        """
        尝试解析缓冲区中的JSON数据
        
        处理策略：
        1. 直接解析完整JSON
        2. 清理常见的格式问题
        3. 查找并提取可能的JSON对象
        """
        if not self.buffer.strip():
            return None
        
        # 策略1: 直接解析
        try:
            result = json.loads(self.buffer)
            self.buffer = ""  # 成功后清空缓冲区
            logger.info("JSON解析成功（直接解析）")
            return result
        except json.JSONDecodeError:
            pass
        
        # 策略2: 清理常见问题后解析
        cleaned_buffer = self._clean_json_buffer()
        if cleaned_buffer != self.buffer:
            try:
                result = json.loads(cleaned_buffer)
                self.buffer = ""
                logger.info("JSON解析成功（清理后解析）")
                return result
            except json.JSONDecodeError:
                pass
        
        # 策略3: 查找可能的完整JSON对象
        json_obj = self._extract_json_object()
        if json_obj:
            try:
                result = json.loads(json_obj)
                # 从缓冲区移除已解析的部分
                self.buffer = self.buffer[self.buffer.find(json_obj) + len(json_obj):]
                logger.info("JSON解析成功（提取对象）")
                return result
            except json.JSONDecodeError:
                pass
        
        # 如果缓冲区过大，重置防止内存问题
        if len(self.buffer) > 10000:
            logger.warning(f"缓冲区过大({len(self.buffer)})，重置解析器")
            self.reset()
        
        return None
    
    def _clean_json_buffer(self) -> str:
        """
        清理JSON缓冲区中的常见问题
        
        常见问题：
        - 多余的换行符和空格
        - AI添加的前缀文字
        - 不完整的转义字符
        """
        cleaned = self.buffer
        
        # 移除首尾空白
        cleaned = cleaned.strip()
        
        # 移除可能的AI前缀（如 "Here's the analysis:" 等）
        # 查找第一个 { 字符，从那里开始
        first_brace = cleaned.find('{')
        if first_brace > 0:
            cleaned = cleaned[first_brace:]
        
        # 统一换行符
        cleaned = re.sub(r'\r\n|\r', '\n', cleaned)
        
        # 移除JSON中的多余空白（但保留字符串内的空白）
        # 这个比较复杂，先简单处理
        cleaned = re.sub(r'\n\s*', '\n', cleaned)
        
        return cleaned
    
    def _extract_json_object(self) -> Optional[str]:
        """
        从缓冲区中提取可能的完整JSON对象
        
        使用括号计数法找到完整的JSON对象边界
        """
        cleaned = self._clean_json_buffer()
        
        # 查找第一个 { 字符
        start = cleaned.find('{')
        if start == -1:
            return None
        
        # 使用括号计数找到匹配的 }
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(cleaned[start:], start):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
                    # 找到匹配的结束括号
                    if brace_count == 0:
                        return cleaned[start:i+1]
        
        return None
    
    def reset(self):
        """重置解析器状态"""
        self.buffer = ""
        self.reset_count += 1
        logger.info(f"JSON解析器已重置 (第{self.reset_count}次)")
    
    def get_buffer_info(self) -> str:
        """获取缓冲区信息，用于调试"""
        return f"缓冲区长度: {len(self.buffer)}, 重置次数: {self.reset_count}"


def test_streaming_json_parser():
    """
    测试流式JSON解析器
    """
    print("\n🧪 测试流式JSON解析器...")
    parser = StreamingJSONParser()
    
    # 测试用例1: 分块发送完整JSON
    chunks = ['{"issues":', ' [{"type":', ' "grammar",', ' "severity": "high"}]}']
    print("测试1: 分块JSON解析")
    
    result = None
    for i, chunk in enumerate(chunks):
        print(f"  添加块 {i+1}: {chunk}")
        result = parser.add_chunk(chunk)
        if result:
            print(f"  ✅ 解析成功: {result}")
            break
    
    if not result:
        print("  ❌ 解析失败")
    
    # 测试用例2: 带前缀的JSON
    parser.reset()
    print("\n测试2: 带前缀的JSON")
    messy_json = 'Here is the analysis: {"issues": [{"type": "test"}]}'
    result = parser.add_chunk(messy_json)
    if result:
        print(f"  ✅ 解析成功: {result}")
    else:
        print("  ❌ 解析失败")
    
    # 测试用例3: 错误的JSON
    parser.reset()
    print("\n测试3: 错误的JSON处理")
    bad_json = '{"issues": [{"type": "test"'  # 不完整的JSON
    result = parser.add_chunk(bad_json)
    print(f"  缓冲状态: {parser.get_buffer_info()}")
    
    # 完成JSON
    result = parser.add_chunk('}]}')
    if result:
        print(f"  ✅ 最终解析成功: {result}")
    else:
        print("  ❌ 最终解析失败")


if __name__ == "__main__":
    # 运行测试
    test_html_conversion()
    test_streaming_json_parser()