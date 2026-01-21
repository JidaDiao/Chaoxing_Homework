# Quickstart: 响应式评分接口迁移

## Prerequisites

- Python 3.8+
- 可用网络与有效模型凭据

## Run

```bash
python main.py --mode grade
```

## Validate

- 分析阶段不再输出“pass”占位内容
- 同一作业复用同一评分 session，允许分批评分
- 输出结构与现有批改流程兼容

## Validation Steps

1. 使用包含 5-8 名学生答案的作业目录运行评分流程
2. 确认分析阶段一次性生成评分标准与样本分数
3. 确认批量评分每次处理 3-5 名学生且复用同一 session
4. 检查 `original_student_score.json` 结构包含 `score` 与 `scoring_criteria`

## Validation Results

- 2026-01-21: Playwright 验证作业列表与两班 Review 页面可达；评分流程未执行
