import os
import json
import tqdm
import argparse
import yaml,re
import pdb
from typing import List, Dict, Any, Tuple, Optional
from llm_api import LLMAPI
from prompts import EVALUATION_PROMPTS

def validate_score(score_str: str) -> Optional[float]:
    """
    验证分数是否在1-5范围内,且是0.5的倍数
    
    Args:
        score_str: 分数字符串
        
    Returns:
        验证后的浮点数分数,如果无效则返回None
    """
    try:
        score = float(score_str)
        # 检查是否在1-5范围内且是0.5的倍数
        if 1 <= score <= 5 and (score * 2) % 1 == 0:
            return score
    except (ValueError, TypeError):
        pass
    return None

def validate_explanation(explanation: str) -> str:
    """
    验证解释是否有效
    
    Args:
        explanation: 解释字符串
        
    Returns:
        验证后的解释字符串, 如果无效则返回默认值
    """
    if not explanation or len(explanation.strip()) < 10:  # 确保解释至少有10个字符
        return "Without detailed explanations."
    return explanation.strip()

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
        # 如果已经找到键，且当前行不是新的键值对
        elif found_key and not re.match(r'^\w+\s*:', line):
            result.append(line)
        # 如果遇到新的键值对，停止收集
        elif found_key and re.match(r'^\w+\s*:', line):
            break
            
    if result:
        return '\n'.join(result).strip()
    return ""

class DimensionEvaluator:
    def __init__(self, llm_api: LLMAPI):
        """
        初始化维度评估器
        
        Args:
            llm_api: LLMAPI实例
        """
        self.llm_api = llm_api
        self.dimensions = list(EVALUATION_PROMPTS.keys())
        
    def evaluate_dialogue(self, dialogue: List[Dict], key_client: str, key_therapist: str) -> Dict[str, Dict[str, float]]:
        """
        评估单个对话的五个维度得分
        
        Args:
            dialogue: 对话数据, 格式为[{"client": "...", "therapist": "..."}, ...]
            
        Returns:
            包含五个维度得分和解释的字典
        """
        # 将对话转换为文本格式
        dialogue_text = self._format_dialogue(dialogue,key_client, key_therapist)
        
        # 对每个维度分别进行评估
        results = {}
        for dimension in self.dimensions:
            score, explanation = self._evaluate_dimension(dimension, dialogue_text)
            results[dimension] = {
                "score": score,
                "explanation": explanation
            }
            
        return results
        
    def _format_dialogue(self, dialogue: List[Dict],key_client: str, key_therapist: str) -> str:
        """将对话转换为文本格式"""
        formatted = []
        for turn in dialogue:
            client_text = turn.get(key_client) or turn.get("client") or turn.get("user") or ""
            therapist_text = (
                turn.get(key_therapist)
                or turn.get("therapist")
                or turn.get("baseline")
                or turn.get("answer_final")
                or turn.get("answer_before")
                or ""
            )
            formatted.append(f"来访者: {client_text}")
            formatted.append(f"咨询师: {therapist_text}")
        return "\n".join(formatted)
        
    def _evaluate_dimension(self, dimension: str, dialogue_text: str) -> Tuple[float, str]:
        """评估单个维度"""
        # 获取该维度的评估提示
        prompt = EVALUATION_PROMPTS[dimension](dialogue_text)
        
        # 调用LLM进行评估
        response = self.llm_api.make_request(
            prompt=prompt,
            system_prompt="""你是一位严苛且专业的叙事疗法咨询师督导。请严格遵循以下评估原则：

1. 评分标准(使用0.5分间隔):
   - 1.0: 完全不符合评估标准中的任何一条
   - 1.5: 基本不符合评估标准,仅勉强达到最低要求
   - 2.0: 部分符合评估标准,但存在明显不足
   - 2.5: 基本符合部分评估标准,但整体表现一般
   - 3.0: 符合大部分评估标准,表现达到基本要求
   - 3.5: 较好地符合评估标准,表现良好
   - 4.0: 很好地符合评估标准,表现优秀
   - 4.5: 非常符合评估标准,表现非常优秀
   - 5.0: 完美符合所有评估标准,表现卓越

2. 评估原则: 
   - 严格遵循评估标准中的具体条目
   - 确保评分有区分度,合理使用0.5分间隔
   - 对每个评分点都要有明确的判断依据
   - 解释必须具体,指出具体问题和优点
   - 重点关注该维度的具体表现

3. 注意事项: 
   - 不要因为对话整体流畅就给高分
   - 要严格对照评估标准中的具体条目
   - 对每个评分点都要有充分理由
   - 保持客观公正,不受主观影响
   - 重点关注咨询师在该维度的具体表现""",
            temperature=0.1,  # 降低temperature,使输出更确定
            max_tokens=100,
            top_p=0.1,  # 降低top_p,限制输出的多样性
            frequency_penalty=0.5,  # 增加频率惩罚,避免重复使用相同的评分
            presence_penalty=0.5  # 增加存在惩罚,鼓励更全面的评估
        )
        
        # 解析评估结果
        try:
            content = response["response"]["choices"][0]["message"]["content"]
            # pdb.set_trace()
            score_str = parse_yaml_value(content, dimension)
            explanation = parse_yaml_value(content, "explanation")
            
            # 验证分数
            score = validate_score(score_str)
            if score is None:
                return 0.0, "Invalid score value. Score must be between 1 and 5 with 0.5 intervals."
            
            # 验证解释
            explanation = validate_explanation(explanation)
            
            return score, explanation
        except:
            return 0.0, "Evaluation failed."

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir",
        type=str,
        default="../../int/simulation_output",
        help="Input directory. Use --version for input_dir/version layouts; use --version . for flat JSON directories."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./evaluation_results-baselines_esconv_clients",
        help="Output directory."
    )
    parser.add_argument(
        "--version",
        type=str,
        default=".",
        help="Version subdirectory name. Use '.' when JSON files are directly under input_dir."
    )
    parser.add_argument(
        "--number",
        type=str,
        default="V1_1",
        # default="INT-full",
        help="Run label used in the output directory."
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="gpt-4o",
        help="The engine to use."
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
        help="API key. Defaults to OPENAI_API_KEY or OPENROUTER_API_KEY."
    )
    parser.add_argument(
        "--base_url",
        type=str,
        default=os.getenv("OPENAI_BASE_URL") or os.getenv("OPENROUTER_BASE_URL") or "https://api.openai.com/v1",
        help="OpenAI-compatible base URL."
    )
    parser.add_argument(
        "--specific_prefix",
        type=str,
        default=None,
        help="Only evaluate JSON files whose names start with this prefix."
    )
    parser.add_argument(
        "--key_client",
        type=str,
        default="client",
        help="JSON key for the client/user utterance."
    )
    parser.add_argument(
        "--key_therapist",
        type=str,
        default="therapist",
        help="JSON key for the therapist/system response."
    )
    parser.add_argument(
        "--max_files",
        type=int,
        default=None,
        help="Maximum number of JSON files to evaluate. Defaults to all files."
    )
    return parser.parse_args()

def main():
    args = parse_args()

    if not args.api_key:
        raise SystemExit("Error: missing API key. Set OPENAI_API_KEY/OPENROUTER_API_KEY or pass --api_key.")
    
    # 初始化LLM API
    llm_api = LLMAPI(
        api_key=args.api_key,
        base_url=args.base_url,
        engine=args.engine
    )
    
    # 初始化评估器
    evaluator = DimensionEvaluator(llm_api)
    
    # 创建输出目录
    version_label = args.version if args.version not in ("", ".") else "flat"
    out_pathdir = os.path.join(args.output_dir, version_label, args.number)
    os.makedirs(out_pathdir, exist_ok=True)
    print("out_pathdir:",out_pathdir)

    # 获取所有对话文件
    in_path = args.input_dir if args.version in ("", ".") else os.path.join(args.input_dir, args.version)
    print("in_path:",in_path)
    if not os.path.exists(in_path):
        raise SystemExit(f"Error: input path '{in_path}' does not exist.")

    key_client = args.key_client
    key_therapist = args.key_therapist
    if args.specific_prefix:
        # 如果指定了文件前缀，只评估以该前缀开头的文件
        dialogue_files = [f for f in os.listdir(in_path) if f.startswith(args.specific_prefix) and f.endswith(".json")]
        print(args.specific_prefix)
    else:
        # 否则评估目录下所有文件
        dialogue_files = [f for f in os.listdir(in_path) if f.endswith(".json")]
    if args.max_files is not None:
        dialogue_files = dialogue_files[: args.max_files]
    # pdb.set_trace()
    print("===提取文件个数===",len(dialogue_files))
    if not dialogue_files:
        print(f"警告：在 {in_path} 中没有找到符合条件的文件")
        return
    
    # 存储所有评估结果
    all_results = []
    # 检查是否存在已评估的结果
    all_results_file = os.path.join(out_pathdir, "all_evaluation_results.json")
    if os.path.exists(all_results_file):
        with open(all_results_file, "r", encoding="utf-8") as f:
            all_results = json.load(f)
        print(f"找到已评估结果，已评估文件数: {len(all_results)}")
    
    # 获取已评估的文件名
    evaluated_files = {result["file_name"] for result in all_results}
    
    # 存储每个维度的总分,用于计算平均值
    dimension_scores = {dim: [] for dim in evaluator.dimensions}
    
    # 从已评估的结果中初始化dimension_scores
    for result in all_results:
        for dimension in evaluator.dimensions:
            dimension_scores[dimension].append(result["results"][dimension]["score"])
    
    # 评估每个对话
    for file_name in tqdm.tqdm(dialogue_files, desc="评估对话"):
        # 如果文件已经评估过，跳过
        if file_name in evaluated_files:
            # print(f"文件 {file_name} 已评估过，跳过")
            continue
            
        # 读取对话文件
        print("当前处理的file_name:",file_name)
        with open(os.path.join(in_path, file_name), "r", encoding="utf-8") as f:
            dialogue = json.load(f)
        if isinstance(dialogue, dict) and isinstance(dialogue.get("dialogue"), list):
            dialogue = dialogue["dialogue"]
        if not isinstance(dialogue, list):
            print(f"警告：{file_name} is not a dialogue list, skipped.")
            continue
        
        # 评估对话
        results = evaluator.evaluate_dialogue(dialogue,key_client,key_therapist)
        
        # # 保存单个文件的评估结果
        # result_file = os.path.join(args.output_dir, f"eval_{file_name}")
        # with open(result_file, "w", encoding="utf-8") as f:
        #     json.dump(results, f, ensure_ascii=False, indent=4)
            
        # 添加到总结果列表
        prefix = args.specific_prefix or ""
        all_results.append({
            "dir": args.input_dir,
            "version": args.version,
            "file_prefix": prefix,
            "file_name": file_name,
            "results": results
        })
        all_results_file = os.path.join(out_pathdir, "all_evaluation_results.json")
        
        # 每评估完一个文件就保存一次结果
        with open(all_results_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
        
        # 更新每个维度的分数
        for dimension in evaluator.dimensions:
            dimension_scores[dimension].append(results[dimension]["score"])
    
    # 计算并保存平均分
    average_scores = {
        dimension: (sum(scores) / len(scores) if scores else 0.0)
        for dimension, scores in dimension_scores.items()
    }
    
    average_scores_file = os.path.join(out_pathdir, "average_scores_all.json")
    with open(average_scores_file, "w", encoding="utf-8") as f:
        json.dump(average_scores, f, ensure_ascii=False, indent=4)
    
    print(f"version: {args.version}, number: {args.number}")
    print(f"所有评估结果已保存到: {all_results_file}")
    print(f"平均分已保存到: {average_scores_file}")
    print("\n各维度平均分:")
    for dimension, score in average_scores.items():
        print(f"{dimension}: {score:.2f}")
    print("=============")

if __name__ == "__main__":
    main()
