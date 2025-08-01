# 专利审查系统增强功能设计方案

## 问题现状

### 现有问题
1. **文本匹配不准确** - 建议卡和文档段落匹配经常出错
2. **缺少视觉反馈** - 点击建议卡时高亮效果不明显
3. **功能不完善** - 建议卡缺少操作按钮，无法接受/关闭建议

### 新功能需求
1. 建议卡操作：关闭/接受/拷贝按钮
2. AI聊天对话框 - 用户主动提问
3. AI画图功能 - 生成流程图、系统图等

## 解决方案

### 1. 精确文本匹配（核心改进）

**问题**：现在用段落号匹配，不准确
**解决**：改用精确文本匹配

```typescript
// AI输出格式改为：
interface AISuggestion {
  originalText: string;    // 原始文本
  replaceTo: string;       // 建议替换文本  
  type: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
}
```

**实现方式**：
- 使用TipTap底层的ProseMirror API进行文本匹配和高亮
- 不再使用HTML过滤，直接操作编辑器文档结构
- 降低LLM温度提高输出稳定性

**ProseMirror实现参考**：

1. **文本定位**：使用 `findText` 方法在文档中定位原始文本位置
```typescript
// 示例：在文档中查找原始文本
const findTextInDocument = (doc: Node, text: string) => {
  let pos = 0;
  doc.descendants((node, nodePos) => {
    if (node.isText && node.text?.includes(text)) {
      const start = nodePos + node.text.indexOf(text);
      const end = start + text.length;
      return { start, end, text };
    }
    pos += node.nodeSize;
  });
};
```

2. **临时高亮装饰**：点击建议卡时创建临时高亮，3秒后自动取消
```typescript
// 示例：创建临时高亮装饰器
const createTemporaryHighlight = (start: number, end: number) => {
  return Decoration.inline(start, end, {
    class: 'temporary-highlight',
    style: 'background-color: #ffeb3b; opacity: 0.6; transition: opacity 0.3s;'
  });
};

// 示例：点击建议卡时的交互逻辑
const handleSuggestionClick = (suggestion: AISuggestion) => {
  // 1. 查找原始文本位置
  const textPosition = findTextInDocument(editor.state.doc, suggestion.originalText);
  
  // 2. 创建临时高亮装饰
  const highlightDecoration = createTemporaryHighlight(textPosition.start, textPosition.end);
  const decorationSet = DecorationSet.create(editor.state.doc, [highlightDecoration]);
  
  // 3. 应用高亮到编辑器
  const tr = editor.state.tr.setMeta('decorations', decorationSet);
  editor.view.dispatch(tr);
  
  // 4. 3秒后自动取消高亮
  setTimeout(() => {
    const clearTr = editor.state.tr.setMeta('decorations', DecorationSet.empty);
    editor.view.dispatch(clearTr);
  }, 3000);
};
```

3. **应用建议替换**：点击"接受建议"按钮时替换文本
```typescript
// 示例：应用建议替换文本
const applySuggestion = (suggestion: AISuggestion) => {
  // 1. 查找原始文本位置
  const textPosition = findTextInDocument(editor.state.doc, suggestion.originalText);
  
  // 2. 执行文本替换
  const tr = editor.state.tr.replaceWith(
    textPosition.start, 
    textPosition.end, 
    editor.schema.text(suggestion.replaceTo)
  );
  
  // 3. 应用替换到编辑器
  editor.view.dispatch(tr);
  
  // 4. 从建议列表中移除该建议
  removeSuggestionFromList(suggestion);
};
```

4. **临时高亮管理**：简单的超时控制
```typescript
// 示例：管理临时高亮超时
let highlightTimeout: number | null = null;

const clearHighlight = () => {
  const clearTr = editor.state.tr.setMeta('decorations', DecorationSet.empty);
  editor.view.dispatch(clearTr);
};

// 在点击建议卡时设置临时高亮
const handleSuggestionClick = (suggestion: AISuggestion) => {
  // 清除之前的超时
  if (highlightTimeout) {
    clearTimeout(highlightTimeout);
  }
  
  // 创建新的临时高亮
  const textPosition = findTextInDocument(editor.state.doc, suggestion.originalText);
  const highlightDecoration = createTemporaryHighlight(textPosition.start, textPosition.end);
  const decorationSet = DecorationSet.create(editor.state.doc, [highlightDecoration]);
  
  const tr = editor.state.tr.setMeta('decorations', decorationSet);
  editor.view.dispatch(tr);
  
  // 3秒后自动清除
  highlightTimeout = setTimeout(clearHighlight, 3000);
};
```

参考文档：
- ProseMirror Transform: https://prosemirror.net/docs/guide/#transform
- ProseMirror Decorations: https://prosemirror.net/docs/guide/#decoration

### 2. 建议卡功能增强

在右侧栏每个建议卡添加操作按钮：

```jsx
<div className="suggestion-actions">
  <button onClick={() => acceptSuggestion(suggestion)}>✅ 接受</button>
  <button onClick={() => copySuggestion(suggestion)}>📋 拷贝</button>  
  <button onClick={() => closeSuggestion(index)}>❌ 关闭</button>
</div>
```

**功能实现**：
- **接受建议**：使用ProseMirror transaction替换文本
- **拷贝内容**：复制建议内容到剪贴板
- **关闭建议**：从建议列表移除

### 3. AI聊天功能

**前端**：在右侧栏添加聊天面板
```jsx
<ChatPanel 
  onSendMessage={(message) => sendChatMessage(message)}
  messages={chatHistory}
/>
```

**后端**：新增聊天API代理
```python
@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    # 转发到OpenAI API
    # 支持function calling
```

### 4. AI画图功能

使用Mermaid渲染图表：

**新增依赖**：
```json
{
  "mermaid": "^10.6.1"
}
```

**AI Function Calling工具**：
```python
tools = [
    {
        "name": "create_suggestion",
        "description": "创建文档建议",
        "parameters": {
            "type": "object",
            "properties": {
                "originalText": {
                    "type": "string",
                    "description": "原始文本内容"
                },
                "replaceTo": {
                    "type": "string", 
                    "description": "建议替换的文本内容"
                },
                "type": {
                    "type": "string",
                    "description": "建议类型：grammar, style, clarity等"
                },
                "severity": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "建议严重程度"
                },
                "description": {
                    "type": "string",
                    "description": "建议的详细说明"
                }
            },
            "required": ["originalText", "replaceTo", "type", "severity", "description"]
        }
    },
    {
        "name": "create_diagram", 
        "description": "生成图表",
        "parameters": {
            "type": "object",
            "properties": {
                "mermaid_syntax": {
                    "type": "string",
                    "description": "Mermaid图表语法"
                },
                "diagram_type": {
                    "type": "string",
                    "enum": ["flowchart", "sequence", "class", "er", "gantt"],
                    "description": "图表类型"
                },
                "title": {
                    "type": "string",
                    "description": "图表标题"
                }
            },
            "required": ["mermaid_syntax", "diagram_type"]
        }
    }
]
```

**Function Calling参考**：
- OpenAI Function Calling文档：https://platform.openai.com/docs/guides/function-calling
- 确保工具定义格式正确，参数类型明确

## 关键技术点

1. **不使用HTML过滤** - 全部改用TipTap/ProseMirror API
2. **精确文本匹配** - originalText + replaceTo格式
3. **Function Calling** - 确保AI工具调用可靠性
4. **后端代理** - 前端调用后端，后端转发OpenAI

## 实现要点

### ProseMirror集成
- 使用TipTap的底层ProseMirror API进行精确文本操作
- 实现文本匹配、高亮和替换功能
- 参考ProseMirror官方文档进行开发

### Function Calling规范
- 严格按照OpenAI Function Calling格式定义工具
- 确保参数类型和描述清晰明确
- 保持与现有AISuggestion数据结构一致
