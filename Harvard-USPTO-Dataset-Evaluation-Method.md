# AI系统性能评估指标详解与实例

## 1. 问题识别能力 (Issue Detection Capability)

### 1.1 指标说明

**中文说明**: 评估AI系统识别专利文档中实际存在问题的能力，包括发现问题的准确性、完整性和误报控制。

**English**: Evaluates the AI system's ability to identify actual issues in patent documents, including accuracy, completeness, and false positive control.

**评估内容**:
- 真阳性率 (True Positive Rate): AI正确识别出的实际问题
- 假阳性率 (False Positive Rate): AI错误识别的问题（误报）
- 假阴性率 (False Negative Rate): AI未能识别的实际问题（漏报）

### 1.2 评估方法

使用已标注的专利数据，将AI识别结果与专家标注进行对比。

### 1.3 数据示例

**测试数据 - 来自Harvard USPTO Dataset**:
```json
{
  "patent_id": "US-2019-0234567",
  "claim_text": "A method for processing data comprising storing the data in a database and retrieving the stored data from a database for analysis",
  "expert_annotations": [
    {
      "issue_id": "E1",
      "text": "comprising storing",
      "issue": "Missing colon after 'comprising'"
    },
    {
      "issue_id": "E2", 
      "text": "from a database",
      "issue": "Incorrect antecedent basis - should be 'from the database'"
    }
  ]
}
```

**AI系统输出**:
```json
{
  "ai_detected_issues": [
    {
      "originalText": "comprising storing",
      "issue": "Missing colon after transitional phrase"
    },
    {
      "originalText": "from a database", 
      "issue": "Antecedent basis error"
    },
    {
      "originalText": "for analysis",
      "issue": "Vague term"  // 这是误报
    }
  ]
}
```

### 1.4 评估代码

```python
def evaluate_detection_capability(expert_annotations, ai_results):
    """
    评估问题识别能力
    
    Returns:
        dict: 包含准确率、召回率、F1分数的评估结果
    """
    # 初始化计数器
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    
    # 创建专家标注的问题集合
    expert_issues = {ann['text']: ann['issue'] for ann in expert_annotations}
    ai_issues = {res['originalText']: res['issue'] for res in ai_results}
    
    # 计算真阳性和假阳性
    for ai_text, ai_issue in ai_issues.items():
        if ai_text in expert_issues:
            true_positives += 1
        else:
            false_positives += 1
    
    # 计算假阴性
    for expert_text in expert_issues:
        if expert_text not in ai_issues:
            false_negatives += 1
    
    # 计算指标
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,  # 0.67 (2个正确，1个误报)
        'recall': recall,        # 1.0 (找到所有问题)
        'f1_score': f1_score,    # 0.80
        'false_positive_rate': false_positives / (false_positives + true_positives)  # 0.33
    }
```

---

## 2. 问题分类能力 (Issue Classification Capability)

### 2.1 指标说明

**中文说明**: 评估AI系统对识别出的问题进行正确分类的能力，包括问题类型判断和严重程度评估。

**English**: Evaluates the AI system's ability to correctly classify identified issues, including issue type determination and severity assessment.

**评估内容**:
- 类型分类准确率: Structure、Punctuation、Antecedent Basis等分类的准确性
- 严重程度判断准确率: high、medium、low等级判断的准确性
- 混淆矩阵: 各类别之间的误分类情况

### 2.2 评估方法

比较AI的分类结果与专家标注的分类标签。

### 2.3 数据示例

**测试数据**:
```json
{
  "patent_id": "US-2020-0345678",
  "issues_with_labels": [
    {
      "text": "A device being substantially flat",
      "expert_type": "Ambiguity",
      "expert_severity": "high",
      "reason": "Term 'substantially' is indefinite"
    },
    {
      "text": "comprising: a processor a memory",
      "expert_type": "Punctuation", 
      "expert_severity": "medium",
      "reason": "Missing punctuation between elements"
    },
    {
      "text": "the CPU processes the data",
      "expert_type": "Antecedent Basis",
      "expert_severity": "high",
      "reason": "No prior introduction of 'the CPU'"
    }
  ]
}
```

**AI分类结果**:
```json
{
  "ai_classifications": [
    {
      "text": "A device being substantially flat",
      "ai_type": "Ambiguity",
      "ai_severity": "high"  // 正确
    },
    {
      "text": "comprising: a processor a memory",
      "ai_type": "Structure",  // 错误，应该是Punctuation
      "ai_severity": "high"     // 错误，应该是medium
    },
    {
      "text": "the CPU processes the data",
      "ai_type": "Antecedent Basis",
      "ai_severity": "high"  // 正确
    }
  ]
}
```

### 2.4 评估代码

```python
from sklearn.metrics import confusion_matrix, classification_report

def evaluate_classification_capability(expert_labels, ai_predictions):
    """
    评估问题分类能力
    """
    # 问题类型分类评估
    type_labels = [item['expert_type'] for item in expert_labels]
    type_predictions = [item['ai_type'] for item in ai_predictions]
    
    # 严重程度分类评估
    severity_labels = [item['expert_severity'] for item in expert_labels]
    severity_predictions = [item['ai_severity'] for item in ai_predictions]
    
    # 计算分类报告
    type_report = classification_report(
        type_labels, 
        type_predictions,
        output_dict=True
    )
    
    severity_report = classification_report(
        severity_labels,
        severity_predictions, 
        output_dict=True
    )
    
    # 混淆矩阵
    type_confusion = confusion_matrix(type_labels, type_predictions)
    
    return {
        'type_accuracy': type_report['accuracy'],  # 0.67
        'severity_accuracy': severity_report['accuracy'],  # 0.67
        'type_confusion_matrix': type_confusion,
        'detailed_metrics': {
            'type_classification': type_report,
            'severity_classification': severity_report
        }
    }
```

---

## 3. 文本定位精度 (Text Localization Precision)

### 3.1 指标说明

**中文说明**: 评估AI系统在原始文档中精确定位问题文本的能力，包括文本边界的准确性和选择范围的合理性。

**English**: Evaluates the AI system's ability to precisely locate problematic text in the original document, including accuracy of text boundaries and reasonableness of selection scope.

**评估内容**:
- 完全匹配率: originalText与实际问题文本完全一致的比例
- 部分匹配率: 有重叠但不完全一致的比例  
- 范围合理性: 选择的文本长度是否适当

### 3.2 评估方法

计算AI定位的文本与专家标注文本的重叠度。

### 3.3 数据示例

**测试数据**:
```json
{
  "claim_text": "A wireless communication device, comprising: a transmitter configured to transmit signals at a predetermined frequency; a receiver configured to receive signals; and an antenna coupled to the transmitter and the receiver.",
  "expert_text_boundaries": [
    {
      "start": 42,
      "end": 92,
      "text": "a transmitter configured to transmit signals at a predetermined frequency",
      "issue": "Term 'predetermined' may be indefinite"
    }
  ]
}
```

**AI定位结果**:
```json
{
  "ai_text_selections": [
    {
      "originalText": "at a predetermined frequency",  // 部分匹配
      "start_estimate": 70,
      "end_estimate": 92
    }
  ]
}
```

### 3.4 评估代码

```python
def evaluate_text_localization(expert_boundaries, ai_selections, full_text):
    """
    评估文本定位精度
    """
    localization_scores = []
    
    for expert in expert_boundaries:
        expert_text = expert['text']
        best_match_score = 0
        
        for ai in ai_selections:
            ai_text = ai['originalText']
            
            # 计算文本重叠度
            if ai_text in expert_text:
                # AI选择的是子串
                overlap_score = len(ai_text) / len(expert_text)
            elif expert_text in ai_text:
                # AI选择的范围更大
                overlap_score = len(expert_text) / len(ai_text)
            else:
                # 计算字符级重叠
                overlap = set(ai_text.split()) & set(expert_text.split())
                overlap_score = len(overlap) / max(len(ai_text.split()), len(expert_text.split()))
            
            best_match_score = max(best_match_score, overlap_score)
        
        localization_scores.append(best_match_score)
    
    return {
        'average_overlap': sum(localization_scores) / len(localization_scores),  # 0.75
        'perfect_matches': sum(1 for s in localization_scores if s == 1.0),
        'partial_matches': sum(1 for s in localization_scores if 0 < s < 1.0),
        'no_matches': sum(1 for s in localization_scores if s == 0)
    }
```

---

## 4. 建议质量 (Suggestion Quality)

### 4.1 指标说明

**中文说明**: 评估AI系统提供的修改建议的质量，包括建议的可执行性、合规性和实用性。

**English**: Evaluates the quality of correction suggestions provided by the AI system, including executability, compliance, and practicality.

**评估内容**:
- 可执行性: 建议是否具体、明确、可直接应用
- 合规性: 建议是否符合USPTO标准
- 改进效果: 采用建议后问题是否得到解决

### 4.2 评估方法

将AI建议与实际专利修改历史或专家建议进行对比。

### 4.3 数据示例

**测试数据 - 包含实际修改历史**:
```json
{
  "original_claim": "A method comprising: processing data efficiently using a processor",
  "issue": "Term 'efficiently' is indefinite",
  "actual_amendment": "A method comprising: processing data at a rate of at least 1000 operations per second using a processor",
  "examiner_suggestion": "Define 'efficiently' with specific metrics"
}
```

**AI建议**:
```json
{
  "ai_suggestion": {
    "originalText": "processing data efficiently",
    "replaceTo": "processing data with a throughput of at least 100 MB/s",
    "explanation": "Replaced subjective term with specific metric"
  }
}
```

### 4.4 评估代码

```python
def evaluate_suggestion_quality(ai_suggestion, actual_amendment, examiner_notes):
    """
    评估建议质量
    """
    quality_scores = {}
    
    # 1. 可执行性评分 (是否提供具体的替换文本)
    if ai_suggestion.get('replaceTo') and len(ai_suggestion['replaceTo']) > 0:
        quality_scores['executability'] = 1.0
    else:
        quality_scores['executability'] = 0.0
    
    # 2. 具体性评分 (是否包含具体数值或标准)
    import re
    if re.search(r'\d+', ai_suggestion.get('replaceTo', '')):
        quality_scores['specificity'] = 1.0
    else:
        quality_scores['specificity'] = 0.5
    
    # 3. 与实际修改的相似度
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(
        None, 
        ai_suggestion.get('replaceTo', ''),
        actual_amendment
    ).ratio()
    quality_scores['similarity_to_actual'] = similarity
    
    # 4. 合规性评分 (是否解决了指出的问题)
    if 'specific' in ai_suggestion.get('replaceTo', '').lower() or \
       any(char.isdigit() for char in ai_suggestion.get('replaceTo', '')):
        quality_scores['compliance'] = 1.0
    else:
        quality_scores['compliance'] = 0.5
    
    # 综合质量分数
    overall_quality = sum(quality_scores.values()) / len(quality_scores)
    
    return {
        'overall_quality': overall_quality,  # 0.875
        'detailed_scores': quality_scores,
        'assessment': 'High quality - provides specific, executable correction'
    }
```

---

## 5. 领域适应性 (Domain Adaptability)

### 5.1 指标说明

**中文说明**: 评估AI系统在不同技术领域的表现差异，识别系统在特定领域的优势和弱点。

**English**: Evaluates performance variations of the AI system across different technical domains, identifying strengths and weaknesses in specific fields.

**评估内容**:
- 跨领域性能差异: 软件、硬件、生物技术等不同领域的表现
- 领域特定规则识别: 能否识别领域特有的问题
- 术语理解准确性: 对专业术语的处理能力

### 5.2 评估方法

在不同技术领域的专利样本上分别测试，比较性能差异。

### 5.3 数据示例

**不同领域的测试数据**:
```json
{
  "software_patent": {
    "cpc_class": "G06F",
    "claim": "A method for optimizing database queries, comprising: analyzing query patterns using machine learning algorithms",
    "domain_specific_issues": ["Software method eligibility", "Algorithm specificity"]
  },
  "biotech_patent": {
    "cpc_class": "C12N", 
    "claim": "An isolated nucleic acid molecule comprising a sequence having at least 80% homology to SEQ ID NO:1",
    "domain_specific_issues": ["Sequence identity precision", "Biological function description"]
  },
  "mechanical_patent": {
    "cpc_class": "F16H",
    "claim": "A gear assembly comprising: a first gear rotatably mounted on a shaft; a second gear meshing with the first gear",
    "domain_specific_issues": ["Mechanical connection specificity", "Movement constraints"]
  }
}
```

### 5.4 评估代码

```python
def evaluate_domain_adaptability(test_results_by_domain):
    """
    评估领域适应性
    """
    domain_performance = {}
    
    for domain, results in test_results_by_domain.items():
        # 计算每个领域的性能指标
        domain_performance[domain] = {
            'accuracy': results['correct'] / results['total'],
            'avg_processing_time': results['total_time'] / results['total'],
            'domain_specific_accuracy': results['domain_issues_found'] / results['domain_issues_total'],
            'sample_size': results['total']
        }
    
    # 计算性能变异系数
    accuracies = [perf['accuracy'] for perf in domain_performance.values()]
    mean_accuracy = sum(accuracies) / len(accuracies)
    variance = sum((x - mean_accuracy) ** 2 for x in accuracies) / len(accuracies)
    cv = (variance ** 0.5) / mean_accuracy  # 变异系数
    
    return {
        'domain_performance': domain_performance,
        'overall_consistency': 1 - cv,  # 0.85 表示跨领域表现较一致
        'best_performing_domain': max(domain_performance, key=lambda x: domain_performance[x]['accuracy']),
        'needs_improvement': [d for d, p in domain_performance.items() if p['accuracy'] < 0.7]
    }
```

---

## 6. 与专家基准对比 (Expert Benchmark Comparison)

### 6.1 指标说明

**中文说明**: 将AI系统的表现与人类专家（专利审查员、专利律师）的判断进行对比，评估AI达到的专业水平。

**English**: Compares AI system performance with human expert judgments (patent examiners, patent attorneys) to assess the professional level achieved by AI.

**评估内容**:
- 与审查员一致性: AI建议与实际审查意见的吻合度
- 与最终授权版本相似度: AI建议的方向是否正确
- 专家评分对比: AI vs 人类专家的质量评分

### 6.2 评估方法

使用包含审查历史的专利数据，对比AI与实际审查员的意见。

### 6.3 数据示例

**包含审查历史的数据**:
```json
{
  "application_number": "16/123,456",
  "original_claim": "A system for improving network performance comprising a module that optimizes traffic flow",
  "examiner_rejection": {
    "statute": "35 U.S.C. 112(b)",
    "reason": "The term 'optimizes' is indefinite",
    "suggestion": "Define specific optimization metrics"
  },
  "applicant_amendment": "A system for improving network performance comprising a module that reduces packet loss by at least 20%",
  "final_granted_claim": "A system for improving network performance comprising a module that reduces packet loss by at least 20% compared to a baseline measurement"
}
```

### 6.4 评估代码

```python
def evaluate_expert_comparison(ai_suggestions, examiner_rejections, final_claims):
    """
    与专家基准对比
    """
    comparison_results = []
    
    for case in zip(ai_suggestions, examiner_rejections, final_claims):
        ai_sugg, examiner_rej, final = case
        
        # 1. AI是否识别了审查员指出的问题
        issue_match = similarity_score(ai_sugg['issue_type'], examiner_rej['reason'])
        
        # 2. AI建议与审查员建议的相似度
        suggestion_match = similarity_score(ai_sugg['suggestion'], examiner_rej['suggestion'])
        
        # 3. AI建议与最终版本的相似度
        final_match = similarity_score(ai_sugg['replaceTo'], final)
        
        comparison_results.append({
            'issue_identification_match': issue_match,
            'suggestion_alignment': suggestion_match,
            'final_version_similarity': final_match
        })
    
    return {
        'avg_examiner_agreement': sum(r['issue_identification_match'] for r in comparison_results) / len(comparison_results),
        'suggestion_quality': sum(r['suggestion_alignment'] for r in comparison_results) / len(comparison_results),
        'correctness_rate': sum(r['final_version_similarity'] for r in comparison_results) / len(comparison_results),
        'professional_level': 'Expert' if sum(r['issue_identification_match'] for r in comparison_results) / len(comparison_results) > 0.8 else 'Competent'
    }
```

---

## 7. 系统鲁棒性 (System Robustness)

### 7.1 指标说明

**中文说明**: 评估AI系统处理各种异常输入和边界情况的能力，确保系统稳定性。

**English**: Evaluates the AI system's ability to handle various abnormal inputs and edge cases, ensuring system stability.

**评估内容**:
- 格式容错性: 处理不同格式的输入
- 噪声容忍度: 处理含有错误的输入
- 边界处理: 极长或极短输入的处理

### 7.2 评估方法

使用特意构造的异常输入测试系统响应。

### 7.3 数据示例

**异常输入测试集**:
```json
{
  "test_cases": [
    {
      "type": "malformed_structure",
      "input": "1. A method comprising step1 step2 step3 without any punctuation or formatting",
      "expected_behavior": "Should identify structure and punctuation issues"
    },
    {
      "type": "extremely_long",
      "input": "[2000+ words claim text]",
      "expected_behavior": "Should handle without timeout or crash"
    },
    {
      "type": "mixed_languages",
      "input": "A device 装置 comprising: a processor 处理器",
      "expected_behavior": "Should process English parts correctly"
    },
    {
      "type": "special_characters",
      "input": "A method comprising: receiving data @#$% processing",
      "expected_behavior": "Should handle special characters gracefully"
    }
  ]
}
```

### 7.4 评估代码

```python
def evaluate_robustness(test_cases, ai_system):
    """
    评估系统鲁棒性
    """
    robustness_scores = {
        'crash_rate': 0,
        'timeout_rate': 0,
        'graceful_degradation': 0,
        'error_recovery': 0
    }
    
    for test_case in test_cases:
        try:
            # 设置超时
            import signal
            signal.alarm(30)  # 30秒超时
            
            result = ai_system.analyze(test_case['input'])
            
            # 检查是否返回了有效结果
            if result and 'suggestions' in result:
                robustness_scores['graceful_degradation'] += 1
            
            signal.alarm(0)  # 取消超时
            
        except TimeoutError:
            robustness_scores['timeout_rate'] += 1
        except Exception as e:
            robustness_scores['crash_rate'] += 1
            # 检查错误恢复
            try:
                # 尝试用正常输入恢复
                normal_result = ai_system.analyze("A normal claim text")
                if normal_result:
                    robustness_scores['error_recovery'] += 1
            except:
                pass
    
    total_tests = len(test_cases)
    return {
        'crash_rate': robustness_scores['crash_rate'] / total_tests,
        'timeout_rate': robustness_scores['timeout_rate'] / total_tests,
        'success_rate': robustness_scores['graceful_degradation'] / total_tests,
        'recovery_rate': robustness_scores['error_recovery'] / max(robustness_scores['crash_rate'], 1),
        'robustness_score': 1 - (robustness_scores['crash_rate'] + robustness_scores['timeout_rate']) / (2 * total_tests)
    }
```

---

## 8. 效率指标 (Efficiency Metrics)

### 8.1 指标说明

**中文说明**: 评估AI系统的处理速度、资源消耗和成本效益。

**English**: Evaluates the AI system's processing speed, resource consumption, and cost-effectiveness.

**评估内容**:
- 响应时间: 不同长度文档的处理时间
- 吞吐量: 单位时间内处理的文档数
- API成本: 每个文档的平均API调用成本

### 8.2 评估方法

记录不同规模输入的处理时间和资源消耗。

### 8.3 数据示例

**不同规模的测试数据**:
```json
{
  "test_documents": [
    {
      "size_category": "small",
      "word_count": 150,
      "claim_count": 1,
      "sample": "A simple device comprising: a processor; and a memory"
    },
    {
      "size_category": "medium",
      "word_count": 500,
      "claim_count": 5,
      "sample": "[Standard patent with 5 claims]"
    },
    {
      "size_category": "large",
      "word_count": 2000,
      "claim_count": 20,
      "sample": "[Complex patent with 20 claims]"
    }
  ]
}
```

### 8.4 评估代码

```python
import time
import psutil
import os

def evaluate_efficiency(test_documents, ai_system):
    """
    评估效率指标
    """
    efficiency_metrics = []
    
    for doc in test_documents:
        # 记录开始状态
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        # 执行分析
        result = ai_system.analyze(doc['sample'])
        
        # 记录结束状态
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        # 计算指标
        processing_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # 估算API成本 (假设每1000 tokens = $0.01)
        estimated_tokens = doc['word_count'] * 1.3  # 粗略估算
        api_cost = (estimated_tokens / 1000) * 0.01
        
        efficiency_metrics.append({
            'size_category': doc['size_category'],
            'word_count': doc['word_count'],
            'processing_time': processing_time,
            'memory_used': memory_used,
            'api_cost': api_cost,
            'time_per_word': processing_time / doc['word_count'],
            'issues_per_second': len(result.get('suggestions', [])) / processing_time if processing_time > 0 else 0
        })
    
    # 汇总统计
    avg_time_per_word = sum(m['time_per_word'] for m in efficiency_metrics) / len(efficiency_metrics)
    total_cost = sum(m['api_cost'] for m in efficiency_metrics)
    
    return {
        'detailed_metrics': efficiency_metrics,
        'summary': {
            'avg_processing_speed': f"{1/avg_time_per_word:.1f} words/second",
            'scalability': 'Linear' if efficiency_metrics[-1]['time_per_word'] < efficiency_metrics[0]['time_per_word'] * 1.5 else 'Non-linear',
            'cost_per_document': f"${total_cost/len(efficiency_metrics):.3f}",
            'memory_efficiency': 'Efficient' if max(m['memory_used'] for m in efficiency_metrics) < 100 else 'Memory-intensive'
        }
    }
```

---

## 9. 学习和改进能力 (Learning and Improvement Capability)

### 9.1 指标说明

**中文说明**: 评估AI系统从反馈中学习和持续改进的能力，识别系统性问题和改进趋势。

**English**: Evaluates the AI system's ability to learn from feedback and continuously improve, identifying systematic issues and improvement trends.

**评估内容**:
- 错误模式识别: 系统是否有重复的错误模式
- 时间趋势分析: 性能是否随时间改善
- 反馈利用率: 用户反馈是否带来改进

### 9.2 评估方法

分析历史性能数据，识别趋势和模式。

### 9.3 数据示例

**历史性能数据**:
```json
{
  "performance_history": [
    {
      "date": "2024-01-01",
      "accuracy": 0.75,
      "user_acceptance": 0.70,
      "common_errors": ["Missing ambiguity issues", "Over-identifying punctuation"]
    },
    {
      "date": "2024-02-01",
      "accuracy": 0.78,
      "user_acceptance": 0.73,
      "common_errors": ["Missing ambiguity issues"]
    },
    {
      "date": "2024-03-01",
      "accuracy": 0.82,
      "user_acceptance": 0.78,
      "common_errors": ["Occasional false positives"]
    }
  ],
  "user_feedback": [
    {"date": "2024-01-15", "type": "false_positive", "category": "Punctuation"},
    {"date": "2024-02-10", "type": "missed_issue", "category": "Ambiguity"},
    {"date": "2024-02-20", "type": "good_suggestion", "category": "Structure"}
  ]
}
```

### 9.4 评估代码

```python
import numpy as np
from sklearn.linear_model import LinearRegression

def evaluate_learning_capability(performance_history, user_feedback):
    """
    评估学习和改进能力
    """
    # 1. 趋势分析
    dates = list(range(len(performance_history)))
    accuracies = [p['accuracy'] for p in performance_history]
    
    # 线性回归分析趋势
    X = np.array(dates).reshape(-1, 1)
    y = np.array(accuracies)
    model = LinearRegression()
    model.fit(X, y)
    
    improvement_slope = model.coef_[0]
    
    # 2. 错误模式分析
    all_errors = []
    for p in performance_history:
        all_errors.extend(p['common_errors'])
    
    from collections import Counter
    error_frequency = Counter(all_errors)
    persistent_errors = [error for error, count in error_frequency.items() if count >= 2]
    
    # 3. 反馈响应分析
    feedback_categories = Counter([f['category'] for f in user_feedback])
    
    # 检查后续性能是否在反馈领域有改善
    improvements_after_feedback = []
    for category, count in feedback_categories.items():
        # 简化: 检查该类别的错误是否减少
        early_errors = performance_history[0]['common_errors']
        late_errors = performance_history[-1]['common_errors']
        if any(category.lower() in error.lower() for error in early_errors) and \
           not any(category.lower() in error.lower() for error in late_errors):
            improvements_after_feedback.append(category)
    
    return {
        'improvement_trend': {
            'slope': improvement_slope,
            'interpretation': 'Improving' if improvement_slope > 0 else 'Declining',
            'improvement_rate': f"{improvement_slope*100:.1f}% per month"
        },
        'systematic_issues': {
            'persistent_errors': persistent_errors,
            'error_resolution_rate': 1 - len(persistent_errors) / len(set(all_errors))
        },
        'feedback_responsiveness': {
            'addressed_categories': improvements_after_feedback,
            'response_rate': len(improvements_after_feedback) / len(feedback_categories) if feedback_categories else 0
        },
        'learning_score': (improvement_slope > 0) * 0.5 + (len(persistent_errors) < 2) * 0.3 + (len(improvements_after_feedback) > 0) * 0.2
    }
```

---

## 10. 用户价值指标 (User Value Metrics)

### 10.1 指标说明

**中文说明**: 评估AI系统为用户带来的实际价值，包括效率提升、质量改进和成本节约。

**English**: Evaluates the actual value the AI system brings to users, including efficiency improvements, quality enhancements, and cost savings.

**评估内容**:
- 专利通过率提升: 使用AI后的专利授权率变化
- 时间节约: 相比纯人工审查节省的时间
- 投资回报率: 系统带来的经济效益

### 10.2 评估方法

比较使用AI前后的关键业务指标。

### 10.3 数据示例

**用户使用数据**:
```json
{
  "before_ai": {
    "period": "2023-01-01 to 2023-06-30",
    "patents_filed": 50,
    "patents_granted": 30,
    "avg_prosecution_time_months": 18,
    "avg_review_time_hours": 8,
    "amendment_rounds": 2.5,
    "attorney_hours_per_patent": 40
  },
  "after_ai": {
    "period": "2024-01-01 to 2024-06-30", 
    "patents_filed": 50,
    "patents_granted": 38,
    "avg_prosecution_time_months": 14,
    "avg_review_time_hours": 3,
    "amendment_rounds": 1.8,
    "attorney_hours_per_patent": 25
  },
  "cost_data": {
    "attorney_hourly_rate": 400,
    "ai_system_monthly_cost": 5000,
    "traditional_review_tools_cost": 2000
  }
}
```

### 10.4 评估代码

```python
def evaluate_user_value(before_ai, after_ai, cost_data):
    """
    评估用户价值指标
    """
    # 1. 质量改进
    grant_rate_before = before_ai['patents_granted'] / before_ai['patents_filed']
    grant_rate_after = after_ai['patents_granted'] / after_ai['patents_filed']
    grant_rate_improvement = (grant_rate_after - grant_rate_before) / grant_rate_before
    
    # 2. 效率提升
    time_saved_per_patent = before_ai['avg_review_time_hours'] - after_ai['avg_review_time_hours']
    prosecution_time_saved = before_ai['avg_prosecution_time_months'] - after_ai['avg_prosecution_time_months']
    attorney_hours_saved = before_ai['attorney_hours_per_patent'] - after_ai['attorney_hours_per_patent']
    
    # 3. 成本节约
    cost_saved_per_patent = attorney_hours_saved * cost_data['attorney_hourly_rate']
    total_patents = after_ai['patents_filed']
    total_cost_saved = cost_saved_per_patent * total_patents
    
    # 4. ROI计算
    ai_total_cost = cost_data['ai_system_monthly_cost'] * 6  # 6个月
    net_savings = total_cost_saved - ai_total_cost
    roi = (net_savings / ai_total_cost) * 100
    
    # 5. 综合价值评分
    value_score = (
        grant_rate_improvement * 0.4 +  # 质量权重40%
        (time_saved_per_patent / before_ai['avg_review_time_hours']) * 0.3 +  # 效率权重30%
        (roi / 100) * 0.3  # ROI权重30%
    )
    
    return {
        'quality_metrics': {
            'grant_rate_improvement': f"{grant_rate_improvement*100:.1f}%",
            'amendment_reduction': f"{(before_ai['amendment_rounds'] - after_ai['amendment_rounds'])/before_ai['amendment_rounds']*100:.1f}%"
        },
        'efficiency_metrics': {
            'review_time_saved': f"{time_saved_per_patent} hours/patent",
            'prosecution_time_saved': f"{prosecution_time_saved} months",
            'productivity_increase': f"{(time_saved_per_patent/before_ai['avg_review_time_hours'])*100:.1f}%"
        },
        'financial_metrics': {
            'cost_per_patent_saved': f"${cost_saved_per_patent:,.0f}",
            'total_savings': f"${total_cost_saved:,.0f}",
            'roi': f"{roi:.1f}%",
            'payback_period': f"{ai_total_cost/total_cost_saved*6:.1f} months"
        },
        'overall_value_score': value_score,
        'value_assessment': 'High Value' if value_score > 0.5 else 'Moderate Value'
    }
```

---

## 综合评估报告示例

```python
def generate_comprehensive_evaluation_report(all_metrics):
    """
    生成综合评估报告
    """
    report = f"""
    # AI系统综合评估报告
    
    ## 执行摘要
    - 总体评分: {all_metrics['overall_score']:.2f}/5.0
    - 专业水平: {all_metrics['professional_level']}
    - 投资回报率: {all_metrics['roi']}
    
    ## 性能指标详情
    
    ### 核心能力
    1. 问题识别准确率: {all_metrics['detection_accuracy']:.1%}
    2. 建议质量评分: {all_metrics['suggestion_quality']:.2f}/5.0
    3. 与专家一致性: {all_metrics['expert_agreement']:.1%}
    
    ### 系统特性
    - 处理速度: {all_metrics['processing_speed']}
    - 系统稳定性: {all_metrics['robustness_score']:.1%}
    - 跨领域一致性: {all_metrics['domain_consistency']:.1%}
    
    ### 业务价值
    - 专利通过率提升: {all_metrics['grant_rate_improvement']}
    - 审查时间节省: {all_metrics['time_saved']}
    - 成本节约: {all_metrics['cost_saved']}
    
    ## 改进建议
    {all_metrics['improvement_recommendations']}
    
    ## 结论
    {all_metrics['conclusion']}
    """
    
    return report
```

---

# 第二部分：真实业务环境下的Multi-agent系统评估（无Ground Truth）

当Multi-agent系统已经部署在真实业务环境中，且没有标准答案（ground truth）可供对比时，需要采用不同的评估策略。以下是三种实用的评估方法：

## 11. 基于用户行为的隐式评估 (User Behavior-based Implicit Evaluation)

### 11.1 指标说明

**中文说明**: 通过分析用户与系统的交互行为来隐式评估系统性能。用户的实际行为是最真实的质量信号，无需预设的标准答案。

**English**: Evaluates system performance by analyzing user interaction behaviors. User's actual behavior serves as the most authentic quality signal without requiring predefined ground truth.

**评估内容**:
- 建议接受率 (Suggestion Acceptance Rate): 用户采纳AI建议的频率
- 交互深度 (Interaction Depth): 用户与建议的交互程度
- 用户留存 (User Retention): 用户持续使用系统的情况
- 隐式满意度 (Implicit Satisfaction): 通过行为推断的满意程度

### 11.2 评估方法

通过埋点收集用户行为数据，分析用户对AI建议的实际使用情况。

### 11.3 数据示例

**用户行为日志数据**:
```json
{
  "session_id": "session_2024_001",
  "user_id": "user_456",
  "document_id": "patent_789",
  "interactions": [
    {
      "timestamp": "2024-03-15T10:23:45",
      "suggestion_id": "sug_001",
      "agent_source": "structure_agent",
      "user_action": "view_details",
      "time_spent": 15.3,
      "subsequent_action": "accept"
    },
    {
      "timestamp": "2024-03-15T10:24:12",
      "suggestion_id": "sug_002",
      "agent_source": "ambiguity_agent",
      "user_action": "view_details",
      "time_spent": 8.7,
      "subsequent_action": "modify_then_accept",
      "modification_extent": 0.3
    },
    {
      "timestamp": "2024-03-15T10:24:35",
      "suggestion_id": "sug_003",
      "agent_source": "antecedent_agent",
      "user_action": "quick_dismiss",
      "time_spent": 2.1,
      "subsequent_action": "reject"
    }
  ],
  "session_metrics": {
    "total_suggestions": 12,
    "suggestions_viewed": 8,
    "suggestions_accepted": 5,
    "suggestions_modified": 2,
    "suggestions_rejected": 5,
    "average_decision_time": 12.4,
    "session_duration": 1840
  }
}
```

### 11.4 评估代码

```python
class UserBehaviorEvaluator:
    def __init__(self):
        self.behavior_logs = []
        self.evaluation_window = 7  # days
        
    def evaluate_implicit_quality(self, user_logs):
        """
        基于用户行为评估系统质量
        
        Returns:
            dict: 包含多维度的隐式评估指标
        """
        # 1. 计算接受率指标
        acceptance_metrics = self._calculate_acceptance_metrics(user_logs)
        
        # 2. 分析交互模式
        interaction_patterns = self._analyze_interaction_patterns(user_logs)
        
        # 3. 评估用户信任度
        trust_indicators = self._evaluate_user_trust(user_logs)
        
        # 4. 计算Agent级别的表现
        agent_performance = self._evaluate_per_agent_performance(user_logs)
        
        return {
            'overall_acceptance_rate': acceptance_metrics['overall_rate'],
            'weighted_acceptance_score': acceptance_metrics['weighted_score'],
            'user_engagement_level': interaction_patterns['engagement_score'],
            'trust_score': trust_indicators['trust_level'],
            'agent_rankings': agent_performance['rankings'],
            'quality_trend': self._calculate_quality_trend(user_logs)
        }
    
    def _calculate_acceptance_metrics(self, user_logs):
        """计算建议接受率相关指标"""
        total_suggestions = 0
        accepted = 0
        modified_accepted = 0
        rejected = 0
        
        for session in user_logs:
            for interaction in session['interactions']:
                total_suggestions += 1
                action = interaction['subsequent_action']
                
                if action == 'accept':
                    accepted += 1
                elif action == 'modify_then_accept':
                    modified_accepted += 1
                elif action == 'reject':
                    rejected += 1
        
        # 加权接受分数：完全接受=1.0，修改后接受=0.7，拒绝=0
        weighted_score = (accepted * 1.0 + modified_accepted * 0.7) / total_suggestions
        
        return {
            'overall_rate': (accepted + modified_accepted) / total_suggestions,
            'direct_acceptance_rate': accepted / total_suggestions,
            'modified_acceptance_rate': modified_accepted / total_suggestions,
            'rejection_rate': rejected / total_suggestions,
            'weighted_score': weighted_score
        }
    
    def _analyze_interaction_patterns(self, user_logs):
        """分析用户交互模式"""
        view_times = []
        decision_times = []
        depth_scores = []
        
        for session in user_logs:
            session_depth = 0
            for interaction in session['interactions']:
                view_times.append(interaction['time_spent'])
                
                # 计算交互深度分数
                if interaction['user_action'] == 'view_details':
                    session_depth += 1.0
                elif interaction['user_action'] == 'quick_dismiss':
                    session_depth += 0.2
                
                if 'modification_extent' in interaction:
                    session_depth += interaction['modification_extent']
            
            depth_scores.append(session_depth / len(session['interactions']))
        
        return {
            'avg_view_time': sum(view_times) / len(view_times) if view_times else 0,
            'engagement_score': sum(depth_scores) / len(depth_scores) if depth_scores else 0,
            'interaction_consistency': 1 - (np.std(view_times) / np.mean(view_times)) if view_times else 0
        }
    
    def _evaluate_user_trust(self, user_logs):
        """评估用户信任度"""
        trust_signals = {
            'quick_accepts': 0,  # 快速接受（高信任）
            'careful_review': 0,  # 仔细审查（中等信任）
            'frequent_rejects': 0,  # 频繁拒绝（低信任）
        }
        
        for session in user_logs:
            for interaction in session['interactions']:
                if interaction['time_spent'] < 5 and interaction['subsequent_action'] == 'accept':
                    trust_signals['quick_accepts'] += 1
                elif interaction['time_spent'] > 10 and interaction['subsequent_action'] in ['accept', 'modify_then_accept']:
                    trust_signals['careful_review'] += 1
                elif interaction['subsequent_action'] == 'reject' and interaction['time_spent'] < 3:
                    trust_signals['frequent_rejects'] += 1
        
        # 计算信任分数
        total_interactions = sum(trust_signals.values())
        if total_interactions > 0:
            trust_level = (trust_signals['quick_accepts'] * 1.0 + 
                          trust_signals['careful_review'] * 0.7 - 
                          trust_signals['frequent_rejects'] * 0.5) / total_interactions
        else:
            trust_level = 0
        
        return {
            'trust_level': max(0, min(1, trust_level)),
            'trust_signals': trust_signals,
            'user_confidence': 'high' if trust_level > 0.7 else 'medium' if trust_level > 0.4 else 'low'
        }
    
    def _evaluate_per_agent_performance(self, user_logs):
        """评估每个Agent的表现"""
        agent_metrics = {}
        
        for session in user_logs:
            for interaction in session['interactions']:
                agent = interaction['agent_source']
                if agent not in agent_metrics:
                    agent_metrics[agent] = {
                        'total': 0,
                        'accepted': 0,
                        'avg_time_spent': [],
                        'trust_score': []
                    }
                
                agent_metrics[agent]['total'] += 1
                if interaction['subsequent_action'] in ['accept', 'modify_then_accept']:
                    agent_metrics[agent]['accepted'] += 1
                agent_metrics[agent]['avg_time_spent'].append(interaction['time_spent'])
        
        # 计算每个Agent的综合得分
        agent_scores = {}
        for agent, metrics in agent_metrics.items():
            acceptance_rate = metrics['accepted'] / metrics['total'] if metrics['total'] > 0 else 0
            avg_time = sum(metrics['avg_time_spent']) / len(metrics['avg_time_spent']) if metrics['avg_time_spent'] else 0
            
            # 综合得分：接受率占70%，用户投入时间占30%（时间长说明用户重视）
            agent_scores[agent] = acceptance_rate * 0.7 + min(avg_time / 20, 1.0) * 0.3
        
        # 排名
        rankings = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'agent_metrics': agent_metrics,
            'agent_scores': agent_scores,
            'rankings': rankings
        }
```

---

## 12. Agent间一致性评估 (Inter-Agent Consistency Evaluation)

### 12.1 指标说明

**中文说明**: 通过分析多个Agent之间的判断一致性来评估系统可靠性。高度一致的判断通常更可信，而分歧较大的情况可能需要进一步验证。

**English**: Evaluates system reliability by analyzing consistency among multiple agents' judgments. Highly consistent judgments are typically more trustworthy, while significant disagreements may require further verification.

**评估内容**:
- 共识度 (Consensus Level): Agent间对同一问题的一致程度
- 置信度分布 (Confidence Distribution): 各Agent置信度分数的分布情况
- 冲突模式 (Conflict Patterns): Agent间分歧的类型和频率
- 协调效率 (Coordination Efficiency): 解决分歧所需的资源

### 12.2 评估方法

分析Multi-agent系统内部的决策过程，通过Agent间的相互验证建立可信度。

### 12.3 数据示例

**Multi-agent决策日志**:
```json
{
  "analysis_id": "analysis_2024_001",
  "document_segment": "A method comprising: processing data substantially faster than conventional methods",
  "agent_decisions": [
    {
      "agent_name": "structure_agent",
      "issue_detected": false,
      "confidence": 0.85,
      "reasoning": "Structure is grammatically correct"
    },
    {
      "agent_name": "ambiguity_agent",
      "issue_detected": true,
      "severity": "high",
      "confidence": 0.92,
      "specific_issue": "Term 'substantially faster' is indefinite",
      "suggestion": "Specify quantitative improvement (e.g., 'at least 50% faster')"
    },
    {
      "agent_name": "clarity_agent",
      "issue_detected": true,
      "severity": "medium",
      "confidence": 0.78,
      "specific_issue": "Vague comparison without baseline",
      "suggestion": "Define what 'conventional methods' means"
    },
    {
      "agent_name": "legal_compliance_agent",
      "issue_detected": true,
      "severity": "high",
      "confidence": 0.88,
      "specific_issue": "May fail 35 U.S.C. 112(b) for indefiniteness"
    }
  ],
  "coordinator_resolution": {
    "final_decision": "issue_exists",
    "consensus_score": 0.75,
    "final_severity": "high",
    "resolution_method": "majority_vote_with_confidence_weighting",
    "agents_in_agreement": ["ambiguity_agent", "clarity_agent", "legal_compliance_agent"],
    "dissenting_agents": ["structure_agent"]
  }
}
```

### 12.4 评估代码

```python
class InterAgentConsistencyEvaluator:
    def __init__(self):
        self.decision_logs = []
        self.consistency_thresholds = {
            'high_consensus': 0.8,
            'moderate_consensus': 0.6,
            'low_consensus': 0.4
        }
    
    def evaluate_agent_consistency(self, multi_agent_logs):
        """
        评估Agent间的一致性
        
        Returns:
            dict: 包含一致性指标和可靠性评分
        """
        consistency_metrics = {
            'overall_consensus': self._calculate_overall_consensus(multi_agent_logs),
            'pairwise_agreement': self._calculate_pairwise_agreement(multi_agent_logs),
            'confidence_correlation': self._analyze_confidence_correlation(multi_agent_logs),
            'conflict_patterns': self._identify_conflict_patterns(multi_agent_logs),
            'resolution_efficiency': self._evaluate_resolution_efficiency(multi_agent_logs)
        }
        
        # 计算系统可靠性分数
        reliability_score = self._calculate_reliability_score(consistency_metrics)
        consistency_metrics['system_reliability'] = reliability_score
        
        return consistency_metrics
    
    def _calculate_overall_consensus(self, logs):
        """计算整体共识度"""
        consensus_scores = []
        
        for decision_log in logs:
            agents = decision_log['agent_decisions']
            
            # 计算检测到问题的Agent比例
            issue_detected_count = sum(1 for a in agents if a.get('issue_detected', False))
            consensus_on_issue = max(issue_detected_count, len(agents) - issue_detected_count) / len(agents)
            
            # 考虑置信度加权
            if issue_detected_count > 0:
                avg_confidence = sum(a['confidence'] for a in agents if a.get('issue_detected', False)) / issue_detected_count
                weighted_consensus = consensus_on_issue * avg_confidence
            else:
                weighted_consensus = consensus_on_issue
            
            consensus_scores.append(weighted_consensus)
        
        return {
            'mean_consensus': sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0,
            'consensus_distribution': self._categorize_consensus_levels(consensus_scores),
            'high_consensus_rate': sum(1 for s in consensus_scores if s > self.consistency_thresholds['high_consensus']) / len(consensus_scores) if consensus_scores else 0
        }
    
    def _calculate_pairwise_agreement(self, logs):
        """计算Agent两两之间的一致性"""
        agent_pairs = {}
        
        for decision_log in logs:
            agents = decision_log['agent_decisions']
            
            # 计算每对Agent之间的一致性
            for i in range(len(agents)):
                for j in range(i + 1, len(agents)):
                    pair_key = tuple(sorted([agents[i]['agent_name'], agents[j]['agent_name']]))
                    
                    if pair_key not in agent_pairs:
                        agent_pairs[pair_key] = {'agree': 0, 'disagree': 0}
                    
                    # 判断是否一致
                    if agents[i].get('issue_detected', False) == agents[j].get('issue_detected', False):
                        agent_pairs[pair_key]['agree'] += 1
                    else:
                        agent_pairs[pair_key]['disagree'] += 1
        
        # 计算每对的一致率
        pairwise_scores = {}
        for pair, counts in agent_pairs.items():
            total = counts['agree'] + counts['disagree']
            pairwise_scores[f"{pair[0]}-{pair[1]}"] = counts['agree'] / total if total > 0 else 0
        
        return {
            'pairwise_agreement_scores': pairwise_scores,
            'average_pairwise_agreement': sum(pairwise_scores.values()) / len(pairwise_scores) if pairwise_scores else 0,
            'most_aligned_pair': max(pairwise_scores.items(), key=lambda x: x[1]) if pairwise_scores else None,
            'least_aligned_pair': min(pairwise_scores.items(), key=lambda x: x[1]) if pairwise_scores else None
        }
    
    def _analyze_confidence_correlation(self, logs):
        """分析置信度相关性"""
        confidence_patterns = {
            'high_confidence_consensus': 0,
            'low_confidence_disagreement': 0,
            'confidence_variance': []
        }
        
        for decision_log in logs:
            agents = decision_log['agent_decisions']
            confidences = [a['confidence'] for a in agents]
            
            # 计算置信度方差
            if confidences:
                variance = np.var(confidences)
                confidence_patterns['confidence_variance'].append(variance)
                
                # 高置信度且一致
                if min(confidences) > 0.8 and decision_log['coordinator_resolution']['consensus_score'] > 0.8:
                    confidence_patterns['high_confidence_consensus'] += 1
                
                # 低置信度且分歧
                if max(confidences) < 0.6 and decision_log['coordinator_resolution']['consensus_score'] < 0.5:
                    confidence_patterns['low_confidence_disagreement'] += 1
        
        avg_variance = sum(confidence_patterns['confidence_variance']) / len(confidence_patterns['confidence_variance']) if confidence_patterns['confidence_variance'] else 0
        
        return {
            'average_confidence_variance': avg_variance,
            'confidence_stability': 1 - min(avg_variance, 1),  # 越稳定越好
            'high_confidence_consensus_rate': confidence_patterns['high_confidence_consensus'] / len(logs) if logs else 0,
            'uncertainty_disagreement_rate': confidence_patterns['low_confidence_disagreement'] / len(logs) if logs else 0
        }
    
    def _identify_conflict_patterns(self, logs):
        """识别冲突模式"""
        conflict_types = {
            'structure_vs_ambiguity': 0,
            'severity_disagreement': 0,
            'detection_disagreement': 0,
            'suggestion_variation': 0
        }
        
        for decision_log in logs:
            agents = decision_log['agent_decisions']
            
            # 检测不同类型的冲突
            issue_detections = [a.get('issue_detected', False) for a in agents]
            if len(set(issue_detections)) > 1:
                conflict_types['detection_disagreement'] += 1
            
            # 严重程度分歧
            severities = [a.get('severity', 'none') for a in agents if a.get('issue_detected', False)]
            if len(set(severities)) > 1:
                conflict_types['severity_disagreement'] += 1
            
            # 特定Agent组合的冲突
            agent_names = [a['agent_name'] for a in agents]
            if 'structure_agent' in agent_names and 'ambiguity_agent' in agent_names:
                struct_decision = next(a for a in agents if a['agent_name'] == 'structure_agent')
                ambig_decision = next(a for a in agents if a['agent_name'] == 'ambiguity_agent')
                if struct_decision.get('issue_detected') != ambig_decision.get('issue_detected'):
                    conflict_types['structure_vs_ambiguity'] += 1
        
        total_decisions = len(logs)
        return {
            'conflict_frequencies': {k: v/total_decisions for k, v in conflict_types.items()} if total_decisions > 0 else conflict_types,
            'most_common_conflict': max(conflict_types.items(), key=lambda x: x[1])[0] if conflict_types else None,
            'conflict_rate': sum(1 for log in logs if log['coordinator_resolution']['consensus_score'] < 0.6) / total_decisions if total_decisions > 0 else 0
        }
    
    def _evaluate_resolution_efficiency(self, logs):
        """评估冲突解决效率"""
        resolution_metrics = {
            'resolution_methods': {},
            'average_iterations': 0,
            'resolution_success_rate': 0
        }
        
        for decision_log in logs:
            resolution = decision_log['coordinator_resolution']
            method = resolution['resolution_method']
            
            if method not in resolution_metrics['resolution_methods']:
                resolution_metrics['resolution_methods'][method] = 0
            resolution_metrics['resolution_methods'][method] += 1
            
            # 成功解决的标准：有明确决策且共识度>0.5
            if resolution['final_decision'] and resolution['consensus_score'] > 0.5:
                resolution_metrics['resolution_success_rate'] += 1
        
        if logs:
            resolution_metrics['resolution_success_rate'] /= len(logs)
            
        return resolution_metrics
    
    def _calculate_reliability_score(self, metrics):
        """基于一致性指标计算系统可靠性分数"""
        weights = {
            'consensus': 0.3,
            'pairwise': 0.2,
            'confidence': 0.2,
            'conflict': 0.15,
            'resolution': 0.15
        }
        
        scores = {
            'consensus': metrics['overall_consensus']['mean_consensus'],
            'pairwise': metrics['pairwise_agreement']['average_pairwise_agreement'],
            'confidence': metrics['confidence_correlation']['confidence_stability'],
            'conflict': 1 - metrics['conflict_patterns']['conflict_rate'],
            'resolution': metrics['resolution_efficiency']['resolution_success_rate']
        }
        
        reliability = sum(scores[k] * weights[k] for k in weights)
        
        return {
            'overall_reliability': reliability,
            'component_scores': scores,
            'reliability_level': 'high' if reliability > 0.8 else 'moderate' if reliability > 0.6 else 'low',
            'confidence_in_results': f"{reliability * 100:.1f}%"
        }
```
