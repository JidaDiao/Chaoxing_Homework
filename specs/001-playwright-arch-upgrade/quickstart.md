# Quickstart: Playwright 架构升级

## Prerequisites

- Python 3.8+
- 可用网络与有效超星账号

## Install

```bash
pip install -r requirements.txt
pip install playwright
playwright install chromium
```

## Configure

- 在 `.env` 或配置文件中设置账号、课程链接、班级与作业筛选
- 确认 `grader/` 与 `config/_args.py` 未被修改

## Run

```bash
python main.py --mode crawl
```

## Validate

- 生成的 `homework/**/answer.json` 可被现有批改模块直接使用
- 日志不包含学生姓名或作答内容
- 运行 `python main.py --mode grade` 验证输出结构可被批改流程解析
- Playwright MCP 验证 (2026-01-21): 登录页 `#phone/#pwd/#loginBtn/#quickCode` 均存在
