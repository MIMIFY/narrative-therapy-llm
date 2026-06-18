import json
from typing import List, Dict, Any, Optional
from llm_api import LLMAPI
import yaml
import re
import pdb
from imcs_prompt import build_prompt,IMCS_system_prompt,IMCS_system_prompt_en
def clean_yaml_text(yaml_text: str) -> str:
    """
    清理YAML文本，处理各种可能的代码块标记情况。
    
    Args:
        yaml_text: 原始YAML文本
        
    Returns:
        清理后的YAML文本
    """
    # 移除所有可能的代码块标记
    yaml_text = yaml_text.strip()
    
    # 处理可能的代码块标记
    code_block_patterns = [
        r"^```(?:yaml|yml)?\s*(.*?)\s*```$",  # 标准格式
        r"^```(?:yaml|yml)?\s*(.*?)\s*``$",  # 标准格式
        r"^```(?:yaml|yml)?\s*(.*?)\s*`$",  # 标准格式
        r"^``(?:yaml|yml)?\s*(.*?)\s*```$",  # 标准格式
        r"^`(?:yaml|yml)?\s*(.*?)\s*```$",  # 标准格式
        r"^```(?:yaml|yml)?\s*(.*?)$",         # 只有开头的
        r"^(.*?)\s*```$",                      # 只有结尾的
        r"^'''\s*(.*?)\s*'''$",                # 单引号格式
        r"^'''\s*(.*?)$",                      # 只有开头的单引号
        r"^(.*?)\s*'''$",                      # 只有结尾的单引号
        r"^\"\"\"\s*(.*?)\s*\"\"\"$",          # 双引号格式
        r"^\"\"\"\s*(.*?)$",                   # 只有开头的双引号
        r"^(.*?)\s*\"\"\"$"                    # 只有结尾的双引号
    ]
    
    for pattern in code_block_patterns:
        match = re.match(pattern, yaml_text, re.IGNORECASE | re.DOTALL)
        if match:
            yaml_text = match.group(1).strip()
            break
    
    # 处理可能的多余代码块标记
    yaml_text = re.sub(r'^```|```$|^\'\'\'|\'\'\'$|^"""|"""$', '', yaml_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 清理空白行和多余空格
    lines = [line.strip() for line in yaml_text.split('\n') if line.strip()]
    yaml_text = '\n'.join(lines)
    
    return yaml_text
def parse_imcs_yaml(yaml_text: str) -> Dict[str, str]:
    """
    从YAML文本中解析IMCS标注内容，确保包含所有必需字段。
    
    Args:
        yaml_text: YAML格式的文本
        
    Returns:
        Dict包含以下必需字段：
        - annotation: IMCS标注类型
        - resource: 资源类型
        - confidence: 置信度
        - latent_narrative_dynamics_analysis: 潜在叙事动力学分析
        
    如果解析失败或缺少必需字段，返回None
    """
    # 必需字段列表
    required_fields = {
        "annotation": "None,解析失败",
        "resource": "None,解析失败",
        "confidence": "0.0,解析失败",
        "latent_narrative_dynamics_analysis": "None,解析失败"
    }
    
    # Step 1: 去掉markdown代码块包装
    yaml_text = clean_yaml_text(yaml_text)
    # yaml_text = yaml_text.strip()
    # code_block_match = re.match(r"^```(?:yaml|yml)?\s*(.*?)\s*```$", yaml_text, re.IGNORECASE | re.DOTALL)
    # if code_block_match:
    #     yaml_text = code_block_match.group(1).strip()
    
    # Step 2: 尝试用PyYAML解析
    try:
        data = yaml.safe_load(yaml_text)
        if not isinstance(data, dict):
            return None
            
        # 检查并获取所有必需字段
        result = {}
        for field in required_fields:
            # 不区分大小写查找键
            found = False
            for k, v in data.items():
                if k.lower() == field.lower():
                    result[field] = str(v).strip()
                    found = True
                    break
            if not found:
                result[field] = required_fields[field]
                
        return result
        
    except Exception as e:
        print(f"YAML解析失败: {str(e)}")
        # Step 3: 使用正则表达式作为备选方案
        lines = yaml_text.split('\n')
        result = required_fields.copy()
        current_key = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是新的键值对
            key_match = re.match(r'^(\w+)\s*:', line)
            if key_match:
                current_key = key_match.group(1).lower()
                # 提取冒号后的内容
                value = line[len(key_match.group(0)):].strip(' :"\'')
                if value:
                    for field in required_fields:
                        if current_key == field.lower():
                            result[field] = value
                            break
            elif current_key:
                # 处理多行值
                for field in required_fields:
                    if current_key == field.lower():
                        result[field] += "\n" + line
                        break
        
        # 清理结果
        for field in result:
            result[field] = result[field].strip()
            
        return result
def parse_yaml_value(yaml_text: str, key: str) -> Optional[str]:
    """
    从 YAML 文本中提取指定字段的值。
    支持以下格式: 
      - 普通 YAML: stage: xxx
      - 带引号: stage: "xxx"
      - markdown 代码块包裹: ```YAML\nstage: xxx\n```
      - 多行YAML内容
    """
    # Step 1: 去掉 markdown 代码块包装( ```yaml ... ``` )
    yaml_text = yaml_text.strip()
    code_block_match = re.match(r"^```(?:yaml|yml)?\s*(.*?)\s*```$", yaml_text, re.IGNORECASE | re.DOTALL)
    if code_block_match:
        yaml_text = code_block_match.group(1).strip()

    # Step 2: 尝试用PyYAML解析
    try:
        data = yaml.safe_load(yaml_text)
        if isinstance(data, dict):
            # 不区分大小写查找键
            for k, v in data.items():
                if k.lower() == key.lower():
                    return str(v).strip()
    except Exception:
        pass  # 如果PyYAML解析失败,使用正则表达式

    # Step 3: 使用正则表达式提取
    # 处理多行内容
    lines = yaml_text.split('\n')
    result = []
    found_key = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 如果找到了目标键
        if line.lower().startswith(key.lower() + ':'):
            found_key = True
            # 提取冒号后的内容
            value = line[len(key) + 1:].strip(' :"\'')
            if value:  # 如果同一行有值
                result.append(value)
        # 如果已经找到键,且当前行不是新的键值对
        elif found_key and not re.match(r'^\w+\s*:', line):
            result.append(line)
        # 如果遇到新的键值对,停止收集
        elif found_key and re.match(r'^\w+\s*:', line):
            break
            
    if result:
        return '\n'.join(result).strip()
    return ""

class IMCSClassifier:
    def __init__(self, llm_api: LLMAPI, context_window: int = 5):
        self.llm_api = llm_api
        
        self.context_window = context_window

    def annotate_client_turn(self, client_utterance: str, context: List[Dict], before_dialogue: List[Dict],language: str = 'zh') -> Dict:
        """
        对来访者某一轮发言进行IMCS标注,结合上下文。
        """
        #拼接PROMPT
        
        system_prompt = IMCS_system_prompt if language == 'zh' else IMCS_system_prompt_en
        prompt = build_prompt(context,language, client_utterance)
        response = self.llm_api.make_request(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,  # 适当提高温度以增加多样性
            max_tokens=1024,   # 保持足够的输出空间
            top_p=1.0,        # 扩大采样范围,增加多样性
            frequency_penalty=0.2,  # 增加对重复内容的惩罚
            presence_penalty=0.0,   # 增加对多样性的鼓励
            stop_sequences=["<example", "## [Dialogue history]"]  # 防止模型继续生成示例
        )
        # pdb.set_trace()
        # 解析大模型输出
        output = response['response']['choices'][0]['message']['content']
        # pdb.set_trace()
        # 解析IMCS标注结果
        parsed_imcs = parse_imcs_yaml(output)
        if parsed_imcs is None:
            print(f"警告:IMCS标注解析失败,使用默认值")
            parsed_imcs = {
                "annotation": "None,解析失败",
                "resource": "None,解析失败",
                "confidence": "0.0,解析失败",
                "latent_narrative_dynamics_analysis": "None,解析失败"
            }
        return parsed_imcs