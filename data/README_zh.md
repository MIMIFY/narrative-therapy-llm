# 数据

[English](README.md) | [中文](README_zh.md)

本目录包含 INT 系统使用的公开数据集和从 ESConv 提取的来访者画像。

论文链接：https://aclanthology.org/2025.emnlp-main.1245/

## NTConv 数据集（`ntconv/`）

`ntconv/` 包含 1300 个由 INT 框架生成的英文叙事疗法对话。

生成流程对应论文第 4.4 节：

1. 从 ESConv 中提取来访者画像，包括情绪、问题和情境。
2. 基于画像使用 GPT-4o 模拟来访者。
3. 让模拟来访者与 INT 进行 50 轮互动。
4. 为每轮标注治疗阶段和反思水平。

划分：1040 train / 260 test (80/20, no overlap)。

## 格式

每个文件是包含 50 轮对话的 JSON 列表。

```json
{
  "round": 1,
  "client": "I feel overwhelmed...",
  "therapist": "That sounds heavy...",
  "stage": "Trust Building",
  "reflection_level": "Empathic Comforting"
}
```

前若干轮可能包含来自源数据的额外字段，例如 `user`、`answer_final`、`user_annotations`、`supporter_annotations` 和 `user_cooperation`。

## ESConv 画像（`esconv_profiles/ESConv.json`）

`ESConv.json` 包含 1300 条处理后的 ESConv 对话，用于作为模拟来访者的画像种子。

每条记录包含以下字段：

- `experience_type`
- `emotion_type`
- `problem_type`
- `situation`
- `survey_score`
- `dialog`
- 来访者与支持者问卷字段

INT 模拟脚本会直接读取该文件。

```bash
cd int
venv/bin/python simulate_client.py \
  --esconv ../data/esconv_profiles/ESConv.json \
  --profile-index 0 \
  --turns 35
```

## 真实用户对话

当前公开目录不包含真实用户对话。

如未来发布，应先完成脱敏，并在本文档中补充数据说明。
