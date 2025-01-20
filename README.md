# Chaoxing_Homework
试着用大模型改超新的作业

## 项目简介

本项目旨在使用大模型自动批改超星平台上的学生作业。通过解析学生的回答和图片，结合预设的评分标准，自动生成学生的分数。

## 安装

请确保你已经安装了 Python 3.7 或更高版本。然后，使用以下命令安装项目所需的依赖库：

```bash
pip install -r requirements.txt
```

## 使用方法

1. 配置 `args.py` 文件中的参数，包括 API 密钥、基准 URL、最大线程数等。
2. 运行 `prepare_data.py` 来爬取作业数据。
3. 使用 `revise_homework.py` 来批改作业并生成评分。

## 文件说明

- `revise_homework.py`：用于批改作业的主脚本。
- `prepare_data.py`：用于爬取作业数据的脚本。
- `utils.py`：包含辅助函数的模块。
- `args.py`：用于解析命令行参数的模块。

## 依赖

项目依赖的主要库包括：
- openai
- concurrent.futures
- argparse
- selenium
- beautifulsoup4
- requests
- pillow
- xlrd
- xlutils

## 注意事项

- 请确保在运行脚本前正确配置所有参数。
- 确保网络连接正常，以便访问超星平台和 OpenAI API。

## 贡献

欢迎对本项目提出建议和贡献代码。
