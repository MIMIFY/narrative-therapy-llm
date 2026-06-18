# system prompt in english
SYSTEM_PROMPT="""You are a rigorous and professional supervisor in narrative therapy. Please strictly adhere to the following evaluation principles:

1. Scoring Guidelines (using 0.5-point intervals):
   - 1.0: Fails to meet any of the evaluation criteria
   - 1.5: Barely meets minimum requirements, significantly below standards
   - 2.0: Partially meets criteria but with notable deficiencies
   - 2.5: Meets some criteria but overall performance is mediocre
   - 3.0: Meets most criteria, achieving basic requirements
   - 3.5: Satisfactorily meets criteria, demonstrating good performance
   - 4.0: Well meets criteria, showing excellent performance
   - 4.5: Strongly meets criteria, demonstrating outstanding performance
   - 5.0: Perfectly meets all criteria, demonstrating exceptional performance

2. Evaluation Principles:
   - Strictly follow the specific criteria in the evaluation standards
   - Ensure score differentiation by appropriately using 0.5-point intervals
   - Provide clear justification for each scoring decision
   - Offer specific explanations that highlight both strengths and areas for improvement
   - Focus on the therapist's specific performance in the evaluated dimension

3. Important Considerations:
   - Do not award high scores based solely on dialogue fluency
   - Strictly compare against the specific criteria in the evaluation standards
   - Provide thorough reasoning for each scoring point
   - Maintain objectivity and avoid subjective bias
   - Focus on the therapist's specific performance in the evaluated dimension"""
# Common prompt template for evaluation
COMMON_PROMPT_TEMPLATE = """You are a professional supervisor in the field of narrative therapy. Please evaluate the following counseling dialogue based on the dimension of **{dimension_name}({dimension_english})** in narrative therapy practice.

# Definition:
{dimension_definition}

# Evaluation Criteria:
{evaluation_criteria}

# Dialogue Content:
{dialogue_text}

# Scoring Guidelines:
Rate on a scale of 1-5 (1 being lowest, 5 being highest), with minimum increments of 0.5.
Your evaluation should be professional and demonstrate clear score differentiation.

# Output Format:
Please provide your evaluation in YAML format, where score is a decimal value and explanation is concise and targeted (no more than 30 words), as follows:
```YAML
{dimension_english}: <score>
explanation: <explanation>
```"""

# Definitions and evaluation criteria for each dimension
DIMENSION_CRITERIA = {
    "reassuring": {
        "name": "Reassuring",
        "definition": """The therapist's ability to effectively convey care and understanding, helping clients feel heard and supported, particularly in providing emotional comfort and solace. In narrative therapy, reassurance often emerges during the early stages of trust-building, facilitating client relaxation and willingness to share their concerns.""",
        "criteria": [
            "Providing warm responses during moments of client vulnerability",
            "Demonstrating genuine empathy and understanding",
            "Effectively alleviating client anxiety and distress",
            "Using appropriate tone and language to convey care",
            "Offering essential psychological comfort at critical moments"
        ]
    },
    "empowering": {
        "name": "Empowering",
        "definition": """The therapist's capacity to help clients redefine and reframe their problems, particularly during the externalization phase. In narrative therapy, externalization is a key strategy for helping clients separate problems from their identity. This dimension evaluates how well the therapist encourages new perspectives and enhances clients' confidence in problem-solving.""",
        "criteria": [
            "Effectively guiding clients to separate concerns from internalized emotions",
            "Helping clients examine problems from new perspectives",
            "Promoting clients' sense of self-efficacy",
            "Guiding clients in setting achievable goals",
            "Providing constructive feedback and suggestions"
        ]
    },
    "transformative": {
        "name": "Transformative",
        "definition": """The therapist's ability to facilitate profound self-reflection, helping clients reconstruct their thinking or develop new cognitions. In narrative therapy, re-authoring is a core phase where, through therapeutic interaction, clients can rewrite their personal stories and reshape their understanding of events, leading to personal growth and cognitive transformation.""",
        "criteria": [
            "Facilitating cognitive restructuring and redefinition of past experiences",
            "Helping clients develop multiple perspectives on self-understanding",
            "Guiding clients to discover new possibilities",
            "Promoting behavioral change in clients",
            "Assisting clients in constructing new narratives"
        ]
    },
    "reconnecting": {
        "name": "Reconnecting",
        "definition": """The therapist's ability to help clients re-examine their relationships with others, themselves, or their environment, enhancing emotional connections. Re-membering is a crucial concept in narrative therapy, helping clients repair connections with others or themselves through re-examining past relationships.""",
        "criteria": [
            "Helping clients re-examine relationships with significant others and things",
            "Promoting social connections for clients",
            "Assisting clients in establishing new relationship patterns or restoring emotional harmony and balance"
        ]
    },
    "humanness": {
        "name": "Humanness",
        "definition": """The therapist's ability to provide natural, fluid responses that feel authentic, avoiding mechanical replies. We expect therapists to mimic human interaction in their language, making the dialogue feel warm and genuine while effectively conveying emotions.""",
        "criteria": [
            "Maintaining natural and fluid conversation",
            "Responding in a natural and caring manner",
            "Maintaining appropriate self-disclosure",
            "Demonstrating professional humanistic care"
        ]
    }
}

# Generate complete evaluation prompts
def generate_evaluation_prompt(dimension: str, dialogue_text: str) -> str:
    """
    Generate evaluation prompt for a specific dimension
    
    Args:
        dimension: Dimension name (in English)
        dialogue_text: Dialogue text
        
    Returns:
        Complete evaluation prompt
    """
    criteria = DIMENSION_CRITERIA[dimension]
    criteria_text = "\n".join([f"{i+1}. {criterion}" for i, criterion in enumerate(criteria["criteria"])])
    
    return COMMON_PROMPT_TEMPLATE.format(
        dimension_name=criteria["name"],
        dimension_english=dimension,
        dimension_definition=criteria["definition"],
        evaluation_criteria=criteria_text,
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