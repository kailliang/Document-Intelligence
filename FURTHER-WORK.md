# 面试准备指南 - Live Code Changes 预测

## 项目背景

这是一个专利审查系统的 take home project，是面试公司的核心业务。系统使用 WebSocket 实现实时 AI 分析，通过 OpenAI Function Calling 生成专利文档改进建议。

## 前端可能的 Live Code Changes

### 1. **AI 建议功能增强**（最可能）

#### a) 添加"批量接受所有建议"功能
```typescript
// 在 App.tsx 中添加一个按钮和功能
const acceptAllSuggestions = () => {
  appState.aiSuggestions.forEach(suggestion => {
    if (suggestion.originalText && suggestion.replaceTo) {
      // 调用编辑器的替换功能
      if (editorRef.current) {
        replaceText(editorRef.current, suggestion.originalText, suggestion.replaceTo);
      }
    }
  });
  
  // 清空建议列表
  setAppState(prev => ({
    ...prev,
    aiSuggestions: [],
    hasUnsavedChanges: true
  }));
};

// 在建议列表上方添加按钮
<div className="flex gap-2 mb-4">
  <button
    onClick={acceptAllSuggestions}
    disabled={appState.aiSuggestions.length === 0}
    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300"
  >
    ✅ Accept All ({appState.aiSuggestions.length})
  </button>
</div>
```

### 2. **实时协作功能**（展示WebSocket理解）

#### a) 添加"用户正在编辑"指示器
```typescript
// Document.tsx 中添加编辑状态广播
const [isTyping, setIsTyping] = useState(false);
const typingTimeoutRef = useRef<NodeJS.Timeout>();

const handleContentChange = (content: string) => {
  onContentChange(content);
  
  // 广播正在编辑状态
  if (!isTyping) {
    setIsTyping(true);
    sendMessage(JSON.stringify({ type: 'user_typing_start' }));
  }
  
  // 清除之前的定时器
  if (typingTimeoutRef.current) {
    clearTimeout(typingTimeoutRef.current);
  }
  
  // 3秒后停止编辑状态
  typingTimeoutRef.current = setTimeout(() => {
    setIsTyping(false);
    sendMessage(JSON.stringify({ type: 'user_typing_stop' }));
  }, 3000);
};
```

### 3. **性能优化**（展示技术能力）

#### a) 防抖优化
```typescript
import { debounce } from 'lodash';

// Document.tsx 中添加
const debouncedAnalysis = useMemo(
  () => debounce(triggerManualAnalysis, 1000),
  [triggerManualAnalysis]
);

// 替换直接调用
// triggerManualAnalysis() -> debouncedAnalysis()
```

#### b) 建议缓存
```typescript
// 添加缓存逻辑
const [analysisCache, setAnalysisCache] = useState<Map<string, AISuggestion[]>>(new Map());

const getCachedAnalysis = (content: string): AISuggestion[] | null => {
  const contentHash = btoa(content).slice(0, 32); // 简单哈希
  return analysisCache.get(contentHash) || null;
};

const setCachedAnalysis = (content: string, suggestions: AISuggestion[]) => {
  const contentHash = btoa(content).slice(0, 32);
  setAnalysisCache(prev => new Map(prev).set(contentHash, suggestions));
};
```

### 4. **用户体验改进**（常见需求）

#### a) 建议置信度显示（对应后端置信度功能）
```typescript
// 更新TypeScript接口
interface AISuggestion {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  text?: string;
  suggestion: string;
  originalText?: string;
  replaceTo?: string;
  confidence?: number;  // 新增置信度字段
  confidence_factors?: {  // 调试信息
    text_length: number;
    issue_type: string;
    has_detailed_replacement: boolean;
  };
}

// 在建议卡片中显示置信度
{suggestion.confidence && (
  <div className="flex items-center gap-2 mb-2">
    <span className="text-xs text-gray-600">Confidence:</span>
    <div className="flex items-center gap-1">
      <div className={`w-16 h-2 bg-gray-200 rounded-full overflow-hidden`}>
        <div 
          className={`h-full transition-all duration-300 ${
            suggestion.confidence >= 0.8 ? 'bg-green-500' :
            suggestion.confidence >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${suggestion.confidence * 100}%` }}
        />
      </div>
      <span className="text-xs font-medium">
        {(suggestion.confidence * 100).toFixed(0)}%
      </span>
    </div>
  </div>
)}

// 可选：根据置信度调整建议卡片的样式
<div
  className={`p-3 rounded-lg border-l-4 transition-all duration-200 ${
    suggestion.confidence && suggestion.confidence < 0.5
      ? 'opacity-75 border-gray-400'  // 低置信度建议显示为半透明
      : suggestion.severity === 'high'
        ? 'border-red-500 bg-red-50'
        : suggestion.severity === 'medium'
          ? 'border-yellow-500 bg-yellow-50'
          : 'border-blue-500 bg-blue-50'
  }`}
>
```

## 后端可能的 Live Code Changes

### 1. **添加AI分析结果持久化**（高概率）

```python
# server/app/models.py - 添加新的数据模型
class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"
    
    id = Column(Integer, primary_key=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"))
    analysis_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    suggestions = Column(Text)  # JSON格式存储
    total_issues = Column(Integer)
    high_severity_count = Column(Integer)
    medium_severity_count = Column(Integer)
    low_severity_count = Column(Integer)
    
    # 关系
    document_version = relationship("DocumentVersion", back_populates="ai_analyses")

# server/app/enhanced_endpoints.py - 修改WebSocket端点
async def websocket_enhanced_endpoint(websocket: WebSocket):
    # ... 现有代码 ...
    
    # 在发送AI建议后，保存到数据库
    if parsed_result.get('issues'):
        # 计算各严重程度的数量
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        for issue in parsed_result['issues']:
            severity_counts[issue.get('severity', 'medium')] += 1
        
        # 保存分析结果
        analysis_result = AIAnalysisResult(
            document_version_id=current_version_id,  # 需要传递
            suggestions=json.dumps(parsed_result),
            total_issues=len(parsed_result.get('issues', [])),
            high_severity_count=severity_counts['high'],
            medium_severity_count=severity_counts['medium'],
            low_severity_count=severity_counts['low']
        )
        db.add(analysis_result)
        db.commit()
```

### 2. **添加API速率限制**（高概率）

```python
# server/app/internal/rate_limiter.py - 新文件
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

class RateLimiter:
    def __init__(self, max_requests: int = 10, window_minutes: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.requests = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, user_id: str) -> tuple[bool, str]:
        async with self._lock:
            now = datetime.utcnow()
            # 清理过期的请求记录
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if now - req_time < self.window
            ]
            
            if len(self.requests[user_id]) >= self.max_requests:
                wait_time = self.requests[user_id][0] + self.window - now
                return False, f"Rate limit exceeded. Try again in {wait_time.seconds} seconds"
            
            self.requests[user_id].append(now)
            return True, "OK"

# server/app/enhanced_endpoints.py - 集成速率限制
rate_limiter = RateLimiter(max_requests=10, window_minutes=60)

async def websocket_enhanced_endpoint(websocket: WebSocket):
    # ... 现有代码 ...
    
    # 在处理AI请求前检查速率限制
    user_id = websocket.client.host  # 或从认证中获取
    allowed, message = await rate_limiter.check_rate_limit(user_id)
    
    if not allowed:
        rate_limit_error = {
            "type": "rate_limit_error",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(rate_limit_error))
        continue
```

### 3. **添加OpenAI API成本监控和预算控制**（高概率）

```python
# server/app/internal/ai_cost_tracker.py - 新文件
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Float
from app.models import Base

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=True)  # 暂时可为空
    document_id = Column(Integer, nullable=True)
    model_used = Column(String, default="gpt-4o")
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    estimated_cost = Column(Float)  # 美元
    request_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    request_type = Column(String)  # 'analysis' 或 'chat'

class CostTracker:
    # GPT-4o pricing (2024年价格)
    PRICING = {
        "gpt-4o": {
            "input": 0.005 / 1000,   # $0.005 per 1K input tokens
            "output": 0.015 / 1000   # $0.015 per 1K output tokens
        }
    }
    
    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = CostTracker.PRICING.get(model, CostTracker.PRICING["gpt-4o"])
        return (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
    
    @staticmethod
    async def log_usage(db, user_id: str, document_id: int, model: str, 
                       input_tokens: int, output_tokens: int, request_type: str):
        cost = CostTracker.calculate_cost(model, input_tokens, output_tokens)
        
        usage_log = AIUsageLog(
            user_id=user_id,
            document_id=document_id,
            model_used=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            request_type=request_type
        )
        
        db.add(usage_log)
        await db.commit()
        return cost

    @staticmethod
    async def get_daily_usage(db, date: datetime = None) -> float:
        if not date:
            date = datetime.utcnow()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        result = db.query(AIUsageLog).filter(
            AIUsageLog.request_timestamp >= start_of_day,
            AIUsageLog.request_timestamp < end_of_day
        ).all()
        
        return sum(log.estimated_cost for log in result)

# server/app/internal/ai_enhanced.py - 集成成本跟踪
class AIEnhanced:
    async def review_document_with_functions(self, document: str, document_id: int = None) -> AsyncGenerator[str | None, None]:
        logger.info(f"Starting enhanced AI analysis, document length: {len(document)}")
        
        # 检查日使用量是否超过预算
        daily_usage = await CostTracker.get_daily_usage(self.db)
        DAILY_BUDGET = 50.0  # $50 daily budget
        
        if daily_usage > DAILY_BUDGET:
            logger.warning(f"Daily budget exceeded: ${daily_usage:.2f}")
            yield json.dumps({
                "error": "daily_budget_exceeded",
                "message": f"Daily AI budget of ${DAILY_BUDGET} exceeded. Current usage: ${daily_usage:.2f}"
            })
            return
        
        # ... 现有AI调用代码 ...
        
        # 调用完成后记录实际使用量
        if hasattr(response, 'usage'):
            actual_input_tokens = response.usage.prompt_tokens
            actual_output_tokens = response.usage.completion_tokens
            
            # 记录使用量和成本
            cost = await CostTracker.log_usage(
                db=self.db,
                user_id="anonymous",  # 暂时匿名
                document_id=document_id,
                model=self.model,
                input_tokens=actual_input_tokens,
                output_tokens=actual_output_tokens,
                request_type="analysis"
            )
            
            logger.info(f"AI request cost: ${cost:.4f}, Daily total: ${daily_usage + cost:.2f}")
```

### 5. **优化Function Calling的错误处理和重试机制**（高概率）

```python
# server/app/internal/ai_enhanced.py - 增强错误处理
import asyncio
from typing import Optional
import backoff

class AIEnhanced:
    @backoff.on_exception(backoff.expo,
                         (openai.RateLimitError, openai.APITimeoutError),
                         max_tries=3,
                         max_time=300)
    async def review_document_with_functions(self, document: str) -> AsyncGenerator[str | None, None]:
        """增强的AI分析，包含重试机制and更好的错误处理"""
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                logger.info(f"AI analysis attempt {retry_count + 1}/{max_retries}")
                
                # ... 现有的AI调用代码 ...
                
                # 增强的Function Calling处理
                suggestions_dict = {}
                parsing_errors = []
                
                for i, func_call in enumerate(function_calls):
                    if func_call["name"] == "create_suggestion":
                        try:
                            args = json.loads(func_call["arguments"])
                            logger.debug(f"Successfully parsed function call {i+1}")
                            
                            # 验证必需字段
                            required_fields = ["originalText", "replaceTo", "type", "severity"]
                            missing_fields = [field for field in required_fields if not args.get(field)]
                            
                            if missing_fields:
                                logger.warning(f"Function call {i+1} missing fields: {missing_fields}")
                                parsing_errors.append({
                                    "call_index": i,
                                    "error": "missing_required_fields",
                                    "missing_fields": missing_fields,
                                    "raw_arguments": func_call["arguments"][:200]
                                })
                                continue
                            
                            # 处理有效的建议...
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON parsing failed for function call {i+1}: {e}")
                            parsing_errors.append({
                                "call_index": i,
                                "error": "json_decode_error",
                                "message": str(e),
                                "raw_arguments": func_call["arguments"][:200]
                            })
                            
                            # 尝试修复常见的JSON错误
                            fixed_args = self.attempt_json_fix(func_call["arguments"])
                            if fixed_args:
                                try:
                                    args = json.loads(fixed_args)
                                    logger.info(f"Successfully fixed JSON for function call {i+1}")
                                    # 继续处理...
                                except:
                                    logger.error(f"JSON fix failed for function call {i+1}")
                
                # 如果解析错误太多，重试
                if len(parsing_errors) > len(function_calls) * 0.5:  # 超过50%失败
                    logger.warning(f"High parsing error rate: {len(parsing_errors)}/{len(function_calls)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Retrying AI analysis due to parsing errors...")
                        await asyncio.sleep(2 ** retry_count)  # 指数退避
                        continue
                
                # 构建最终响应，包含错误信息
                final_response = {
                    "issues": list(suggestions_dict.values()),
                    "parsing_errors": parsing_errors if parsing_errors else None,
                    "retry_count": retry_count,
                    "total_function_calls": len(function_calls)
                }
                
                yield json.dumps(final_response)
                return
                
            except openai.RateLimitError as e:
                logger.error(f"OpenAI rate limit exceeded: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    yield json.dumps({
                        "error": "rate_limit_exceeded",
                        "message": "OpenAI API rate limit exceeded after retries"
                    })
                    return
                await asyncio.sleep(60)  # 等待1分钟
                
            except openai.APITimeoutError as e:
                logger.error(f"OpenAI API timeout: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    yield json.dumps({
                        "error": "api_timeout",
                        "message": "OpenAI API timeout after retries"
                    })
                    return
                await asyncio.sleep(5 * retry_count)
                
            except Exception as e:
                logger.error(f"Unexpected error in AI analysis: {e}")
                yield json.dumps({
                    "error": "unexpected_error",
                    "message": f"Unexpected error: {str(e)}"
                })
                return
    
    def attempt_json_fix(self, broken_json: str) -> Optional[str]:
        """尝试修复常见的JSON格式错误"""
        try:
            # 修复常见问题
            fixed = broken_json.strip()
            
            # 修复缺少引号的问题
            if not fixed.startswith('{'):
                fixed = '{' + fixed
            if not fixed.endswith('}'):
                fixed = fixed + '}'
            
            # 修复截断的JSON
            if fixed.count('"') % 2 != 0:
                fixed += '"'
            
            # 验证修复结果
            json.loads(fixed)
            return fixed
            
        except:
            return None
```

## 面试准备要点

### 1. **前端准备**
- **理解核心流程**: WebSocket消息流、**状态管理模式**
- **准备常见操作**: 如何添加新组件、如何处理状态更新
- **最佳实践**: 适当的日志、清晰的注释、遵循现有代码风格

### 2. **后端准备**
- **数据库操作**: 熟悉 SQLAlchemy ORM、了解如何添加新表和关系
- **异步编程**: 理解 `async/await` 模式、熟悉 `asyncio` 库
- **API 设计**: RESTful 原则、错误处理规范、响应格式统一
- **性能考虑**: 缓存策略、数据库查询优化、API 响应压缩

### 3. **通用技能**
- **问题分析**: 先理解需求，再动手编码
- **代码质量**: 错误处理、边界条件、用户体验
- **沟通能力**: 解释设计决策、讨论权衡方案

### 4. **可能的追问**

#### 前端追问：
- "如何优化大量建议的渲染性能？"（虚拟滚动）
- "如何处理WebSocket连接不稳定？"（重连策略、离线缓存）
- "如何确保用户不会丢失编辑内容？"（自动保存、本地存储）

#### 后端追问：
- "如何处理大文档的分析？"（分块处理、流式响应）
- "如何降低 OpenAI API 成本？"（缓存策略、批处理）
- "如何确保数据安全？"（加密存储、访问控制）
- "如何监控系统性能？"（日志记录、指标收集）

记住：面试官关心的不只是你能否实现功能，更关心你的思维过程、代码质量和解决问题的能力。