import os
import json
import tqdm
import argparse
import sys
from llm_api import LLMAPI
from typing import Dict, List
from imcs_annotation import IMCSClassifier
import pdb

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir",
        type=str,
        default="../../int/simulation_output",
        help="Input directory. Use --version for input_dir/version layouts; use --version . for flat JSON directories.",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=".",
        help="Version subdirectory name. Use '.' when JSON files are directly under input_dir.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./evaluation_results-baselines_esconv_clients",
        help="Output directory.",
    )
    parser.add_argument(
        "--number",
        type=str,
        default="INT-full",
        help="Run label used in the output directory."
    ),
    parser.add_argument(
        "--engine",
        type=str,
        default="gpt-4o",
        help="The engine to use."
    )
    parser.add_argument(
        "--context_window",
        type=int,
        default=5,
        help="The context window of the IMCS annotation."
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
    ),
    parser.add_argument(
        "--specific_prefix",
        type=str,
        default=None,
        help="Cooperation-level prefix filter, comma-separated. Example: 2 processes files starting with cooperation_level_2_."
    ),
    parser.add_argument(
        "--language",
        type=str,
        default="zh",
        # default="en",
        help="The language to use."
    )
    parser.add_argument(
        "--max_files",
        type=int,
        default=None,
        help="Maximum number of JSON files to annotate. Defaults to all files."
    )
    args = parser.parse_args()
    
    # 处理specific_prefix参数
    if args.specific_prefix:
        args.specific_prefix = [int(x.strip()) for x in args.specific_prefix.split(',')]
    else:
        args.specific_prefix = None
        
    return args

def get_data_before_processing(root_dir, versions):
    """获取需要处理的原始数据文件列表"""
    version_conv_ids = {}
    folder_path = os.path.join(root_dir, versions)
    json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    version_conv_ids[versions] = json_files
    return version_conv_ids

def load_stage_reflection_mapping():
    """加载中英文映射文件"""
    try:
        with open('stage-reflection-dict-en.json', 'r', encoding='utf-8') as f:
            stage_reflection_en = json.load(f)
        with open('stage-reflection-dict-zh.json', 'r', encoding='utf-8') as f:
            stage_reflection_zh = json.load(f)
        
        # 构建映射字典
        stage_mapping = {
            "trust building": "Trust Building",
            "problem externalization": "Problem Externalization",
            "re-authoring": "Re-authoring Conversation",
            "re-membering": "Re-membering Conversation"
        }
        
        # 构建reflection_level映射
        reflection_mapping = {}
        for stage_zh, stage_en in stage_mapping.items():
            reflections_en = stage_reflection_en[stage_en]
            reflections_zh = stage_reflection_zh[stage_zh]
            for ref_en, ref_zh in zip(reflections_en, reflections_zh):
                reflection_mapping[ref_zh["title"]] = ref_en["title"]
        
    except Exception as e:
        print(f"加载映射文件失败: {str(e)}")
        raise
    return stage_mapping, reflection_mapping

# def translate_stage(self, stage: str) -> str:
#     """翻译stage"""
#     return self.stage_mapping.get(stage.lower(), stage)
    
# def translate_reflection(self, reflection: str) -> str:
#     """翻译reflection_level"""
#     return self.reflection_mapping.get(reflection, reflection)

    
def get_processed_files(progress_file: str) -> Dict[str, List[str]]:
    """从进度记录文件中获取已处理的文件及其变体状态"""
    if not os.path.exists(progress_file):
        return {}
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def update_progress(progress_file: str, file_status: Dict[str, List[str]]):
    """更新进度记录文件"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(file_status, f, ensure_ascii=False, indent=4)   

def annatate_single_dialogue(before_data: List[Dict], classifier: IMCSClassifier, context_window: int, language: str = 'zh',key_client: str = "client", key_therapist: str = "therapist"):
    """
    标注单个对话文件
    """
    
    # 1. 优化现有对话
    annatated_dialogue = []
    
    for turn in before_data:
         # 保存turn的基本信息
        tmp ={}
        tmp["round"] = turn["round"]
        tmp[key_client] = turn.get(key_client) or turn.get("client") or turn.get("user", "")
        tmp[key_therapist] = turn.get(key_therapist) or turn.get("therapist") or turn.get("baseline") or turn.get("answer_final") or turn.get("answer_before", "")
        
        # tmp['client'] = turn.get("client") or turn.get("user", "")
        # tmp['therapist'] = turn.get("therapist") or turn.get("baseline") or turn.get("answer_final") or turn.get("answer_before", "")
        tmp["stage"] = turn.get("stage", "")
        tmp["reflection_level"] = turn.get("reflection_level", "")
        tmp["user_cooperation"] = turn.get("user_cooperation", "")
        tmp['context_window'] = context_window
        
        if turn["round"] == 1:
            tmp['IMCS'] = {
                "annotation": "None",
                "resource": "None",
                "confidence": "0.98",
                "latent_narrative_dynamics_analysis": "叙述现状问题/保持原有身份认同/对话开始阶段"
            }
            annatated_dialogue.append(tmp)
            continue
            
        # 根据context_window，获取上下文
        context_start = max(0, turn["round"] - context_window)
        context_turns = annatated_dialogue[context_start:turn["round"]]
        
        # 将上下文转换为指定格式
        formatted_context = []
        for context_turn in context_turns:
            formatted_context.append(f"Client: {context_turn[key_client]}")
            formatted_context.append(f"Therapist: {context_turn[key_therapist]}")
            # formatted_context.append(f"Client: {context_turn['client']}")
            # formatted_context.append(f"Therapist: {context_turn['therapist']}")
    
        # 针对每一轮，开始标注
        # pdb.set_trace()
        client_utterance = turn.get(key_client) or turn.get("client") or turn.get("user", "")
        # client_utterance = turn.get("client") or turn.get("user", "")
        tmp['IMCS']= classifier.annotate_client_turn(client_utterance, formatted_context, before_data, language)
        annatated_dialogue.append(tmp)
        
    return annatated_dialogue

def main():
    args = parse_args()
    # key_client, key_therapist = "client_roleplay", "baseline_roleplay"
    key_client, key_therapist = "client", "therapist"

    if not args.api_key:
        print("Error: missing API key. Set OPENAI_API_KEY/OPENROUTER_API_KEY or pass --api_key.")
        sys.exit(1)

    # 检查输入目录是否存在
    if not os.path.exists(args.input_dir):
        print(f"Error: The directory '{args.input_dir}' does not exist. 原始数据根目录错误, 提前退出IMCS标注程序.")
        sys.exit(1)
        
    print("Part I: Start IMCS Annotation!")
    
    # 初始化LLM API
    llm_api = LLMAPI(
        api_key=args.api_key,
        base_url=args.base_url,
        engine=args.engine
    )

    # 创建标注器实例
    classifier = IMCSClassifier(llm_api, context_window=args.context_window)
    
    # 创建输出目录
    version_label = args.version if args.version not in ("", ".") else "flat"
    out_pathdir = os.path.join(args.output_dir, version_label, args.number)
    os.makedirs(out_pathdir, exist_ok=True)
    print("out_pathdir:",out_pathdir)
    
    # 获取需要处理的文件列表
    in_path = args.input_dir if args.version in ("", ".") else os.path.join(args.input_dir, args.version)
    print("in_path:",in_path)
    if not os.path.exists(in_path):
        print(f"Error: The input path '{in_path}' does not exist.")
        sys.exit(1)
    
    # 根据有无前缀，获取目录下待标注评估的文件名
    
    dialogue_files = []
    if args.specific_prefix:
        # 如果指定了文件前缀，只评估以该前缀开头的文件
        for prefix in args.specific_prefix:
            dialogue_files.extend([f for f in os.listdir(in_path) if f.startswith("cooperation_level_"+str(prefix)+"_") and f.endswith(".json")])
            print("lalalala",args.specific_prefix)
    else:
        # 否则评估目录下所有文件
        dialogue_files = [f for f in os.listdir(in_path) if f.endswith(".json")]
        if args.max_files is not None:
            dialogue_files = dialogue_files[: args.max_files]
    print("===提取文件个数===",len(dialogue_files))
    
    if not dialogue_files:
        print(f"警告：在 {in_path} 中没有找到符合条件的文件")
        return

    # before_refine_version_filenames = get_data_before_processing(args.input_dir, args.version)
    # before_refine_filenames = before_refine_version_filenames[args.version]

    # 进度记录文件路径
    progress_file = ""
    if args.specific_prefix:
        progress_file = os.path.join(args.output_dir, args.version, f"progress_{args.version}_{args.number}_with_cooperation_level.json")
    else:
        progress_file = os.path.join(args.output_dir, args.version, f"progress_{args.version}_{args.number}.json")

    # 获取已处理的文件状态
    processed_files = get_processed_files(progress_file)
    
    # cooperation_levels = {"不配合":0, "一般配合":1, "配合":2} 
    # cooperation_levels = {}
    # cooperation_levels = {"uncooperative":0, "moderately cooperative":1,"cooperative":2}

    # 创建每个文件的标注结果的输出目录
    Dialogue_generation_version_dir = out_pathdir
    print("Output Dir: Where the AI-annatated data was stored ", Dialogue_generation_version_dir)
    os.makedirs(Dialogue_generation_version_dir, exist_ok=True)
    # # 加载stage-reflection字典,中英文映射关系
    # stage_mapping, reflection_mapping = load_stage_reflection_mapping()
    # # 加载英文版stage-reflection字典
    # with open("stage-reflection-dict-en.json", "r", encoding="utf-8") as f:
    #     stage_reflection_dict = json.load(f)
    
    
    # 设置进度条
    gen_dialogue_in_version_progress_bar = tqdm.tqdm(
        total=len(dialogue_files), 
        desc="Within specific version, the annatation loop of every single user files: "
    )
    # pdb.set_trace()
    # 处理每个对话文件
    for task_name in dialogue_files:
        # 检查是否已处理所有变体
        if args.specific_prefix:
            # 如果指定了文件前缀，只评估以该前缀开头的文件,以配合程度区分
            # if task_name in processed_files:
            if task_name in processed_files and len(processed_files[task_name]) == len(args.specific_prefix):
                gen_dialogue_in_version_progress_bar.update(1)
                continue
        else:
            if task_name in processed_files:
                gen_dialogue_in_version_progress_bar.update(1)
                continue
        
        # 读取原始数据
        input_file = os.path.join(in_path, task_name)
        with open(input_file, "r", encoding="utf-8") as f_in:
            before_data = json.load(f_in) # list of turns, or {"dialogue": [...]}
            if isinstance(before_data, dict) and isinstance(before_data.get("dialogue"), list):
                before_data = before_data["dialogue"]
            if not isinstance(before_data, list):
                print(f"警告：{input_file} is not a dialogue list, skipped.")
                gen_dialogue_in_version_progress_bar.update(1)
                continue
            # {round: int, user: str, answer_before: str, answer_final: str, stage: str, reflection_level: str, rag_references: list of str}
        
        # 初始化文件状态
        if task_name not in processed_files:
            processed_files[task_name] = []
        
        # 当指定文件前缀，有配合度情况下，根据配合度记录标注文件、更新进度文件：
        if args.specific_prefix:
            # 处理每个配合度变体
            for cooperation_level_id in args.specific_prefix:
                # 检查是否已处理该变体
                # variant_name = f"cooperation_level_{cooperation_level_id}_{task_name}"
                variant_name = task_name
                if variant_name in processed_files[task_name]:
                    continue
                
                # 开始标注当前对话文件
                after_data = annatate_single_dialogue(before_data, classifier, args.context_window, args.language)
                
                # 保存优化后的数据
                out_path = os.path.join(Dialogue_generation_version_dir, variant_name)
                with open(out_path, "w", encoding="utf-8") as f_out:
                    json.dump(after_data, f_out, ensure_ascii=False, indent=4)
                
                # 更新进度
                processed_files[task_name].append(variant_name)
                update_progress(progress_file, processed_files)
        # 当指定文件前缀，无配合度情况下，记录标注文件、更新进度文件：
        else:
            # 开始标注当前对话文件
            after_data = annatate_single_dialogue(before_data, classifier, args.context_window, args.language,key_client, key_therapist)
            # after_data = optimize_single_dialogue(before_data, optimizer, cooperation_level, args.target_rounds)
            # 保存优化后的数据
            out_path = os.path.join(Dialogue_generation_version_dir, task_name)
            with open(out_path, "w", encoding="utf-8") as f_out:
                json.dump(after_data, f_out, ensure_ascii=False, indent=4)
            
            # 更新进度
            processed_files[task_name].append(task_name)
            update_progress(progress_file, processed_files)
            
            
        gen_dialogue_in_version_progress_bar.update(1)
        # break
        

if __name__ == "__main__":
    main()
