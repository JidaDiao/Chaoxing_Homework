import json
import base64
import requests
from io import BytesIO
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image
import time
import os
import shutil
import xlrd
from xlutils.copy import copy
import glob
import re


def import_json_file(file_path):
    """
    导入JSON文件并返回其内容。
    
    :param file_path: JSON文件的路径
    :return: 解析后的JSON内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"JSON文件解析错误: {file_path}")
        return None


def download_image(url_or_base64):
    """下载图片或处理Base64格式图片，并压缩以减少字符串长度"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Referer': url_or_base64  # 添加来源页面，部分网站需要
    }
    try:
        if url_or_base64.startswith("data:image/"):  # 判断是否是 Base64 图片
            # 处理 Base64 数据
            base64_data = url_or_base64.split(",")[1]  # 去掉前缀 "data:image/png;base64,"
            image_bytes = base64.b64decode(base64_data)
            image = Image.open(BytesIO(image_bytes))
        else:
            # 下载图片
            response = requests.get(url_or_base64, headers=headers, timeout=10)
            if response.status_code == 200:
                # 使用 BytesIO 处理二进制数据
                image_bytes = BytesIO(response.content).read()
                image = Image.open(BytesIO(image_bytes))
            else:
                print(f"请求失败，状态码: {response.status_code}")
                return None

        # 检查并转换图片模式为 RGB（JPEG 不支持 RGBA 模式）
        if image.mode in ("RGBA", "P"):  # 如果图片有透明通道
            image = image.convert("RGB")

        # 调整图像分辨率至原来的80%
        width, height = image.size
        new_size = (int(width * 0.8), int(height * 0.8))  # 降低分辨率，省钱！！！！
        image = image.resize(new_size, Image.Resampling.LANCZOS)

        # 压缩图片并转换为 Base64 格式
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=80)  # 调整质量因子为80，省钱！！！！
        compressed_image_bytes = buffered.getvalue()

        ## 学生们图片太大了，api调用费时就算了钱还花的多55555

        # 返回压缩后的 Base64 字符串
        return base64.b64encode(compressed_image_bytes).decode('utf-8')

    except Exception as e:
        print(f"处理图片失败: {url_or_base64}, 错误: {str(e)}")
        return None


def randomselect_uncorrected(student_answers_prompt_uncorrected, number):
    # 随机选择 n 个键
    selected_keys = random.sample(list(student_answers_prompt_uncorrected.keys()), number)
    # 创建新字典并从原字典删除这些键
    # selected_dict = {key: student_answers_prompt_uncorrected.pop(key) for key in selected_keys}
    selected_dict = {key: student_answers_prompt_uncorrected[key] for key in selected_keys}
    return selected_dict, selected_keys


def pop_uncorrected(student_answers_prompt_uncorrected, selected_keys):
    # 创建新字典并从原字典删除这些键
    _ = {key: student_answers_prompt_uncorrected.pop(key) for key in selected_keys}


def randompop_corrected(student_answers_prompt_corrected, number):
    # 随机选择 n 个键
    selected_keys = random.sample(list(student_answers_prompt_corrected.keys()), number)
    # 创建新字典
    selected_dict = {key: student_answers_prompt_corrected[key] for key in selected_keys}
    return selected_dict


def context_prepare_prompt(selected_dict, prepare_system_prompt, number):
    context_prompt = prepare_system_prompt
    for index, (key, value) in enumerate(selected_dict.items(), start=1):
        context_prompt += value
        if index < number:
            context_prompt.append({
                "role": "assistant",
                "content": "第" + str(index) + "轮：pass"
            })
    return context_prompt


def context_few_shot_learning_prompt(selected_dict_uncorrected, selected_dict_corrected,
                                     few_shot_learning_system_prompt):
    context_prompt = few_shot_learning_system_prompt
    for index, (key, value) in enumerate(selected_dict_corrected.items(), start=1):
        context_prompt += value
    for index, (key, value) in enumerate(selected_dict_uncorrected.items(), start=1):
        context_prompt += value
    return context_prompt


def parse_grading_response(response):
    # 提取学生名字和成绩部分
    # 提取学生名字和成绩
    student_scores = re.findall(r"(\S+)：(\d+)分", response)
    student_dict = {name: int(score) for name, score in student_scores}

    # 提取评分标准
    scoring_standard_match = re.search(r"### 本作业评分标准：\s*(.*)", response, re.DOTALL)
    scoring_standard = scoring_standard_match.group(1).strip() if scoring_standard_match else ""

    return student_dict, scoring_standard


def convert_url(original_url, pages=1):
    """
    将链接1的URL转换为链接2的格式，并支持指定翻页。

    Parameters:
        original_url (str): 原始链接
        pages (int): 页码，默认为1

    Returns:
        str: 转换后的链接
    """
    # 解析原始链接
    parsed_url = urlparse(original_url)
    query_params = parse_qs(parsed_url.query)

    # 保留的参数：courseid, clazzid, cpi
    courseid = query_params.get("courseid", [""])[0]
    clazzid = query_params.get("clazzid", [""])[0]
    cpi = query_params.get("cpi", [""])[0]

    # 构造新的参数
    new_params = {
        "courseid": courseid,
        "clazzid": clazzid,
        "cpi": cpi,
        "recycle": "0",
        "pid": "0",
        "status": "-1",
        "pages": str(pages),  # 指定页码
        "size": "12",
        "selectClassid": "0",
        "search": "",
        "v": "0",
        "topicid": "0",
    }

    # 构造新链接
    new_query = urlencode(new_params)
    new_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", new_query, ""))
    return new_url


def sanitize_folder_name(folder_name):
    """
    将字符串转换为合法的Windows文件夹名称，尽量少修改。
    """
    # 定义Windows文件夹名称中的非法字符
    invalid_chars = r'[<>:"/\\|?*]'
    reserved_names = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]

    # 替换非法字符为下划线
    sanitized_name = re.sub(invalid_chars, "_", folder_name)

    # 去掉结尾的点和空格（Windows不允许以点或空格结尾）
    sanitized_name = sanitized_name.rstrip(" .")

    # 如果名称是保留关键字，则添加后缀
    if sanitized_name.upper() in reserved_names:
        sanitized_name += "_folder"

    # 如果最终名称为空，则设置为默认名称
    if not sanitized_name:
        sanitized_name = "default_folder"

    return sanitized_name


def download(driver, save_path, url):
    driver.get(url)
    # 等待页面加载完成
    wait = WebDriverWait(driver, 10)

    # 1. 定位"更多"按钮
    more_button = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'piyue_more')))

    # 2. 将鼠标悬停在"更多"按钮上
    ActionChains(driver).move_to_element(more_button).perform()

    # 3. 定位"导入成绩"按钮（悬停后出现）
    import_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@onclick="showImportDiv();"]')))

    # 4. 点击"导入成绩"按钮
    import_button.click()
    # 点击按钮，触发 URL 的动态生成
    download_button = driver.find_element(By.XPATH, '//a[@onclick="exportScoreTemplate(true)"]')
    download_button.click()

    time.sleep(5)  # 等待文件下载完成
    source_path = r"C:\Users\JidaDiao\Downloads"
    move_xls_files(source_path, save_path)


def move_xls_files(source_path, save_path):
    # 检查源目录是否存在
    if not os.path.exists(source_path):
        print(f"源目录不存在: {source_path}")
        return

    # 检查目标目录是否存在，如果不存在则创建
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        print(f"目标目录不存在，已创建: {save_path}")

    # 遍历源目录中的文件
    for file_name in os.listdir(source_path):
        # 构建完整文件路径
        file_path = os.path.join(source_path, file_name)

        # 检查是否是文件且后缀为.xls
        if os.path.isfile(file_path) and file_name.endswith('.xls'):
            # 移动文件到目标目录
            shutil.move(file_path, os.path.join(save_path, file_name))
            print(f"已移动文件: {file_name}")


def normalize_and_save_grade(student_score_final, min_score, max_score):
    xls_file = glob.glob("*.xls")[0]  # 获取当前路径下唯一的 .xls 文件
    workbook = xlrd.open_workbook(xls_file, formatting_info=True)
    sheet = workbook.sheet_by_index(0)

    # 找到学生姓名和分数列索引
    name_col_idx = None
    score_col_idx = None

    for col in range(sheet.ncols):
        header = sheet.cell_value(1, col)  # 假设第一行是表头
        if "学生姓名" in header:
            name_col_idx = col
        elif "分数" in header:
            score_col_idx = col

    if name_col_idx is None or score_col_idx is None:
        raise ValueError("未找到'学生姓名'或'分数'列，请检查表头是否包含这些字段！")

    # 归一化分数
    # scores = list(student_score_final.values())
    # min_original = min(scores)
    # max_original = max(scores)

    # def normalize_score(score):
    #     return ((score - min_original) / (max_original - min_original)) * (max_score - min_score) + min_score
    def scale_score(score):
        if score < 20:
            return score
        else:
            return score / 100 * max_score + min_score

    normalized_scores = {name: scale_score(score) for name, score in student_score_final.items()}

    # 创建副本以便写入数据
    new_workbook = copy(workbook)
    new_sheet = new_workbook.get_sheet(0)

    # 遍历表格，将归一化后的分数填入对应的行
    for row in range(2, sheet.nrows):  # 跳过表头行
        student_name = sheet.cell_value(row, name_col_idx)  # 获取学生姓名
        if student_name in normalized_scores:
            new_sheet.write(row, score_col_idx, normalized_scores[student_name])  # 写入归一化分数

    # 保存文件（覆盖原文件或保存为新文件）
    new_workbook.save(xls_file)  # 保存为 updated 文件
    print("分数更新完成！")
    return normalized_scores
