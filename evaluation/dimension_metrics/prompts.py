# 评估提示模板的共有部分
COMMON_PROMPT_TEMPLATE = """你是严苛专业的叙事治疗领域专业的心理咨询师督导, 请评估以下践行叙事疗法咨询对话的**{维度名称}({维度英文})**
#定义#:
{维度定义}
#评估标准#:
{评估标准}
#对话内容#:
{dialogue_text}
#打分标准#:
从1-5分进行评分(1分最低, 5分最高),分数之间最少间距为0.5
你评估非常严格专业,你的打分是有区分度的。
#输出格式#:
请以YAML格式输出评分结果, 其中score是小数数值,explanation凝练切中要害且不超过30字,格式如下:
```YAML
{维度英文}: <score>
explanation: <explanation>
```"""

# 各个维度的定义和评估标准
DIMENSION_CRITERIA = {
    "reassuring": {
        "name": "安抚性",
        "definition": """咨询师是否能有效传递关怀和理解, 帮助来访者感受到被理解、被支持, 尤其是在情绪上得到安慰和抚慰.安抚性在叙事疗法中常常出现在建立信任的早期阶段, 帮助来访者放松, 愿意分享自己的困扰.""",
        "criteria": [
            "是否在来访者情绪脆弱时提供温暖的反应",
            "是否表现出真诚的共情和理解",
            "是否能够有效缓解来访者的焦虑和不安",
            "是否使用恰当的语气和措辞传递关怀",
            "是否在关键时刻提供必要的心理安慰"
        ]
    },
    "empowering": {
        "name": "赋权性",
        "definition": """咨询师是否能帮助来访者重新定义和看待自己的问题, 特别是在外化对话阶段.在叙事疗法中, 外化是帮助来访者将问题与自我区分的关键策略, 赋权性评估的是咨询师是否鼓励来访者以新的视角看待问题, 并增强解决问题的信心.""",
        "criteria": [
            "是否有效引导来访者将困扰从自身内化的情绪中分离",
            "是否帮助来访者以新的视角重新审视问题",
            "是否促进来访者的自我效能感",
            "是否引导来访者设定可实现的目标",
            "是否提供建设性的反馈和建议"
        ]
    },
    "transformative": {
        "name": "变革性",
        "definition": """咨询师是否能引发来访者深刻的自我反思, 帮助来访者重新构建思维或产生新的认知.在叙事疗法中, 改写（re-authoring）是一个核心阶段, 通过与治疗师的互动, 来访者能够重新编写个人故事、重塑自己对事件的理解, 达到自我成长和认知转变.""",
        "criteria": [
            "是否促进来访者的认知重构, 重新思考和定义过去的经历",
            "是否帮助来访者建立新的视角, 多视角理解自我",
            "是否引导来访者发现新的可能性",
            "是否促进来访者的行为改变",
            "是否帮助来访者建立新的叙事"
        ]
    },
    "reconnecting": {
        "name": "连接性",
        "definition": """咨询师是否能够帮助来访者重新审视与他人、自己或环境的关系, 增强来访者与他人的情感联系.重组关系（re-membering）是叙事疗法中的一个重要概念, 通过重新审视过去的关系, 帮助来访者修复与他人或自我的联系.""",
        "criteria": [
            "是否帮助来访者重新审视自己与重要他人他物的关系",
            "是否促进来访者的社会连接",
            "是否帮助来访者建立新的关系模式或↩恢复情感的和谐与平衡"
        ]
    },
    "humanness": {
        "name": "类人性",
        "definition": """咨询师的回答是否自然流畅、具有真实感, 避免机械化的回复.我们希望咨询师在语言上能模仿人与人之间的互动, 使对话显得亲切、真实, 并且能有效传达情感.""",
        "criteria": [
            "对话是否自然流畅",
            "是否以自然且富有关怀的方式回应",
            "是否保持适当的自我暴露",
            "是否展现出专业的人性关怀"
        ]
    }
}

# 生成完整的评估提示
def generate_evaluation_prompt(dimension: str, dialogue_text: str) -> str:
    """
    生成指定维度的评估提示
    
    Args:
        dimension: 维度名称（英文）
        dialogue_text: 对话文本
        
    Returns:
        完整的评估提示
    """
    criteria = DIMENSION_CRITERIA[dimension]
    criteria_text = "\n".join([f"{i+1}. {criterion}" for i, criterion in enumerate(criteria["criteria"])])
    
    return COMMON_PROMPT_TEMPLATE.format(
        维度名称=criteria["name"],
        维度英文=dimension,
        维度定义=criteria["definition"],
        评估标准=criteria_text,
        dialogue_text=dialogue_text
    )

# 导出评估提示字典
# EVALUATION_PROMPTS = {
#     dimension: lambda dialogue_text: generate_evaluation_prompt(dimension, dialogue_text)
#     for dimension in DIMENSION_CRITERIA.keys()
# } 存在错误原因：
# lambda 函数捕获的是变量的最终值,而不是每次循环时的值。因此,当循环结束后,dimension 的值被固定为最后一个维度（humanness）。所以,所有维度的评估提示都使用了 humanness 的定义和标准。
EVALUATION_PROMPTS = {
    dimension: (lambda dimension: lambda dialogue_text: generate_evaluation_prompt(dimension, dialogue_text))(dimension)
    for dimension in DIMENSION_CRITERIA.keys()
}