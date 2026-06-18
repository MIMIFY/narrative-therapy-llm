# 评估

[English](README.md) | [中文](README_zh.md)

本目录包含两套用于 INT 对话的评估流程。

论文链接：https://aclanthology.org/2025.emnlp-main.1245/

- `ima/`：对来访者发言进行 Innovative Moment Assessment / IMCS 标注。
- `dimension_metrics/`：基于大模型的多维度治疗质量评分。

两套流程均支持 INT 模拟输出和导出的会话记录。

## 输入格式

推荐输入格式是一个由对话轮次组成的 JSON 列表。

```json
[
  {
    "round": 1,
    "client": "I feel overwhelmed...",
    "therapist": "That sounds heavy...",
    "stage": "Trust Building",
    "reflection_level": "Empathic Comforting"
  }
]
```

脚本也支持 INT 模拟脚本生成的包装格式：

```json
{
  "session_id": "...",
  "dialogue": [
    {"round": 1, "client": "...", "therapist": "..."}
  ]
}
```

脚本也兼容旧字段，例如 `user`、`baseline`、`answer_final` 和 `answer_before`。

## 安装

```bash
cd evaluation
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

设置 OpenAI-compatible API 凭证。

```bash
export OPENAI_API_KEY=your-key
export OPENAI_BASE_URL=https://api.openai.com/v1
```

如使用 OpenRouter：

```bash
export OPENROUTER_API_KEY=your-key
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## 输入目录结构

扁平目录：

```text
int/simulation_output/
├── dialogue_001.json
└── dialogue_002.json
```

此时使用 `--version .`。

多版本目录：

```text
outputs/
├── GPT-4o/
│   ├── dialogue_001.json
│   └── dialogue_002.json
└── INT/
    └── dialogue_001.json
```

此时使用 `--input_dir outputs --version GPT-4o`。

## IMA / IMCS 标注

从 `evaluation/ima` 目录运行。

```bash
cd ima
../venv/bin/python IMCS_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/imcs \
  --number INT-full \
  --language en
```

常用参数：

- `--language zh|en`：提示词语言。
- `--context_window 5`：标注时使用的历史轮数。
- `--max_files 10`：快速小规模测试。
- `--specific_prefix 2`：只处理文件名以 `cooperation_level_2_` 开头的文件。
- `--engine gpt-4o`：OpenAI-compatible 模型名。
- `--base_url`：覆盖服务商 URL。
- `--api_key`：覆盖环境变量中的 API key。

输出目录：

```text
outputs/imcs/
└── flat/
    └── INT-full/
        ├── dialogue_001.json
        └── ...
```

每轮会新增 `IMCS` 对象，包含 `annotation`、`resource`、`confidence` 和 `latent_narrative_dynamics_analysis`。

## IMA 统计分析

标注完成后，可以使用 `ima/Analysis.py` 统计并绘制 IMCS 类别显著性。

```bash
../venv/bin/python Analysis.py \
  --input_dir ../outputs/imcs/flat/INT-full \
  --output_dir ../outputs/imcs_analysis
```

## 治疗维度评分

从 `evaluation/dimension_metrics` 目录运行。

```bash
cd ../dimension_metrics
../venv/bin/python dimention_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/dimensions \
  --number INT-full \
  --key_client client \
  --key_therapist therapist
```

也可以使用封装脚本：

```bash
OPENAI_API_KEY=your-key ./run_evaluation.sh
```

常用参数：

- `--key_client client`：来访者发言字段名。
- `--key_therapist therapist`：咨询师回复字段名。
- `--specific_prefix cooperation_level_2`：只处理指定前缀文件。
- `--max_files 10`：快速小规模测试。
- `--engine gpt-4o`：OpenAI-compatible 模型名。

输出目录：

```text
outputs/dimensions/
└── flat/
    └── INT-full/
        ├── all_evaluation_results.json
        └── average_scores_all.json
```

## 可复现性说明

- 这些脚本会调用外部大模型，因此分数可能随服务商、模型和日期变化。
- 为保证可复现性，建议固定模型名，并记录 `base_url`、`engine` 和运行日期。
