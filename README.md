# Chaoxing_Homework 自动化作业爬取与批改系统

## 项目简介

本项目旨在实现对超星学习通平台作业的自动化爬取与智能批改。系统分为两大模块：

- **crawler**：用于自动化登录超星平台，爬取课程、班级、作业及学生作答数据。
- **grader**：基于大模型（如OpenAI/ollama等）对学生作业进行智能批改和评分。

适用于高职/高校教师批量处理学生作业，极大提升工作效率。

---

## 目录结构

```
Chaoxing_Homework/
│
├── main.py                  # 项目主入口
├── config/
│   └── _args.py             # 配置参数与命令行解析
├── core/
│   └── browser.py           # Playwright 浏览器管理
├── crawler/                 # 作业爬取相关代码
│   ├── client.py
│   ├── crawler.py
│   ├── processor.py
│   ├── auth/
│   │   ├── base.py
│   │   ├── password.py
│   │   └── qrcode.py
│   └── interface.py
├── grader/                  # 作业批改相关代码
│   ├── homework_grader.py
│   ├── score_processor.py
│   ├── openai_client.py
│   ├── homework_processor.py
│   ├── file_manager.py
│   ├── message_builder.py
│   └── interface.py
└── requirements.txt         # 依赖包列表（如无请自行创建）
```

---

## 环境依赖

1. **Python 3.8+**
2. 推荐使用虚拟环境（venv/conda）

### 安装依赖

请先进入项目根目录，执行：

```bash
pip install -r requirements.txt
```

如未提供 `requirements.txt`，请根据实际代码补充依赖（如 playwright、beautifulsoup4、requests、openai 等）。
迁移到 Playwright 后，请额外执行 `playwright install chromium`。

---

## 配置说明

所有参数均可通过 `config/_args.py` 配置，支持命令行传参。

常用参数说明：

- `--api_key`：大模型API密钥（如OpenAI/ollama）
- `--base_url`：大模型API地址
- `--phonenumber`、`--password`：超星登录手机号和密码（如需自动登录）
- `--use_qr_code`：是否使用二维码登录（默认True）
- `--course_urls`：要爬取的课程URL列表
- `--class_list`：要爬取的班级列表
- `--homework_name_list`：要爬取的作业名列表
- 其他参数详见 `config/_args.py` 注释

**示例：**

```bash
python main.py --api_key=你的APIKEY --phonenumber=手机号 --password=密码
```

---

## 使用方法

1. **配置参数**  
   修改 `config/_args.py` 或通过命令行传参，填写你的API密钥、超星账号等信息。

2. **运行主程序**

   ```bash
   python main.py
   ```

   程序将自动执行以下流程：
   - 使用爬虫模块登录超星，爬取指定课程/班级/作业的学生作答数据
   - 调用大模型对作业进行智能批改与评分
   - 输出批改结果（可根据代码自定义保存/导出方式）

3. **日志与结果查看**  
   日志信息会输出到控制台，批改结果可在相关输出文件或数据库中查看（具体见 `grader/file_manager.py` 实现）。

---

## 常见问题

- **API Key/模型地址如何获取？**  
  请根据你所用的大模型平台（如OpenAI、Ollama等）获取API Key和API地址。

- **二维码登录/账号密码登录失败？**  
  检查网络环境、账号密码是否正确，或尝试切换登录方式。

- **依赖缺失/报错？**  
  请根据报错信息补充安装依赖包。

---

## 贡献与反馈

如有建议、Bug反馈或功能需求，欢迎提交 Issue 或 PR！
